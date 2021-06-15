import argparse
import asyncio
import discord
import config
import os
import traceback

import black
import discord
import docker
from discord.ext import commands
from pathlib import Path


class Manim(commands.Bot):
    def __init__(self):                     
        manim_intents = {
                        'guilds': True, 
                        'members': True, 
                        'messages': True, 
                        'reactions': True, 
                        'presences': True
                        }
        intents = discord.Intents(**manim_intents)   
        super().__init__(command_prefix = config.PREFIX,
                         case_insensitive = False,
                         self_bot = False,
                         description = "Manim Community Discord Bot",                    
                         intents = intents,
                         help_command = None
        )
        for extension in os.listdir("cogs/"):
            try:
                self.load_extension(f"cogs.{extension[:-3]}")
            except:                
                print(f'{extension} couldn\'t be loaded')



    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name='The Waiting Game'))
        print(f'Logged in as {self.user.name}')
        return




bot = Manim()
bot.run(config.TOKEN, bot=True, reconnect=True)
traceback.print_exc()


