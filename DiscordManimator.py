import asyncio
import os
import traceback

import config
import discord
import logging

from discord.ext import commands
from pathlib import Path

intents = discord.Intents.default()
intents.message_content = True

discord.utils.setup_logging()

bot = commands.Bot(
    description="Manim Community Discord Bot",
    activity=discord.Game("Animating with Manim"),
    help_command=None,
    command_prefix=config.PREFIX,
    case_insensitive=True,
    strip_after_prefix=True,
    intents=intents
)


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user.name}")
    await bot.tree.sync()

async def load_cogs():
    for extension in os.listdir(Path(__file__).parent/"cogs/"):
        if extension.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{extension[:-3]}")
            except Exception:
                logging.error(f"{extension} couldn't be loaded.")
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(load_cogs())


bot.run(config.TOKEN)
