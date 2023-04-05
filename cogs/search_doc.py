from __future__ import annotations

import discord
import logging
import requests

from discord import app_commands
from discord.ext import commands


class SearchDocumentation(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(
        description="Submit a query to search https://docs.manim.community.",
    )
    async def search_documentation(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        query_url = f"https://docs.manim.community/_/api/v2/search/?q={query}&project=manimce&version=stable&language=en"
        try:
            req = requests.get(query_url)
            if req.status_code != 200:
                await interaction.followup.send(
                    content="Failed to query the documentation API. Try again later."
                )
                return

            response = req.json()
        except:
            await interaction.followup.send(
                content="Failed to establish a connection. Try again later."
            )
            return
        else:
            query_results = response["results"]
            if not query_results:
                embed = discord.Embed(title="No results found", color=0xE8E3E3)
                await interaction.followup.send(
                    content=f"No results found for `{query}`."
                )
                return
            
            title = f"Documentation results for `{query}`"
            embeds = []

            embed = discord.Embed(
                title=title,
                color=0xE8E3E3
            )

            for ind, result in enumerate(query_results):
                url = result['domain'] + result['path']
                for itm in result['blocks']:
                    itm_name = itm.get("name", None) or itm.get("title", None)
                    itm_prefix = itm.get("role", "")
                    itm_id = itm.get("id", "")
                    if itm_prefix:
                        itm_prefix = f"[{itm_prefix}] "
                    embed.add_field(
                        name=f"{itm_prefix} {itm_name}",
                        value=f"[Go to Documentation]({url}#{itm_id})\n\n{itm['content'][:100]}...",
                        inline=False,
                    )
                # TODO: currently only the first block is processed,
                # some sort of (working) pagination has to be
                # implemented
                break

            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    """Entrypoint of loading the bot extension."""
    await bot.add_cog(SearchDocumentation(bot))
    logging.info("SearchDocumentation cog has been added.")
