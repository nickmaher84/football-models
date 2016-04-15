from settings import events, regions, tournaments, seasons, stages, matches, teams, players
from numpy import dot, arccos, array
from numpy.linalg import norm
from pandas import DataFrame


def load_data(limit=0):
    BODYPARTS = ['RightFoot', 'LeftFoot', 'Head', 'OtherBodyPart']
    PATTERNOFPLAY = ['RegularPlay', 'FastBreak', 'SetPiece', 'FromCorner', 'Penalty', 'DirectFreekick', 'ThrowinSetPiece']
    SHOTLOCATION = ['SmallBoxLeft', 'SmallBoxCentre', 'SmallBoxRight',
                    'DeepBoxLeft', 'BoxLeft', 'BoxCentre', 'BoxRight', 'DeepBoxRight',
                    'OutOfBoxDeepLeft', 'OutOfBoxLeft', 'OutOfBoxCentre', 'OutOfBoxRight', 'OutOfBoxDeepRight',
                    'ThirtyFivePlusLeft', 'ThirtyFivePlusCentre', 'ThirtyFivePlusRight']

    l, c, r = array([104, 34]), array([104, 38]), array([104, 42])
    shots = []
    for event in events.find({'isShot': True, 'isOwnGoal': {'$exists': False}}).limit(limit):
        shot = dict()
        shot['id'] = int(event['id'])
        shot['Goal'] = event.get('isGoal') is True
        shot['X'] = 1.04 * event['x']
        shot['Y'] = 0.76 * event['y']

        p = array([shot['X'], shot['Y']])
        shot['Distance'] = norm(p - c)
        shot['Angle'] = arccos(dot(p - l, p - r) / norm(p - l) / norm(p - r))

        shot_qualifiers = {q['type']['displayName']: q.get('value') for q in event['qualifiers']}
        for qualifier in shot_qualifiers:
            if qualifier in BODYPARTS:
                shot['BodyPart'] = qualifier
            elif qualifier in PATTERNOFPLAY:
                shot['PatternOfPlay'] = qualifier
            elif qualifier in SHOTLOCATION:
                shot['ShotLocation'] = qualifier
            elif qualifier == 'Zone':
                shot['Zone'] = shot_qualifiers[qualifier]
            elif qualifier == 'RelatedEventId':
                related_event = events.find_one({'eventId': event['relatedEventId'],
                                                 'matchId': event['matchId'],
                                                 'teamId': event['teamId']})
                shot['RelatedEventType'] = related_event['type']['displayName'] if related_event else None

        region = regions.find_one({'regionId': event['regionId']})
        shot['Region'] = region['name'] if region else None

        tournament = tournaments.find_one({'tournamentId': event['tournamentId']})
        shot['Tournament'] = tournament['name'] if tournament else None

        season = seasons.find_one({'seasonId': event['seasonId']})
        shot['Season'] = season['name'] if season else None

        stage = stages.find_one({'stageId': event.get('stageId')})
        shot['Stage'] = stage['name'] if stage else None

        team = teams.find_one({'teamId': event['teamId']})
        shot['Team'] = team['name'] if team else None

        player = players.find_one({'playerId': event['playerId']})
        shot['Player'] = player['name'] if player else None

        match = matches.find_one({'matchId': event['matchId']})
        shot['Side'] = 'home' if team['name'] == match['home']['name'] else 'away'
        shot['Opponent'] = match['away']['name'] if team['name'] == match['home']['name'] else match['home']['name']
        shot['Date'] = match['startDate']

        shot['Period'] = event['period']['displayName']
        shot['Minute'] = event['minute']

        shots.append(shot)

        if len(shots) % 10 == 0:
            print('{0} shots in data set'.format(len(shots)))

    print('{0} shots in data set'.format(len(shots)))

    return DataFrame(shots)


if __name__ == "__main__":
    dataset = load_data(1000)
    dataset.to_csv('shots.csv', index=False)
