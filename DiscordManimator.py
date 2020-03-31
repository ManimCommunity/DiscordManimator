import os
import shutil
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
import list_imports

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(
    command_prefix="!",              # Set the prefix
    description="I render simple Manim Scripts.",  # Set a description for the bot           
    case_insensitive=False                   # Make the commands case sensitive
)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='Waiting... for Manim code.'))
    print(f'Logged in as {bot.user.name}')  # Print the name of the bot logged in.
    return

@bot.command()
async def manimate(ctx,*,arg):
    
    try:
        script=re.search(r"^```(.*)```$",arg,flags=re.DOTALL).group(1)
        
        if script.startswith("python"):
            script=script[6:]
        elif script.startswith("py"):
            script=script[2:]

        scenename=str(re.search(r"^class (.*) ?\(.*?$",script,flags=re.M).group(1)).rstrip()

        imports = list_imports.parse(script)
        
        for package in imports:
            if package not in ["manimlib.imports","manimlib.constants","numpy","scipy"]:
                raise Exception("Your code imports system modules. Can't have that happening!")
            else:
                pass

    except Exception as error:
        await ctx.send("Couldn't parse your code... Sorry!"+"\n```"+str(error)+"```")
        script=None
    
    if bool(script):
        try:
            open("temporary.py","w+").write(script)
        except Exception as error:
            await ctx.send("Couldn't write your code to an internal file... Sorry!"+"\n```"+str(error)+"```")

        try:
            os.system("cd /Users/aathishs/Python/ManimEnv && source bin/activate && cd manim && python manim.py /Users/aathishs/Python/ManimatorEnv/temporary.py -l --media_dir /Users/aathishs/Python/ManimatorEnv/tempmedia ")
        except Exception as error:
            await ctx.send("Manim couldn't render your file... Sorry!"+"\n```"+str(error)+"```")
        
        try:
            filepath="tempmedia/videos/temporary/480p15/"+scenename+".mp4"
            await ctx.send("Here you go:",file=discord.File(filepath))
        except Exception as error:
            await ctx.send("Couldn't send you your video... Sorry!"+"\n```"+str(error)+"```")
        
        os.remove("temporary.py")
        
    shutil.rmtree("tempmedia")
    os.mkdir("tempmedia")

bot.run(TOKEN, bot=True, reconnect=True)