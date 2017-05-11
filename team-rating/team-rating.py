import requests
import pandas.io.json
import patsy
import statsmodels.api


def get_data(season, division, variables):
    assert isinstance(variables, int) and variables in [1, 2, 3, 4]

    url = 'https://api.project-hanoi.co.uk/football-data/v1/{0}/{1}'.format(season, division)
    response = requests.get(url)

    data = pandas.io.json.json_normalize(response.json())

    lookup = {'Home': 'Attack', 'Away': 'Defend', 'Full Time.Home': 'Goals'}
    home = data[list(lookup.keys())]
    home = home.rename(index=str, columns=lookup)
    home['Home'] = 1

    lookup = {'Away': 'Attack', 'Home': 'Defend', 'Full Time.Away': 'Goals'}
    away = data[list(lookup.keys())]
    away = away.rename(index=str, columns=lookup)
    away['Home'] = 0

    combined = home.append(away, ignore_index=True)
    combined['Constant'] = 1

    if variables == 1:
        """One variable per team, plus a global home advantage term"""
        a = combined.pivot(columns='Attack', values='Constant').fillna(0)
        d = combined.pivot(columns='Defend', values='Constant').fillna(0)

        teams = a - d
        teams['Home'] = combined['Home']

        return combined['Goals'], teams

    elif variables == 2:
        """Two variables per team - attack and defend - plus a global home advantage term"""
        combined['Attack'] += '.Attack'
        combined['Defend'] += '.Defend'

        a = combined.pivot(columns='Attack', values='Constant').fillna(0)
        d = combined.pivot(columns='Defend', values='Constant').fillna(0)

        teams = a.merge(-d, left_index=True, right_index=True)
        teams['Home'] = combined['Home']

        return combined['Goals'], teams

    elif variables == 3:
        """Three variables per team for attack, defend and home advantage"""
        combined['Home Advantage'] = combined['Attack'] + '.Home'
        combined['Attack'] += '.Attack'
        combined['Defend'] += '.Defend'

        h = combined.pivot(columns='Home Advantage', values='Home').fillna(0)
        a = combined.pivot(columns='Attack', values='Constant').fillna(0)
        d = combined.pivot(columns='Defend', values='Constant').fillna(0)

        teams = a.merge(-d, left_index=True, right_index=True)
        teams = teams.merge(h, left_index=True, right_index=True)

        return combined['Goals'], teams

    elif variables == 4:
        """Four variables per team, with attack and defend, with and without home advantage"""
        combined['Away'] = combined['Constant'] - combined['Home']
        combined['Home Attack'] = combined['Attack'] + '.Home Attack'
        combined['Home Defend'] = combined['Defend'] + '.Home Defend'
        combined['Attack'] += '.Away Attack'
        combined['Defend'] += '.Away Defend'

        ha = combined.pivot(columns='Home Attack', values='Home').fillna(0)
        aa = combined.pivot(columns='Attack', values='Away').fillna(0)
        hd = combined.pivot(columns='Home Defend', values='Away').fillna(0)
        ad = combined.pivot(columns='Defend', values='Home').fillna(0)

        teams = ha.merge(aa, left_index=True, right_index=True)
        teams = teams.merge(-hd, left_index=True, right_index=True)
        teams = teams.merge(-ad, left_index=True, right_index=True)

        return combined['Goals'], teams


def run_model(season='latest', division='E0', variables=2):
    poisson = statsmodels.api.families.Poisson()
    goals, teams = get_data(season, division, variables)

    model = statsmodels.api.GLM(goals, teams, poisson)
    result = model.fit()

    print(result.summary())

    return result

if __name__ == '__main__':
    run_model()
