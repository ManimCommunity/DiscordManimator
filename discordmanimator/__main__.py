import argparse
import toml

import discordmanimator

from pathlib import Path

from .DiscordManimator import create_and_run_bot


parser = argparse.ArgumentParser(prog="DiscordManimator")
parser.add_argument("configfile", help="Path to the configfile", type=Path)
args = parser.parse_args()

discordmanimator.config = config = toml.load(args.configfile)

manimator_bot = create_and_run_bot(config=config)
manimator_bot.command_prefix = config.get("PREFIX")

manimator_bot.run(config.get("TOKEN"))
