from requests import Session
from requests.exceptions import Timeout
from datetime import datetime
import re


class FantasyPremierLeague:
    def __init__(self, username=None, password=None, verbose=False):
        self.session = Session()
        self.username = username
        self.password = password
        self.verbose = verbose

    def login(self, username, password):
        url = 'https://users.premierleague.com/'

        response = self.session.get(url)
        response.raise_for_status()

        print('Logging in...')
        token = response.cookies.get('csrftoken')
        data = {
            'csrfmiddlewaretoken': token,
            'login': username,
            'password': password,
            'app': 'plusers',
            'redirect_uri': url
        }
        response = self.session.post(url + 'accounts/login/', data=data)
        response.raise_for_status()

        if self.logged_in():
            print('Logged in.')
        else:
            print('Failed to log in!')
            exit()

        response = self.session.get('https://fantasy.premierleague.com/')
        response.raise_for_status()

    def logged_in(self):
        if self.session.cookies.get('pl_profile'):
            return True
        else:
            return False

    def get_endpoint(self, page, item=None, subpage=None, auth=False):
        if not self.logged_in() and auth:
            self.login(self.username, self.password)

        url = 'https://fantasy.premierleague.com/drf/{0}'.format(page)
        if item is not None:
            url += '/{0}'.format(item)
        if subpage:
            url += '/{0}'.format(subpage)

        try:
            response = self.session.get(url)
        except Timeout:
            print('Timeout. Retrying...')
            response = self.session.get(url)
        if self.verbose:
            print(response.url)
        response.raise_for_status()

        return convert(response.json())

    def events(self):
        return self.get_endpoint('events')

    def players(self):
        return self.get_endpoint('elements')

    def player(self, player_id):
        return self.get_endpoint('element-summary', player_id)

    def positions(self):
        return self.get_endpoint('element-types')

    def fixtures(self):
        return self.get_endpoint('fixtures')

    def teams(self):
        return self.get_endpoint('teams')

    def regions(self):
        return self.get_endpoint('regions')

    def entry(self, entry_id):
        return self.get_endpoint('entry', entry_id)

    def entry_history(self, entry_id):
        return self.get_endpoint('entry', entry_id, 'history')

    def transfers(self):
        return self.get_endpoint('transfers', auth=True)

    def my_team(self, entry_id):
        return self.get_endpoint('my-team', entry_id, auth=True)

    def leagues_entered(self, entry_id):
        return self.get_endpoint('leagues-entered', entry_id, auth=True)

    def leagues_classic(self, league_id):
        return self.get_endpoint('leagues-classic', league_id, auth=True)

    def leagues_classic_standings(self, league_id):
        return self.get_endpoint('leagues-classic-standings', league_id)

    def leagues_h2h(self, league_id):
        return self.get_endpoint('leagues-h2h', league_id, auth=True)

    def leagues_h2h_standings(self, league_id):
        return self.get_endpoint('leagues-h2h-standings', league_id)

    def static_data(self):
        return self.get_endpoint('bootstrap-static')

    def current_status(self):
        return self.get_endpoint('bootstrap-dynamic', auth=True)

    def all_data(self):
        return self.get_endpoint('bootstrap', auth=True)


def convert(json):
    if type(json) is str and re.match(r'^-?\d+\.\d+$', json):
        return float(json)
    elif type(json) is str and re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', json):
        return datetime.strptime(json, '%Y-%m-%dT%H:%M:%SZ')

    elif type(json) is dict:
        for k, v in json.items():
            if type(v) is str and re.match(r'^-?\d+\.\d+$', v):
                json[k] = float(v)
            elif type(v) is str and re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', v):
                json[k] = datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
            elif type(v) is dict:
                json[k] = convert(v)
            elif type(v) is list:
                json[k] = [convert(x) for x in v]

    return json
