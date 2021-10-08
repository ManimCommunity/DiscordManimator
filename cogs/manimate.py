import asyncio
import io
import os
import re
import tempfile
import traceback
from pathlib import Path

import discord
from discord.ext import commands

# If you don't want to use docker, set NO_DOCKER to True
# where-ever you define environment variables.
if "NO_DOCKER" in os.environ:
    import subprocess

    NO_DOCKER = os.getenv("NO_DOCKER") == "True"
    # If you want to use manim-onlinetex, set USE_ONLINETEX to True
    # whereever you define environment variables.
    # If you want to use manim-onlinetex, set TEX_DIR to somewhere that won't be erased in a new manim.cfg
    USE_ONLINETEX = (
        os.getenv("USE_ONLINETEX") == "True" if "USE_ONLINETEX" in os.environ else False
    )
else:
    import docker

    dockerclient = docker.from_env()

class Manimate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name="manimate", aliases=["m"])
    @commands.guild_only()
    async def manimate(self, ctx, *, arg):
        def construct_reply(arg):
            if arg.startswith("```"):  # empty header
                arg = "\n" + arg
            header, *body = arg.split("\n")

            cli_flags = header.split()
            allowed_flags = [
                "-i",
                "--save_as_gif",
                "-s",
                "--save_last_frame",
                "-t",
                "--transparent",
                "--renderer=opengl"
            ]

            if not all([flag in allowed_flags for flag in cli_flags]):
                reply_args = {
                    "content": "You cannot pass CLI flags other than "
                    "`-i` (`--save_as_gif`), `-s` (`--save_last_frame`), "
                    "`-t` (`--transparent`), or `--renderer=opengl`."
                }
                return reply_args
            if "--renderer=opengl" in cli_flags:
                cli_flags.append("--write_to_movie")
            cli_flags = " ".join(cli_flags)


            body = "\n".join(body).strip()

            if body.count("```") != 2:
                reply_args = {
                    "content": "Your message is not properly formatted. "
                    "Your code has to be written in a code block, like so:\n"
                    "\\`\\`\\`py\nyour code here\n\\`\\`\\`"
                }
                return reply_args

            script = re.search(
                pattern=r"```(?:py)?(?:thon)?(.*)```",
                string=body,
                flags=re.DOTALL,
            ).group(1)
            script = script.strip()

            # for convenience: allow construct-only:
            if script.startswith("def construct(self):"):
                script = ["class Manimation(Scene):"] + [
                    "    " + line for line in script.split("\n")
                ]
            else:
                script = script.split("\n")

            script = ["from manim import *", "from manim_onlinetex import *"] + script if USE_ONLINETEX else ["from manim import *"] + script

            # write code to temporary file (ideally in temporary directory)
            with tempfile.TemporaryDirectory() as tmpdirname:
                scriptfile = Path(tmpdirname) / "script.py"
                with open(scriptfile, "w", encoding="utf-8") as f:
                    f.write("\n".join(script))
                try:  # now it's getting serious: get docker involved
                    reply_args = None

                    if NO_DOCKER:
                        proc = subprocess.run(
                            f"timeout 120 manim -ql --media_dir {tmpdirname} -o scriptoutput {'--config_file manim.cfg' if USE_ONLINETEX else ''} {cli_flags} {scriptfile}",
                            shell=True,
                            stderr=subprocess.PIPE,
                        )
                        manim_stderr = proc.stderr
                    else:
                        manim_stderr = dockerclient.containers.run(
                            image="manimcommunity/manim:stable",
                            volumes={tmpdirname: {"bind": "/manim/", "mode": "rw"}},
                            command=f"timeout 120 manim -qm --disable_caching --progress_bar=none -o scriptoutput {cli_flags} /manim/script.py",
                            user=os.getuid(),
                            stderr=True,
                            stdout=False,
                            remove=True,
                        )
                    if manim_stderr:
                        if len(manim_stderr.decode("utf-8")) <= 1200:
                            reply_args = {
                                "content": "Something went wrong, here is "
                                "what Manim reports:\n"
                                f"```\n{manim_stderr.decode('utf-8')}\n```"
                            }
                        else:
                            reply_args = {
                                "content": "Something went wrong, here is "
                                "what Manim reports:\n",
                                "file": discord.File(
                                    fp=io.BytesIO(manim_stderr),
                                    filename="Error.log",
                                ),
                            }

                        return reply_args

                except Exception as e:
                    if isinstance(e, docker.errors.ContainerError):
                        tb = e.stderr
                    else:
                        tb = str.encode(traceback.format_exc())
                    reply_args = {
                        "content": f"Something went wrong, the error log is attached. :cry:",
                        "file": discord.File(fp=io.BytesIO(tb), filename="error.log"),
                    }
                    raise e
                finally:
                    if reply_args:
                        return reply_args

                try:
                    [outfilepath] = Path(tmpdirname).rglob("scriptoutput.*")
                except Exception as e:
                    reply_args = {
                        "content": "Something went wrong: no (unique) output file was produced. :cry:"
                    }
                    raise e
                else:
                    reply_args = {
                        "content": "Here you go:",
                        "file": discord.File(outfilepath),
                    }
                finally:
                    return reply_args

        async def react_and_wait(reply):
            await reply.add_reaction("\U0001F5D1")  # Trashcan emoji

            def check(reaction, user):
                return str(reaction.emoji) == "\U0001F5D1" and user == ctx.author

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check, timeout=60.0
                )
            except asyncio.TimeoutError:
                await reply.remove_reaction("\U0001F5D1", self.bot.user)
            else:
                await reply.delete()

        async with ctx.typing():
            reply_args = construct_reply(arg)
            reply = await ctx.reply(**reply_args)

        await react_and_wait(reply)
        return


def setup(bot):
    bot.add_cog(Manimate(bot))
