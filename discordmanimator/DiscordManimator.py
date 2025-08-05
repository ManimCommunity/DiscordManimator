import asyncio
import os
import traceback

import discord
import logging

from discord.ext import commands
from pathlib import Path

def create_and_run_bot(config):
    intents = discord.Intents.default()
    intents.message_content = True

    discord.utils.setup_logging()

    bot = commands.Bot(
        description="Manim Community Discord Bot",
        activity=discord.Game("Animating with Manim"),
        help_command=None,
        command_prefix="!",
        case_insensitive=True,
        strip_after_prefix=True,
        intents=intents,
    )


    @bot.event
    async def on_ready():
        logging.info(f"Logged in as {bot.user.name}")
        await bot.tree.sync()


    async def load_cogs():
        for extension in os.listdir(Path(__file__).parent / "cogs/"):
            if extension.endswith(".py"):
                try:
                    await bot.load_extension(f"discordmanimator.cogs.{extension[:-3]}")
                except Exception:
                    logging.error(f"{extension} couldn't be loaded.")
                    traceback.print_exc()


    asyncio.run(load_cogs())

    return bot
