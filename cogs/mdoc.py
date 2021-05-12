import discord
from discord.ext import commands
#from bs4 import BeautifulSoup
from requests_html import AsyncHTMLSession
import nest_asyncio

nest_asyncio.apply()


class Mdoc(commands.Cog):
    def __init__(self, bot):        
        self.bot = bot
        self.base_link = 'https://docs.manim.community/'
        self.res = []

    @commands.command(name = 'mdoc')
    async def mdocs(self, ctx, *args):
        if len(args) == 0 or len(args) > 1:
            return await ctx.reply(
                "Pass some manim function or class and I will find the "
                "corresponding documentation for you. Example: `!mdoc Square`"
                "Remember to not add any spaces."
            ) 
        arg = args[0]
        if not arg.isidentifier():
            return await ctx.reply(f"`{arg}` is not a valid identifier, no class or function can be named like that.")     

        query_url = f'https://docs.manim.community/en/stable/search.html?q={arg}&check_keywords=yes&area=default#'
        try:
            session = AsyncHTMLSession()
            response = await session.get(query_url)
        except:
            return await ctx.send('`Failed to Establish Connection. Try again Later!`')            
        else:
            await response.html.arender(sleep=2)
            about = response.html.find('.search', first=True)
            a = about.find('li')
            for i in range(2):
                self.res.append(f'[`{a[i].text}`]({self.base_link + str(a[i].find("a")[0].text)})')                
            
        if self.res == []:            
            self.title = '`No Results Found`'
        else:
            self.title = f'`Results for: {arg}`'

        embed = discord.Embed(title = self.title, 
                            description = '\n'.join(self.res),
                            color = 0xe8e3e3)

        return await ctx.reply(embed = embed, mention_author=False)                            

def setup(bot):
    bot.add_cog(Mdoc(bot))                            