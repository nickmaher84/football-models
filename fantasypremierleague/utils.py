from fantasypremierleague.api import FantasyPremierLeague
from math import exp
from pymongo import MongoClient

db = MongoClient().get_database('fantasy-premier-league')

team_table = db['teams']
team_table.create_index(keys='id', name='team_id', unique=True)
team_table.create_index(keys='code', name='team_code', unique=True)
team_table.create_index(keys='name', name='team_name', unique=True)
team_table.create_index(keys='short_name', name='team_short_name', unique=True)

position_table = db['positions']
position_table.create_index(keys='id', name='position_id', unique=True)
position_table.create_index(keys='singular_name', name='position_singular_name', unique=True)
position_table.create_index(keys='singular_name_short', name='position_singular_name_short', unique=True)

player_table = db['players']
player_table.create_index(keys='id', name='player_id', unique=True)
player_table.create_index(keys='code', name='player_code', unique=True)
player_table.create_index(keys='web_name', name='player_web_name', unique=False)
player_table.create_index(keys='team', name='player_team', unique=False)
player_table.create_index(keys='element_type', name='player_position', unique=False)

my_team_table = db['my-team']
my_team_table.create_index(keys='position', name='squad_position', unique=True)
my_team_table.create_index(keys='element', name='squad_player_id', unique=True)


def full_refresh(username, password):
    fpl = FantasyPremierLeague(username, password)
    print('Getting bootstrap')
    data = fpl.all_data()

    for team in data['teams']:
        team_id = team['id']

        team_table.update_one({'id': team_id}, {'$set': team}, upsert=True)

    for position in data['element_types']:
        position_id = position['id']

        scoring = {**data['game-settings']['game'], **data['game-settings']['element_type'][str(position_id)]}
        for k, v in scoring.items():
            if k.startswith('scoring_'):
                if k.endswith('_limit'):
                    position.setdefault(k.replace('scoring_', 'limit.').replace('_limit', ''), v)
                else:
                    position.setdefault(k.replace('scoring_', 'scoring.'), v)

        position_table.update_one({'id': position_id}, {'$set': position}, upsert=True)

    for player in data['elements']:
        player_id = player['id']
        print(player.get('web_name'))

        player_details = fpl.player(player_id)
        player.update(player_details)

        position = position_table.find_one({'id': player['element_type']})
        scoring = position['scoring']
        for k in scoring:
            if not k.endswith('_limit'):
                player[k] = sum([result.get(k, 0) for result in player['history']])
        player['short_play'] = len([result for result in player['history'] if position['limit']['long_play'] > result['minutes'] > 0])
        player['long_play'] = len([result for result in player['history'] if position['limit']['long_play'] <= result['minutes']])
        player['participation'] = player['minutes'] / (90 * len(player['history'])) if player['minutes'] else 0

        player.setdefault('p90', dict())
        for k in scoring:
            if player['minutes']:
                player['p90'][k] = 90 * player[k] / player['minutes']
            else:
                player['p90'][k] = 0

        player.setdefault('expected', dict())
        for k, v in scoring.items():
            player['expected'][k] = player['p90'][k] * v
            if k == 'goals_conceded':
                player['expected'][k] /= position['limit']['concede']
            if k == 'saves':
                player['expected'][k] /= position['limit']['saves']
            if k == 'clean_sheets':
                player['expected'][k] = exp(-player['p90']['goals_conceded']) * v
        if type(player['chance_of_playing_next_round']) is int:
            availability = player['chance_of_playing_next_round']/100
        else:
            availability = 1
        player['expected_points'] = player['participation'] * availability * sum(player['expected'].values())
        player['expected_value'] = player['expected_points'] / player['now_cost']

        player_table.update_one({'id': player_id}, {'$set': player}, upsert=True)

    team_refresh(username, password)


def team_refresh(username, password):
    fpl = FantasyPremierLeague(username, password)
    print('Getting my team')
    data = fpl.all_data()

    my_team = fpl.my_team(data['entry']['id'])
    my_team_table.delete_many({})
    for pick in my_team['picks']:
        my_team_table.update_one({'position': pick['position']}, {'$set': pick}, upsert=True)


