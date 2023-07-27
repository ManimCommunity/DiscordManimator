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

import aiodocker

# time in seconds after which view (= button row) is removed
VIEW_TIMEOUT = 120


class RenderCodeblock(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        if extract_manim_snippets(message.content):
            view = RenderView(timeout=VIEW_TIMEOUT)
            message = await message.reply(
                "This message looks like it contains a Manim snippet, "
                "do you want me to render it?",
                view=view,
            )
            view.message = message


class RenderView(discord.ui.View):
    @discord.ui.button(
        label="Yes, render",
        style=discord.ButtonStyle.blurple,
    )
    async def render(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        await interaction.response.defer()
        async with interaction.channel.typing():
            code_message = await interaction.channel.fetch_message(
                interaction.message.reference.message_id
            )
            response = await render_animation_snippet(code_message)
            response.pop("cli_flags")

            button.label = "Render again"
            for child in self.children:
                child.disabled = False
            await interaction.followup.edit_message(
                message_id=interaction.message.id, view=self, **response
            )

    @discord.ui.button(
        label="Change settings",
        style=discord.ButtonStyle.secondary,
    )
    async def change_settings(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(SettingsModal())

    @discord.ui.button(
        label="Go away",
        style=discord.ButtonStyle.red,
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.message.delete()

    async def on_timeout(self):
        await self.message.edit(view=self.clear_items())


class SettingsModal(discord.ui.Modal, title="Change render settings"):
    CLI_flags = discord.ui.TextInput(
        label="CLI flags",
        placeholder="--renderer=cairo",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if ";" in self.CLI_flags.value or "&" in self.CLI_flags.value:
            await interaction.response.send_message(
                f"Something went wrong, please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        async with interaction.channel.typing():
            code_message = await interaction.channel.fetch_message(
                interaction.message.reference.message_id
            )
            response = await render_animation_snippet(
                code_message, cli_flags=self.CLI_flags.value.split()
            )
            cli_flags = response.pop("cli_flags")
            if cli_flags:
                response["content"] += f"\n\nPassed CLI flags: `{cli_flags}`"
            view = RenderView(timeout=VIEW_TIMEOUT)
            view.children[0].label = "Render again"
            message = await interaction.followup.edit_message(
                message_id=interaction.message.id, view=view, **response
            )
            view.message = message


def extract_manim_snippets(msg) -> None | str:
    pattern = re.compile(r"```(?:py|python)?([^`]*def construct[^`]*)```")
    return pattern.findall(msg)


async def render_animation_snippet(code_message, cli_flags=None) -> Dict[str, Any]:
    if cli_flags is None:
        cli_flags = []

    dockerclient = aiodocker.Docker()

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
            container = await dockerclient.containers.run(
                config={
                    "Image": "manimcommunity/manim:stable",
                    "Cmd": [
                        "timeout",
                        "120",
                        "manim",
                        "--quality=m",
                        "--disable_caching",
                        "--progress_bar=none",
                        "--output_file=scriptoutput",
                        *cli_flags,
                        "/manim/script.py",
                    ],
                    "User": "manimuser",
                    "HostConfig": {
                        "Binds": [f"{tmpdirname}:/manim/:rw"],
                        "AutoRemove": True,
                    },
                }
            )
            manim_stderr = []
            # `follow=True` allow to keep the stream open until the container stops
            async for line in container.log(follow=True, stderr=True):
                manim_stderr.append(line.rstrip())
            await dockerclient.close()
            if manim_stderr:
                raise ManimError(traceback=manim_stderr)
        except Exception as e:
            if isinstance(e, ManimError):  # manim itself threw an error
                reply_args = {
                    "content": "Something went wrong! :cry: Here is what Manim reports.",
                    "cli_flags": cli_flags,
                    "attachments": [
                        discord.File(
                            fp=io.StringIO(e.traceback),
                            filename="error.log",
                        ),
                    ],
                }
                return reply_args
            else:
                if isinstance(e, aiodocker.DockerContainerError):
                    # communication with docker yields error
                    tb = e.message
                else:
                    # something else (?) went wrong
                    tb = str.encode(traceback.format_exc())
                reply_args = {
                    "content": f"Something went wrong, the error log is attached. :cry:",
                    "cli_flags": cli_flags,
                    "attachments": [
                        discord.File(fp=io.BytesIO(tb), filename="error.log"),
                    ],
                }
                return reply_args

        try:
            [outfilepath] = Path(tmpdirname).rglob("scriptoutput.*")
        except Exception as e:
            reply_args = {
                "content": "Something went wrong: no (unique) output file was produced. :cry:",
                "cli_flags": cli_flags,
            }
        else:
            reply_args = {
                "content": "Here you go!",
                "cli_flags": cli_flags,
                "attachments": [
                    discord.File(outfilepath),
                ],
            }
        finally:
            return reply_args


async def setup(bot: commands.Bot):
    """Entrypoint of loading the bot extension."""
    await bot.add_cog(RenderCodeblock(bot))
    logging.info("RenderCodeblock cog has been added.")


class ManimError(ChildProcessError):
    def __init__(self, traceback: List[str]):
        self.traceback = "\n".join(traceback)
