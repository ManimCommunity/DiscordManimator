import asyncio

import discord
import nest_asyncio
from discord.ext import commands
import requests

nest_asyncio.apply()


class Msearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_link = "https://docs.manim.community/"
        self.res = []

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="msearch", aliases=["ms"])
    async def msearch(self, ctx, *args):
        if len(args) == 0 or len(args) > 1:
            return await ctx.reply(
                "Pass some manim function or class and I will find the "
                "corresponding documentation for you. Example: `!msearch Square`"
                "Remember to not add any spaces."
            )
        arg = args[0]
        if not arg.isidentifier():
            return await ctx.reply(
                f"`{arg}` is not a valid identifier, no class or function can be named like that."
            )

        query_url = f"https://docs.manim.community/_/api/v2/search/?q={arg}&project=manimce&version=stable&language=en"
        try:
            req = requests.get(query_url)
            if req.status_code != 200:
                return await ctx.send("`Failed to query the documentation API. Try again later.`")

            response = req.json()
        except:
            return await ctx.send("`Failed to establish connection. Try again later.`")
        else:
            query_results = response["results"]
            if not query_results:
                embed = discord.Embed(title="No results found", color=0xE8E3E3)
                await ctx.reply(embed=embed, mention_author=False)
                return
            
            title = f"Results for `{arg}`"
            embeds = []

            for ind, result in enumerate(query_results):
                embed = discord.Embed(
                    title=title + f" – {ind+1} / {len(query_results)}",
                    color=0xE8E3E3
                )
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

                embeds.append(embed)

            current_page = 0
            reply_embed = await ctx.reply(
                embed=embeds[current_page], mention_author=False
            )
            await reply_embed.add_reaction("◀️")
            await reply_embed.add_reaction("▶️")
            await reply_embed.add_reaction("\U0001F5D1")

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add",
                        check=lambda reaction, user: user == ctx.author
                        and str(reaction.emoji) in ["◀️", "▶️", "\U0001F5D1"],
                        timeout=60,
                    )
                    if str(reaction.emoji) == "▶️":
                        current_page += 1
                        current_page = current_page % len(embeds)
                        await reply_embed.edit(embed=embeds[current_page])
                        await reply_embed.remove_reaction(reaction, ctx.author)

                    elif str(reaction.emoji) == "◀️":
                        current_page -= 1
                        current_page = current_page % len(embeds)
                        await reply_embed.edit(embed=embeds[current_page])
                        await reply_embed.remove_reaction(reaction, ctx.author)

                    elif str(reaction.emoji) == "\U0001F5D1":
                        await reply_embed.delete()
                    else:
                        await reply_embed.remove_reaction(reaction, ctx.author)

                except asyncio.TimeoutError:
                    await reply_embed.clear_reactions()


def setup(bot):
    bot.add_cog(Msearch(bot))