def count_teams(players):
    teams = dict()
    for player in players:
        team = player['team']
        teams.setdefault(team, 0)
        teams[team] += 1
    return teams


def get_players(position=None, limit=None, key='expected_value', available_only=True):
    if available_only:
        parameters = {'status': 'a'}
    else:
        parameters = dict()

    if type(position) is int:
        parameters['element_type'] = position
    elif type(position) is str and len(position) == 3:
        parameters['element_type'] = position_table.find_one({'singular_name_short': position}).get('id')
    elif type(position) is str:
        parameters['element_type'] = position_table.find_one({'singular_name': position}).get('id')

    players = player_table.find(parameters).sort(key, -1)

    if limit:
        return players.limit(limit)
    else:
        return players


def find_trade(team, budget=0, picks=1):
    reduce_cost = budget < 0
    teams = count_teams(team)

    trades = list()

    for pick in team:
        for player in get_players(pick['element_type']):
            if player not in team:
                cost = player['now_cost'] - pick['now_cost']
                points = player['expected_points'] - pick['expected_points']
                if reduce_cost:
                    if cost < 0:
                        if pick['team'] == player['team'] or teams.get(player['team'], 0) < 3:
                            trade = (pick, player, cost, points, points / cost)
                            trades.append(trade)

                else:
                    if points > 0 and budget >= cost:
                        if pick['team'] == player['team'] or teams.get(player['team'], 0) < 3:
                            trade = (pick, player, cost, points, cost / points)
                            trades.append(trade)

    if trades and picks > 1:
        # TODO: Two picks
        pass

    elif trades:
        trades.sort(key=lambda p: (p[4], -p[3]))
        for pick, player, cost, points, value in trades[:]:
            print('{0} -> {1} ({2}, {3})'.format(pick['web_name'], player['web_name'], cost, points))
        return trades[0]

    else:
        return None


def pick_transfers(budget=0, trades=1, wildcard=False):
    my_team = my_team_table.find()

    if my_team.count():
        team = list()
        team_value = 0
        for pick in my_team:
            team_value += pick['selling_price']
            player = player_table.find_one({'id': pick['element']})
            team.append(player)
        team.sort(key=lambda p: (p['element_type'], -p['expected_points']))
        print('Team value: {0} (Transfer budget: {1})'.format(team_value, budget))

        if wildcard:
            # TODO: Play wildcard and re-select whole team
            pass

        elif trades == 1:
            find_trade(team, budget)

        elif trades >= 2:
            find_trade(team, budget, 2)

    else:
        return pick_team()


def pick_team(budget=1000):
    print('Starting budget: {0}'.format(budget))

    # Make starting team: best 2xGKP, 5xDEF, 5xMID, 3xFWD
    team = list()
    players = get_players()
    while len(team) < 15:
        player = players.next()
        position = player['element_type']
        position_count = len([p for p in team if p['element_type'] == position])
        if position_count >= {1: 2, 2: 5, 3: 5, 4: 3}.get(position):
            continue
        if count_teams(team).get(player['team'], 0) >= 3:
            continue
        team.append(player)

    team.sort(key=lambda p: (p['element_type'], -p['expected_points']))
    team_cost = sum([player['now_cost'] for player in team])
    print(team_cost)

    # Trade down until within budget
    while team_cost > budget:
        trade = find_trade(team, budget - team_cost)

        if trade:
            i = team.index(trade[0])
            team[i] = trade[1]
            team_cost = sum([player['now_cost'] for player in team])
            print(team_cost)

        else:
            print('No more trades')
            break

    # Trade up with remaining budget
    while team_cost <= budget:
        trade = find_trade(team, budget - team_cost)

        if trade:
            i = team.index(trade[0])
            team[i] = trade[1]
            team_cost = sum([player['now_cost'] for player in team])
            print(team_cost)

        else:
            print('No more trades')
            break

    # List team
    for p in team:
        print(p['web_name'])

    return team

if __name__ == "__main__":
    full_refresh('nickmaher84@googlemail.com', 'anfield')
