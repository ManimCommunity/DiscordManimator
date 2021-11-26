import os
from discord.ext import commands
import config

if config.NO_DOCKER:
    import subprocess
else:
    import docker

    dockerclient = docker.from_env()

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

        arg = args[0]
        if not arg.isidentifier():
            await ctx.reply(
                f"`{arg}` is not a valid identifier, no class or function can be named like that."
            )
            return

        try:
            if config.NO_DOCKER:
                errortype = Exception
                proc = subprocess.run(
                    f"""timeout 10 python -c "import manim; assert '{arg}' in dir(manim); print(manim.{arg}.__module__ + '.{arg}')" """,
                    shell=True,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
                err = proc.stderr.decode("utf-8")
                if err:
                    raise Exception(err)
            else:
                errortype = docker.errors.ContainerError
                container_output = dockerclient.containers.run(
                    image="manimcommunity/manim:stable",
                    command=f"""timeout 10 python -c "import manim; assert '{arg}' in dir(manim); print(manim.{arg}.__module__ + '.{arg}')" """,
                    user=os.getuid(),
                    stderr=False,
                    stdout=True,
                    detach=False,
                    remove=True,
                )
        except errortype as e:
            if "AssertionError" in e.args[0]:
                await ctx.reply(f"I could not find `{arg}` in our documentation, sorry.")
                return
            await ctx.reply(f"Something went wrong: ```{e.args[0]}```")
            return

        if config.NO_DOCKER:
            fqname = proc.stdout.decode("utf-8").strip().splitlines()[0]
        else:
            fqname = container_output.decode("utf-8").strip().splitlines()[2]
        url = f"https://docs.manim.community/en/stable/reference/{fqname}.html"
        await ctx.reply(f"Here you go: {url}")
        return

def setup(bot):
    bot.add_cog(Mdoc(bot))