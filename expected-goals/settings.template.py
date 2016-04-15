from pymongo import MongoClient

client = MongoClient()
if client:
    events = client.whoscored.events
    models = client.whoscored.expectedgoals
    regions = client.whoscored.regions
    tournaments = client.whoscored.tournaments
    seasons = client.whoscored.seasons
    stages = client.whoscored.stages
    matches = client.whoscored.matches
    teams = client.whoscored.teams
    players = client.whoscored.players
else:
    events = None
    models = None
    regions = None
    tournaments = None
    seasons = None
    stages = None
    matches = None
    teams = None
    players = None
