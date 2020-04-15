import os
import subprocess
import shutil
from dotenv import load_dotenv

import re
import shlex

import list_imports

import discord
from discord.ext import commands

import docker
from docker.types import Mount

dockerclient=docker.from_env()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(
    command_prefix="!",
    description="I render simple Manim Scripts.",
    case_insensitive=False
)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='The Waiting Game'))
    print(f'Logged in as {bot.user.name}')  # Print the name of the bot logged in.
    return

@bot.command()
async def mhelp(ctx):
    await ctx.send(
            '''A Simple Manim Rendering Bot.
            Use the !manimate command to render short and simple Manim scripts.
            Code must be properly formatted, and indented.
            Tags supported:
                -w,-s,-i,-t,-a,-n,-r,-c
                --write_to_movie, --save_last_frame,
                --save_as_gif,--transparent,--write_all
            Ex:
            !manimate -l
            ```py
            ```
            ''')

@bot.command()
async def manimate(ctx,*,arg):
    name=ctx.author.mention
    async with ctx.typing():
        try:
            res_tag="480"
            tagstring=re.search(r"(-.*)?^```(.*)```$",arg,flags=re.DOTALL|re.M).group(1)
            
            if tagstring != None:
                tags=shlex.split(tagstring)
                valid_tags=[
                        "-w","-write_to_movie",
                        "-s","-save_last_frame",
                        "-l","--low_quality",
                        "-i","--save_as_gif",
                        "-t","--transparent",
                        "-a","--write_all",
                        "-n",
                        "-r",
                        "-c"
                        ]
                for i in range(0,len(tags)):
                        tag=tags[i]
                        if tag in ["-n","-c"]:
                            tags[i]+=" "+tags[i+1]
                        elif tag=="-r":
                            reso=tags[i+1]
                            res_tag=""
                            res_l= [int(v) for v in reso.split(",")]
                            if res_l[0]>1280 or res_l[1]>720:
                                res_tag="480"
                                tags[i]+=' "480,854"'
                            else:
                                tags[i]+=" "+tags[i+1]
                                res_tag=str(res_l[0])
                        else:
                            pass

                for tag in tags:
                    if tag.startswith(tuple(valid_tags))==False:
                        tags.remove(tag)

                tagstring=" ".join(tags)
            else:
                tagstring=""

            script=re.search(r"(-.*)?^```(.*)```$",arg,flags=re.DOTALL|re.M).group(2)
            
            if script.startswith("python"):
                script=script[6:]
            elif script.startswith("py"):
                script=script[2:]
            
            script=script.strip()

            if script.startswith("def"):            
                script="""from manimlib.imports import *
class test(Scene):
    """ +"\n    ".join(re.findall('(?:"[^"]*"|.)+|(?!\Z)',script))
            
            scenename=str(re.search(r"^class (.*) ?\(.*?$",script,flags=re.M).group(1)).rstrip()

            imports = list_imports.parse(script)

            for package in imports:
                if package not in ["manimlib.imports","manimlib.constants","numpy","scipy"]:
                    raise Exception("Your code imports system modules. Can't have that happening!")
                else:
                    pass

        except Exception as error:
            await ctx.send(str(name)+" Couldn't parse your code... Sorry!"+"\n```"+str(error)+"```")
            script=None

        if bool(script):
            try:
                open("TempManim/temporary.py","w+").write(script)
            except Exception as error:
                await ctx.send(str(name)+" Couldn't write your code to an internal file... Sorry!"+"\n```"+str(error)+"```")

            cmd="timeout 180 python3 /root/manim/manim.py /root/manim/TempManim/temporary.py --media_dir /root/manim/TempManim -l " + tagstring
            
            try:
                dockerclient.containers.run(
                        image="manimimage",
                        auto_remove=True, 
                        mounts=[ Mount(target="/root/manim/TempManim",source="TempManim")], 
                        command=cmd)
            except Exception as error:
                await ctx.send(str(name)+" Manim couldn't render your file... Sorry!"+"\n```"+str(error)+"```")
            
            filepath="/root/ManimatorEnv/TempManim/videos/temporary/images/"+scenename+".png" if "-s" in tags else "/root/ManimatorEnv/TempManim/videos/temporary/"+res_tag+"p15/"+scenename+".mp4"

            
            try:
                await ctx.send(str(name)+" Here you go:",file=discord.File(filepath))
            except Error as error:
                await ctx.send(str(name)+" Couldn't send you your video... Sorry!"+"\n```"+str(error)+"```")
           
            os.remove("TempManim/temporary.py")
        shutil.rmtree("TempManim/Tex")
        shutil.rmtree("TempManim/texts")
        shutil.rmtree("TempManim/videos")
        shutil.rmtree("TempManim/__pycache__")

bot.run(TOKEN, bot=True, reconnect=True)
