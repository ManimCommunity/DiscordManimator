import os
<<<<<<< HEAD
import re
import tempfile
import textwrap
import traceback
from pathlib import Path
from string import Template
=======
import traceback
>>>>>>> refactor

import config
import discord
from discord.ext import commands

bot = commands.Bot(
    description="Manim Community Discord Bot",
    activity=discord.Game("Animating with Manim"),
    help_command=None,
    command_prefix=config.PREFIX,
    case_insensitive=True,
    strip_after_prefix=True,
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
<<<<<<< HEAD
    return


@bot.command()
async def mhelp(ctx):
    await ctx.send(
        """A simple Manim rendering and utility bot.

Use the `!manimate` command to render short and simple Manim scripts.
Code **must** be properly formatted and indented. Note that you can't animate through DM's.

Supported tags:
```
    -t, --transparent, -i, --save_as_gif, -s, --save_last_frame
```
Example:
```
!manimate -s
\`\`\`py
def construct(self):
    self.play(ReplacementTransform(Square(), Circle()))
\`\`\`
```

Also, check `!mdocstring -h` for information about `mdocstring` command.
"""
    )


def get_formatted_code(code: str, lang: str = ""):
    return f"```{lang}\n{code}\n```"


@bot.command(aliases=["md"])
@commands.guild_only()
async def mdocstring(ctx, *, arg):
    template = Template(
        textwrap.dedent(
            """\
            .. manim:: ${CLASSNAME} ${EXTRA_ARGS}

            ${CODEHERE}
            """
        )
    )

    def construct_reply(arg):
        if arg.startswith("```"):  # empty header
            arg = "\n" + arg
        header, *body = arg.split("\n")

        cli_flags = header.split()

        class HandleErrArgumentParser(argparse.ArgumentParser):
            def __init__(self, *args, **kwargs):
                super(HandleErrArgumentParser, self).__init__(*args, **kwargs)

                self.error_message = ""

            def error(self, message):
                self.error_message = message

            def parse_args(self, *args, **kwargs):
                # catch SystemExit exception to prevent closing the application
                result = None
                try:
                    result = super().parse_args(*args, **kwargs)
                except SystemExit:
                    pass
                return result

            def _print_message(self, message, file=None):
                # don't do anything, or else it will clutter
                # logs.
                pass

            def print_help(self, file=None):
                if file is None:
                    return
                file.write(self.format_help())

        parser = HandleErrArgumentParser(
            prog="!mdocstring",
            description="Convert code-blocks to docs output.",
        )
        parser.add_argument(
            "--class_name",
            help="Name of the scene. It will be calculated otherwise.",
            default="",
        )
        parser.add_argument(
            "--hide_source",
            action="store_true",
            help="If this flag is present without argument,"
            "the source code is not displayed above the rendered video.",
        )
        parser.add_argument(
            "--quality",
            choices=["low", "medium", "high", "fourk"],
            help="Controls render quality of the video, in analogy to"
            "the corresponding command line flags.",
        )
        parser.add_argument(
            "--save_as_gif",
            action="store_true",
            help="If this flag is present without argument,"
            "the scene is rendered as a gif.",
        )
        parser.add_argument(
            "--save_last_frame",
            "-s",
            action="store_true",
            help="If this flag is present without argument,"
            "an image representing the last frame of the scene will"
            "be rendered and displayed, instead of a video.",
        )
        parser.add_argument(
            "--ref_classes",
            nargs="+",
            help="A list of classess that is"
            "rendered in a reference block after the source code.",
        )
        parser.add_argument(
            "--ref_functions",
            nargs="+",
            help="A list of functions"
            "that is rendered in a reference block after the source code.",
        )
        parser.add_argument(
            "--ref_methods",
            nargs="+",
            help="A list of methods"
            "that is rendered in a reference block after the source code.",
        )
        args = parser.parse_args(cli_flags)
        if args is None:
            # -h or --help is passed, so print help.
            with io.StringIO() as f:
                parser.print_help(f)
                content = f.getvalue()
            return {"content": get_formatted_code(content, "")}
        if parser.error_message:
            return {"content": get_formatted_code(parser.error_message)}
        body = "\n".join(body).strip()
        if body.count("```") != 2:
            return {
                "content": "Your message is not properly formatted. "
                "Your code has to be written in a code block, like so:\n"
                "\\`\\`\\`py\nyour code here\n\\`\\`\\`"
            }
        script = re.search(
            pattern=r"```(?:py)?(?:thon)?(.*)```",
            string=body,
            flags=re.DOTALL,
        ).group(1)
        script = script.strip()
        if "from manim import *" in script:
            script = script.replace("from manim import *", "").strip()
        if args.class_name:
            class_name = args.class_name
        else:
            scene_name = "Scene|GraphScene|VectorScene|LinearTransformationScene|MovingCameraScene|ZoomedScene|ReconfigurableScene|SampleSpaceScene|ThreeDScene|SpecialThreeDScene"
            classregex = re.compile(
                rf"class\s+(?P<classname>[A-Za-z]*)\(({scene_name})\)"
            )
            res = classregex.search(script)
            if res:
                class_name = res.group("classname")
            else:
                return {
                    "content": "Can't find a unique Class Name. Either pass it as an argument or use standard methods."
                }
        dictargs = args.__dict__
        extra_args_lst = []
        dictargs.pop("class_name")
        for key, value in dictargs.items():
            if value != None and not isinstance(value, bool):
                if isinstance(value, list):
                    for n in range(len(value)):
                        if "," in value[n]:
                            _temp = value[n].split(",")
                            value.pop(n)
                            value.extend(_temp)
                    value = " ".join(value)
                extra_args_lst += [f":{key}: {value}"]
            elif isinstance(value, bool):
                if value is True:
                    extra_args_lst += [f":{key}:"]
        if len(extra_args_lst) == 0:
            extra_args = ""
        else:
            extra_args = "\n" + " " * 4
            extra_args += "\n    ".join(extra_args_lst)

        # format using black
        max_line_length = 88
        mode = black.FileMode(line_length=max_line_length)
        try:
            script = black.format_str(script, mode=mode)
        except Exception as e:
            return {"content": f"""Error while formatting code:\n```py\n{e}\n```"""}

        output = template.substitute(
            CLASSNAME=class_name,
            CODEHERE=textwrap.indent(script, 4 * " "),
            EXTRA_ARGS=extra_args,
        )
        return {"content": get_formatted_code(output, "py")}

    reply_args = construct_reply(arg)
    await ctx.reply(**reply_args)
    return


@bot.command(aliases=["m"])
@commands.guild_only()
async def manimate(ctx, *, arg):
    def construct_reply(arg):
        if arg.startswith("```"):  # empty header
            arg = "\n" + arg
        header, *body = arg.split("\n")

        cli_flags = header.split()
        allowed_flags = [
            "-i",
            "--save_as_gif",
            "-s",
            "--save_last_frame",
            "-t",
            "--transparent",
        ]
        if not all([flag in allowed_flags for flag in cli_flags]):
            reply_args = {
                "content": "You cannot pass CLI flags other than "
                "`-i` (`--save_as_gif`), `-s` (`--save_last_frame`), "
                "`-t` (`--transparent`)."
            }
            return reply_args
        else:
            cli_flags = " ".join(cli_flags)

        body = "\n".join(body).strip()

        if body.count("```") != 2:
            reply_args = {
                "content": "Your message is not properly formatted. "
                "Your code has to be written in a code block, like so:\n"
                "\\`\\`\\`py\nyour code here\n\\`\\`\\`"
            }
            return reply_args

        script = re.search(
            pattern=r"```(?:py)?(?:thon)?(.*)```",
            string=body,
            flags=re.DOTALL,
        ).group(1)
        script = script.strip()

        # for convenience: allow construct-only:
        if script.startswith("def construct(self):"):
            script = ["class Manimation(Scene):"] + [
                "    " + line for line in script.split("\n")
            ]
        else:
            script = script.split("\n")

        script = ["from manim import *"] + script

        # write code to temporary file (ideally in temporary directory)
        with tempfile.TemporaryDirectory() as tmpdirname:
            scriptfile = Path(tmpdirname) / "script.py"
            with open(scriptfile, "w", encoding="utf-8") as f:
                f.write("\n".join(script))
            try:  # now it's getting serious: get docker involved
                reply_args = None
                container_stderr = dockerclient.containers.run(
                    image="manimcommunity/manim:stable",
                    volumes={tmpdirname: {"bind": "/manim/", "mode": "rw"}},
                    command=f"timeout 120 manim -qm --disable_caching --progress_bar=none -o scriptoutput {cli_flags} /manim/script.py",
                    user=os.getuid(),
                    stderr=True,
                    stdout=False,
                    remove=True,
                )

            except Exception as e:
                if isinstance(e, docker.errors.ContainerError):
                    tb = e.stderr
                else:
                    tb = str.encode(traceback.format_exc())
                reply_args = {
                    "content": f"Something went wrong, the error log is attached. :cry:",
                    "file": discord.File(
                                fp=io.BytesIO(tb),
                                filename="error.log",
                            ),
                }
                raise e
            finally:
                if reply_args:
                    return reply_args
=======

>>>>>>> refactor

if __name__ == "__main__":
    for extension in os.listdir("cogs/"):
        if extension.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{extension[:-3]}")
            except Exception:
                print(f"{extension} couldn't be loaded.")
                traceback.print_exc()
                print("")

bot.run(config.TOKEN)
