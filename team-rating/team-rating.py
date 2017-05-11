import requests
import pandas.io.json
import patsy
import statsmodels.api


def get_data(season, division, variables=1):
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

    if variables == 1:
        """One variable per team, plus a global home advantage term"""
        pass

    elif variables == 2:
        """Two variables per team - attack and defend - plus a global home advantage term"""

        return patsy.dmatrices('Goals ~ Home + Attack + Defend - 1', data=combined, return_type='dataframe')

    elif variables == 3:
        """Three variables per team for attack, defend and home advantage"""
        pass

    elif variables == 4:
        """Four variables per team, with attack and defend, with and without home advantage"""
        pass


def run_model(season='latest', division='E0'):
    poisson = statsmodels.api.families.Poisson()
    goals, teams = get_data(season, division, variables=2)

    model = statsmodels.api.GLM(goals, teams, poisson)
    result = model.fit()

    print(result.summary())

    return result

if __name__ == '__main__':
    run_model()
