import os
import re
from discord.ext import commands
import config

if config.NO_DOCKER:
    import subprocess
else:
    import docker

    dockerclient = docker.from_env()

validate_version = re.compile(r"latest|stable|v\d\.\d{1,2}\.\d")


class Mdoc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mdoc")
    @commands.guild_only()
    async def mdoc(self, ctx, *args):
        if len(args) == 0:
            await ctx.reply(
                "Pass some manim function or class and I will find the "
                "corresponding documentation for you. Example: `!mdoc Square`"
            )
            return

        arg = args[0].split(".")

        object_or_class = arg[0]
        try:
            method_or_attribute = arg[1]
        except IndexError:
            method_or_attribute = ""

        try:
            version = args[1]
            if validate_version.search(version) is None:
                await ctx.reply(f"Invalid version {version} provided")
                return
        except IndexError:
            version = "stable"


        if not object_or_class.isidentifier():
            await ctx.reply(
                f"`{object_or_class}` is not a valid identifier, no class or function can be named like that."
            )
            return

        try:
            if config.NO_DOCKER:
                errortype = Exception
                proc = subprocess.run(
                    f"""timeout 10 python -c "import manim; assert '{object_or_class}' in dir(manim); print(manim.{object_or_class}.__module__ + '.{object_or_class}')" """,
                    shell=True,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
                if method_or_attribute:
                    method_absence = subprocess.run(
                        f"""timeout 10 python -c "import manim; assert hasattr(manim.{object_or_class}, '{method_or_attribute}')" """,
                        shell=True,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                    )
                    error = method_absence.stderr.decode("utf-8")
                    if error:
                        raise Exception(error)

                error = proc.stderr.decode("utf-8")
                if error:
                    raise Exception(error)
            else:
                errortype = docker.errors.ContainerError
                container_output = dockerclient.containers.run(
                    image="manimcommunity/manim:stable",
                    command=f"""timeout 10 python -c "import manim; assert '{object_or_class}' in dir(manim); print(manim.{object_or_class}.__module__ + '.{object_or_class}')" """,
                    user=os.getuid(),
                    stderr=False,
                    stdout=True,
                    detach=False,
                    remove=True,
                )

                if method_or_attribute:
                    dockerclient.containers.run(
                        image="manimcommunity/manim:stable",
                        command=f"""timeout 10 python -c "import manim; assert hasattr(manim.{object_or_class}, '{method_or_attribute}')" """,
                        user=os.getuid(),
                        stderr=True,
                        stdout=False,
                        detach=False,
                        remove=True,
                    )
        except errortype as e:
            if "AssertionError" in e.args[0]:
                await ctx.reply(
                    f"I could not find `{object_or_class}.{method_or_attribute}` in our documentation, sorry."
                )
                return
            await ctx.reply(f"Something went wrong: ```{e.args[0]}```")
            return

        if config.NO_DOCKER:
            fqname = proc.stdout.decode("utf-8").strip().splitlines()[0]
        else:
            fqname = container_output.decode("utf-8").strip().splitlines()[2]

        url = f"https://docs.manim.community/en/{version}/reference/{fqname}.html#{fqname}.{method_or_attribute}"
        await ctx.reply(f"Here you go: {url}")
        return


def setup(bot):
    bot.add_cog(Mdoc(bot))
