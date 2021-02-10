# DiscordManimator

A Manim Rendering Bot for Discord. Requires a working `docker` environment: the `manimcommunity/manim:stable` image is used for rendering.


### Deploying the Bot

After obtaining a Discord bot token, add a `.env` file containing the line
```
DISCORD_TOKEN=<insert bot token here>
```
to this directory. The bot is then started by running `python DiscordManimator.py`.





