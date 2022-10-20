import asyncio

import nextcord
from nextcord.ext import commands

from .handlers import register_all_handlers
from .misc import ConfigKeys


# from refactor.database.models import register_models


def __on_start_up(bot):
    register_all_handlers(bot)

    # register_models()

async def __on_shutdown():
    pass


def start_bot():
    intents = nextcord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='=', intents=intents)
    __on_start_up(bot)
    bot.run(ConfigKeys.TOKEN)
