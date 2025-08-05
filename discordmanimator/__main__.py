import argparse
import toml

from pathlib import Path

from .DiscordManimator import create_and_run_bot


parser = argparse.ArgumentParser(prog="DiscordManimator")
parser.add_argument("configfile", help="Path to the configfile", type=Path)
args = parser.parse_args()

config = toml.load(args.configfile)

create_and_run_bot(config=config)
