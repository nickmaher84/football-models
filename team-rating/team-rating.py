import requests
import pandas.io.json
import patsy
import statsmodels.api


def get_data(season='latest', division='E0'):
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

    return home.append(away, ignore_index=True)


def run_model():
    goals, teams = patsy.dmatrices('Goals ~ Home + Attack + Defend - 1', data=get_data(), return_type='dataframe')

    model = statsmodels.api.GLM(endog=goals, exog=teams)
    result = model.fit()

    print(result.summary())

    return result

if __name__ == '__main__':
    run_model()
