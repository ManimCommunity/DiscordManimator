import asyncio
import discord
import docker
import os
import tempfile
import re
import io

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
    -t, --transparent, -i, --save_as_gif, -s, --save_last_frame
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

@bot.command(aliases=['m'])
@commands.guild_only()
async def manimate(ctx, *, arg):

    def construct_reply(arg):
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
            reply_args = {"content": "You cannot pass CLI flags other than "
                            "`-i` (`--save_as_gif`), `-s` (`--save_last_frame`), "
                            "`-t` (`--transparent`)."}
            return reply_args
        else:
            cli_flags = ' '.join(cli_flags)

        body = '\n'.join(body).strip()

        if body.count('```') != 2:
            reply_args = {
                "content": 'Your message is not properly formatted. '
                'Your code has to be written in a code block, like so:\n'
                '\\`\\`\\`py\nyour code here\n\\`\\`\\`'
            }
            return reply_args

        script=re.search(
            pattern = r"```(?:py)?(?:thon)?(.*)```",
            string = body,
            flags=re.DOTALL,
        ).group(1)
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
            with open(scriptfile, 'w', encoding='utf-8') as f:
                f.write('\n'.join(script))
            try: # now it's getting serious: get docker involved
                reply_args = None
                container_stderr = dockerclient.containers.run(
                    image="manimcommunity/manim:stable",
                    volumes={tmpdirname: {'bind': '/manim/', 'mode': 'rw'}},
                    command=f"timeout 120 manim -qm --disable_caching --progress_bar=none -o scriptoutput {cli_flags} /manim/script.py",
                    user=os.getuid(),
                    stderr=True,
                    stdout=False,
                    remove=True
                )
                if container_stderr:
                    if len(container_stderr.decode('utf-8')) <= 1200:
                        reply_args = {
                            "content": "Something went wrong, here is "
                            "what Manim reports:\n"
                            f"```\n{container_stderr.decode('utf-8')}\n```"
                        }
                    else:
                        reply_args = {
                            "content": "Something went wrong, here is "
                            "what Manim reports:\n",
                            "file": discord.File(
                                fp=io.BytesIO(container_stderr),
                                filename="Error.log",
                            )
                        }

                    return reply_args

            except Exception as e:
                reply_args = {"content": f"Something went wrong: ```{e}```"}
                raise e
            finally:
                if reply_args:
                    return reply_args

            try:
                [outfilepath] = Path(tmpdirname).rglob('scriptoutput.*')
            except Exception as e:
                reply_args = {"content": "Something went wrong: no (unique) output file was produced. :cry:"}
                raise e
            else:
                reply_args = {"content": "Here you go:", "file": discord.File(outfilepath)}
            finally:
                return reply_args

    async def react_and_wait(reply):
        await reply.add_reaction("\U0001F5D1") # Trashcan emoji

        def check(reaction, user):
            return str(reaction.emoji) == '\U0001F5D1' and user == ctx.author

        try:
            reaction, user = await bot.wait_for('reaction_add', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await reply.remove_reaction("\U0001F5D1", bot.user)
        else:
            await reply.delete()

    async with ctx.typing():
        reply_args = construct_reply(arg)
        reply = await ctx.reply(**reply_args)

    await react_and_wait(reply)
    return


@bot.command()
@commands.guild_only()
async def mdoc(ctx, *args):
    if len(args) == 0:
        await ctx.reply(
            "Pass some manim function or class and I will find the "
            "corresponding documentation for you. Example: `!mdoc Square`"
        )
        return

    arg = args[0]
    if not arg.isidentifier():
        await ctx.reply(f"`{arg}` is not a valid identifier, no class or function can be named like that.")
        return

    try:
        container_output = dockerclient.containers.run(
            image="manimcommunity/manim:stable",
            command=f"""timeout 10 python -c "import manim; assert '{arg}' in dir(manim); print(manim.{arg}.__module__ + '.{arg}')" """,
            user=os.getuid(),
            stderr=False,
            stdout=True,
            detach=False,
            remove=True
        )
    except docker.errors.ContainerError as e:
        if 'AssertionError' in e.args[0]:
            await ctx.reply(f"I could not find `{arg}` in our documentation, sorry.")
            return
        await ctx.reply(f"Something went wrong: ```{e.args[0]}```")
        return
    
    fqname = container_output.decode("utf-8").strip()
    url = f"https://docs.manim.community/en/stable/reference/{fqname}.html"
    await ctx.reply(f"Here you go: {url}")
    return
    

bot.run(TOKEN, bot=True, reconnect=True)
