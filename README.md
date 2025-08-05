# DiscordManimator

A Manim Rendering Bot for Discord.

## How to run

Prerequisites:
- Docker dameon running with the `manimcommunity/manim:stable` image pulled
- `uv`, a python dependency manager
- A discord bot token with the `MESSAGE CONTENT` Intent enabled.

Deployment:
- run `uv sync`
- create a new config file `config.toml` based on the template given in `example.config.toml`
- run `uv run python -m discordmanimator path/to/config.toml`
