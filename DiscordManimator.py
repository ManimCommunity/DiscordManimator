import os
import traceback

import config
import discord
from discord.ext import commands

bot = commands.Bot(
    description="Manim Community Discord Bot",
    activity=discord.Game("Animating with manim"),
    help_command=None,
    command_prefix=config.PREFIX,
    case_insensitive=True,
    strip_after_prefix=True,
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


if __name__ == "__main__":
    for extension in os.listdir("cogs/"):
        if extension.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{extension[:-3]}")
            except Exception:
                print(f"{extension} couldn't be loaded.")
                traceback.print_exc()
                print("")

bot.run(config.TOKEN)
