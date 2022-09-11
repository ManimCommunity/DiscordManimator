from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mhelp")
    async def mhelp(self, ctx):
        await ctx.send(
            """A simple Manim rendering bot.

Use the `!manimate` command to render short and simple Manim scripts.
Code **must** be properly formatted and indented. Note that you can't animate through DM's.

Supported tags:
```
    -i (--format=gif), -s (--save_last_frame), -t (--transparent), --renderer=opengl, --use_projection_fill_shaders, --use_projection_stroke_shaders
```
Example:
```
!manimate -s
\`\`\`py
def construct(self):
    self.play(ReplacementTransform(Square(), Circle()))
\`\`\`
```
"""
        )


def setup(bot):
    bot.add_cog(Help(bot))
