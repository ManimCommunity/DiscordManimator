import discord
from discord.ext import commands


class errorHandler(commands.Cog):
    """
    Error Handler cog that handles bot errors globally
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Triggered when a valid command catches an error
        """

        if isinstance(error, commands.CommandNotFound):
            title = "Command not found"
            description = f"No command {ctx.invoked_with} found. Please try again."
        elif isinstance(error, commands.CommandOnCooldown):
            title = "You are on cooldown"
            description = f"Please try again in {int(error.retry_after)} seconds"
        else:
            title = "Unhandled error"
            description = f"An Unhandled exception occured, if this happens frequently please report to bot devs.\n{error}"

        if title and description:
            await ctx.reply(
                embed=discord.Embed(
                    title=title, description=description, color=discord.Color.red()
                ),
                mention_author=True,
            )


def setup(bot):
    bot.add_cog(errorHandler(bot))
