import discord
import docker
import os
import re
import shutil
import tempfile

from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

dockerclient = docker.from_env()

bot = commands.Bot(
    command_prefix="!",
    description="I render simple Manim Scripts.",
    case_insensitive=False
)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='The Waiting Game'))
    print(f'Logged in as {bot.user.name}')
    return

@bot.command()
async def mhelp(ctx):
    await ctx.send("""A simple Manim rendering bot.

Use the `!manimate` command to render short and simple Manim scripts.
Code **must** be properly formatted and indented. Note that you can't animate through DM's.

Supported tags:
```
    -t, -i, -s
```
Example:
```
!manimate -s
\`\`\`py
def construct(self):
    self.play(ReplacementTransform(Square(), Circle()))
\`\`\`
```
""")

@bot.command()
@commands.guild_only()
async def manimate(ctx, *, arg):
    async with ctx.typing():
        if arg.startswith('```'): # empty header
            arg = '\n' + arg
        header, *body = arg.split('\n')

        cli_flags = header.split()
        allowed_flags = [
            "-i", "--save_as_gif",
            "-s", "--save_last_frame",
            "-t", "--transparent"
        ]
        if not all([flag in allowed_flags for flag in cli_flags]):
            await ctx.reply("You cannot pass CLI flags other than "
                            "`-i` (`--save_as_gif`), `-s` (`--save_last_frame`), "
                            "`-t` (`--transparent`).")
            return
        else:
            cli_flags = ' '.join(cli_flags)

        body = '\n'.join(body).strip()

        if not (body.count('```') == 2
                and body.startswith('```')
                and body.endswith('```')):
            await ctx.reply(
                'Your message is not properly formatted. '
                'Your code has to be written in a code block, like so:\n'
                '\\`\\`\\`py\nyour code here\n\\`\\`\\`'
            )
            return

        if body.startswith('```python'):
            script = body[9:-3]
        elif body.startswith('```py'):
            script = body[5:-3]
        else:
            script = body[3:-3]
        script = script.strip()

        # for convenience: allow construct-only:
        if script.startswith('def construct(self):'):
            script = ['class Manimation(Scene):'] + ["    " + line for line in script.split("\n")]
        else:
            script = script.split("\n")

        script = ["from manim import *"] + script

        # write code to temporary file (ideally in temporary directory)
        with tempfile.TemporaryDirectory() as tmpdirname:
            scriptfile = Path(tmpdirname) / 'script.py'
            with open(scriptfile, 'w') as f:
                f.write('\n'.join(script))
            try: # now it's getting serious: get docker involved
                container_stderr = dockerclient.containers.run(
                    image="manimcommunity/manim:stable",
                    volumes={tmpdirname: {'bind': '/manim/', 'mode': 'rw'}},
                    command=f"timeout 120 manim /manim/script.py -qm -o scriptoutput {cli_flags}",
                    user=os.getuid(),
                    stderr=True,
                    stdout=False,
                    remove=True
                )
                if container_stderr:
                    await ctx.reply("Something went wrong, here is "
                                    "what Manim reports:\n"
                                    f"```\n{container_stderr.decode('utf-8')}\n```")
                    return

            except Exception as e:
                await ctx.reply(f"Something went wrong: ```{e}```")
                raise e

            try:
                [outfilepath] = Path(tmpdirname).rglob('scriptoutput.*')
                await ctx.reply("Here you go:", file=discord.File(outfilepath))
            except Exception as e:
                await ctx.reply("Something went wrong: no (unique) output file was produced. :cry:")

            return

    return


bot.run(TOKEN, bot=True, reconnect=True)
