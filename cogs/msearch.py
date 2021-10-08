import asyncio

import discord
import nest_asyncio
from discord.ext import commands
from requests_html import AsyncHTMLSession

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
        self.res = []
        pages = 0
        if not arg.isidentifier():
            return await ctx.reply(
                f"`{arg}` is not a valid identifier, no class or function can be named like that."
            )

        query_url = f"https://docs.manim.community/en/stable/search.html?q={arg}&check_keywords=yes&area=default#"
        try:
            session = AsyncHTMLSession()
            response = await session.get(query_url)
        except:
            return await ctx.send("`Failed to Establish Connection. Try again Later!`")
        else:
            await response.html.arender(sleep=2)
            await session.close()
            about = response.html.find(".search", first=True)
            a = about.find("li")
            pages = len(a)

            if pages == []:
                self.title = "`No Results Found`"
            else:
                self.title = f"`Results for: {arg}`"

            for i in range(pages):
                desc = (
                    f'[`{a[i].text}`]({str(list(a[i].find("a")[0].absolute_links)[0])})'
                )
                embed = discord.Embed(
                    title=self.title, description=desc, color=0xE8E3E3
                )
                self.res.append(embed)
            cur_page = 0
            reply_embed = await ctx.reply(
                embed=self.res[cur_page], mention_author=False
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
                    if str(reaction.emoji) == "▶️" and cur_page != pages:
                        cur_page += 1
                        await reply_embed.edit(embed=self.res[cur_page])
                        await reply_embed.remove_reaction(reaction, ctx.author)

                    elif str(reaction.emoji) == "◀️" and cur_page > 0:
                        cur_page -= 1
                        await reply_embed.edit(embed=self.res[cur_page])
                        await reply_embed.remove_reaction(reaction, ctx.author)

                    elif str(reaction.emoji) == "\U0001F5D1":
                        await reply_embed.delete()
                    else:
                        await reply_embed.remove_reaction(reaction, ctx.author)

                except asyncio.TimeoutError:
                    await reply_embed.clear_reactions()


def setup(bot):
    bot.add_cog(Msearch(bot))
