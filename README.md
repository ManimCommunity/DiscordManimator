# DiscordManimator

A Manim Rendering Bot for Discord.

## How to run

Prerequisites:
- Docker dameon running with the `manimcommunity/manim:stable` image pulled
- `poetry`, a python dependency manager
- A discord bot token with the `MESSAGE CONTENT` Intent enabled.

Deploy:
- run `poetry install`
- make a new file `config.py` in this directory based on `config_example.py` including the bot token
- run `poetry run python DiscordManimator.py`
