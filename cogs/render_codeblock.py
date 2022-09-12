from __future__ import annotations

import discord
import io
import logging
import re
import tempfile
import traceback
import os

import config

from discord.ext import commands
from pathlib import Path

import docker
dockerclient = docker.from_env()

class RenderCodeblock(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        if extract_manim_snippets(message.content):
            await message.reply(
                "This message looks like it contains a Manim snippet, "
                "do you want me to render it?",
                view=RenderView()
            )


class RenderView(discord.ui.View):
    @discord.ui.button(
        label='Yes, render',
        style=discord.ButtonStyle.blurple,
    )
    async def render(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        async with interaction.channel.typing():
            code_message = await interaction.channel.fetch_message(
                interaction.message.reference.message_id
            )
            response = render_animation_snippet(code_message)

            button.label = "Render again"
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                view=self,
                **response
            )

    @discord.ui.button(
        label='Change settings',
        style=discord.ButtonStyle.secondary,
    )
    async def change_settings(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(SettingsModal())

    @discord.ui.button(
        label='Go away',
        style=discord.ButtonStyle.red,
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.message.delete()


class SettingsModal(discord.ui.Modal, title='Change render settings'):
    CLI_flags = discord.ui.TextInput(
        label='CLI flags',
        placeholder='--renderer=cairo',
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if ';' in self.CLI_flags.value or '&' in self.CLI_flags.value:
            await interaction.response.send_message(
                f'Something went wrong, please try again.',
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        async with interaction.channel.typing():
            code_message = await interaction.channel.fetch_message(
                interaction.message.reference.message_id
            )
            response = render_animation_snippet(
                code_message,
                cli_flags=self.CLI_flags.value
            )
            view = RenderView()
            view.children[0].label = "Render again"
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                view=view,
                **response
            )


def extract_manim_snippets(msg) -> None | str:
    pattern = re.compile(r"```(?:py|python)?([^`]*def construct[^`]*)```")
    return pattern.findall(msg)

def render_animation_snippet(code_message, cli_flags=None) -> discord.File:
    if cli_flags is None:
        cli_flags = ""

    # theoretically, multiple snippets could be rendered
    # at once. for now, we'll just choose and render the
    # first one.
    [snippet, *rest] = extract_manim_snippets(code_message.content)
    snippet = snippet.strip()

    if snippet.startswith("def construct(self):"):
        snippet = ["class Manimation(Scene):"] + [
            "    " + line for line in snippet.split("\n")
        ]
    else:
        snippet = snippet.split("\n")

    prescript = ["from manim import *"]
    if config.USE_ONLINETEX:
        prescript.append("from manim_onlinetex import *")
    script = prescript + snippet

    with tempfile.TemporaryDirectory() as tmpdirname:
        with open(Path(tmpdirname) / "script.py", "w", encoding="utf-8") as f:
            f.write("\n".join(script))

        try:
            reply_args = None
            manim_stderr = dockerclient.containers.run(
                image="manimcommunity/manim:stable",
                volumes={tmpdirname: {"bind": "/manim/", "mode": "rw"}},
                command=f"timeout 120 manim -qm --disable_caching --progress_bar=none -o scriptoutput {cli_flags} /manim/script.py",
                user=os.getuid(),
                stderr=True,
                stdout=False,
                remove=True,
            )
            if manim_stderr:
                raise ManimError(traceback=manim_stderr)
        except Exception as e:
            if isinstance(e, ManimError):  # manim itself threw an error
                reply_args = {
                    "content": "Something went wrong! :cry: Here is what Manim reports.",
                    "attachments": [
                        discord.File(
                            fp=io.BytesIO(e.traceback),
                            filename="error.log",
                        ),
                    ]
                }
            else:
                if isinstance(e, docker.errors.ContainerError):
                    # communication with docker yields error
                    tb = e.stderr
                else:
                    # something else (?) went wrong
                    tb = str.encode(traceback.format_exc())
                reply_args = {
                    "content": f"Something went wrong, the error log is attached. :cry:",
                    "attachments": [
                        discord.File(fp=io.BytesIO(tb), filename="error.log"),
                    ],
                }
                return reply_args

        try:
            [outfilepath] = Path(tmpdirname).rglob("scriptoutput.*")
        except Exception as e:
            reply_args = {
                "content": "Something went wrong: no (unique) output file was produced. :cry:"
            }
        else:
            reply_args = {
                "content": "Here you go!",
                "attachments": [discord.File(outfilepath),],
            }
        finally:
            return reply_args

async def setup(bot: commands.Bot):
    """Entrypoint of loading the bot extension."""
    await bot.add_cog(RenderCodeblock(bot))
    logging.info("RenderCodeblock cog has been added.")

class ManimError(ChildProcessError):
    def __init__(self,traceback):
        self.traceback = traceback