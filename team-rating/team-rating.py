import requests
import statsmodels.api


def get_data(season='latest', division='E0'):
    url = 'https://api.project-hanoi.co.uk/football-data/v1/{0}/{1}'.format(season, division)
    response = requests.get(url)

    goals, teams = list(), list()

    for record in response.json():
        goals.append(record['Full Time']['Home'])
        teams.append({'Home': True, 'Attack': record['Home'], 'Defend': record['Away']})

        goals.append(record['Full Time']['Away'])
        teams.append({'Home': False, 'Attack': record['Away'], 'Defend': record['Home']})

    return goals, teams


def run_model():
    goals, teams = get_data()

    model = statsmodels.api.GLM(endog=goals, exog=teams)
    result = model.fit()

    print(result.summary())

    return result

if __name__ == '__main__':
    run_model()
