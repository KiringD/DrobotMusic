import configparser

class ConfigKeys:
    config = configparser.ConfigParser()
    config.read("config.ini")

    TOKEN = config["Nextcord"]['TOKEN']
