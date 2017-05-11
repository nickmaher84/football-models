import requests
import pandas.io.json
import patsy
import statsmodels.api


def get_data(season, division):
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

    return patsy.dmatrices('Goals ~ Home + Attack + Defend - 1', data=combined, return_type='dataframe')


def run_model(season='latest', division='E0'):
    poisson = statsmodels.api.families.Poisson()
    goals, teams = get_data(season, division)

    model = statsmodels.api.GLM(goals, teams, poisson)
    result = model.fit()

    print(result.summary())

    return result

if __name__ == '__main__':
    run_model()
