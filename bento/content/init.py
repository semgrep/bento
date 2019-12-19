from bento.renderer import (
    Box,
    Confirm,
    Content,
    Echo,
    Error,
    Link,
    Multi,
    Newline,
    Processors,
    Progress,
    Prompt,
    Steps,
    Sub,
    Text,
    Warn,
)


def _step_item(desc: str, cmd: str, nl: bool = True) -> Content:
    """
    Echoes

      desc․․․․․․․․․․․․․․․․․․․․․․․․․․․․․․․․․․ $ cmd

    with styling.

    If 'nl' is False, does not emit a newline at the end of the line
    """
    return Multi(
        [
            "  ",
            Text(desc, processor=Processors.ljust(-40, "․"), style={"dim": True}),
            f" $ {cmd}\n",
        ]
    )


class InstallConfig:
    install = Progress(
        content=Multi(
            [
                "Creating default configuration at ",
                Sub(0, style={"bold": True, "dim": True}),
            ]
        ),
        extra=12,
    )
    error = Error("Bento can't identify this project")


class InstallIgnore:
    install = Progress(
        content=Multi(
            [
                "Creating default ignore file at ",
                Sub(0, style={"bold": True, "dim": True}),
            ]
        ),
        extra=12,
    )


class Clean:
    tools = Steps(Echo("Reinstalling tools due to passed --clean flag."), Newline())
    check = Warn(
        """
Removing archive due to passed --clean flag.
"""
    )


class Identify:
    success = Steps(
        Newline(),
        Echo(Multi(["Detected project with ", Sub(0, style={"bold": True})])),
        Newline(),
    )
    failure = Steps(Newline(), Error("Bento can't identify this project."))


class Check:
    unnecessary = Steps(
        Echo("Bento archive is already configured on this project."), Newline()
    )

    prompt = Confirm(
        "Analyze this project for the first time?", options={"default": True}
    )

    header = Box("Bento Check")

    noninteractive = Warn("Skipping project analysis due to noninteractive terminal.")


class NextSteps:
    prompt = Prompt(
        "Press ENTER to view next steps",
        options={"default": "", "hide_input": True, "show_default": False},
    )

    body = Steps(
        Box("Next Steps"),
        Echo(
            Text(
                "Bento is at its best when it runs automatically, either in CI or as a git hook. To learn "
                "more about these, see Bento in CI or Bento as a Git Hook in our README.",
                processor=Processors.wrap_link(
                    [
                        Link(
                            "Bento in CI",
                            "https://github.com/returntocorp/bento#running-bento-in-ci",
                        ),
                        Link(
                            "Bento as a Git Hook",
                            "https://github.com/returntocorp/bento#running-bento-as-a-git-hook",
                        ),
                    ],
                    dim=True,
                ),
            )
        ),
        Newline(),
        Echo("To use Bento:"),
        Echo(
            Multi(
                [
                    _step_item("check project", "bento check"),
                    _step_item("view archived results", "bento check --show-all"),
                    _step_item("disable a check", "bento disable check [TOOL] [CHECK]"),
                    _step_item("enable a tool", "bento enable tool [TOOL]"),
                    _step_item("install commit hook", "bento install-hook"),
                    _step_item(
                        "get help for a command", "bento [COMMAND] --help", nl=False
                    ),
                ]
            )
        ),
    )

    finish_init = Steps(
        Newline(),
        Prompt(
            "Press ENTER to finish initialization",
            options={"default": "", "hide_input": True, "show_default": False},
        ),
    )

    thank_you = Steps(
        Box("Thank You"),
        Echo(
            Text(
                "From all of us at r2c, thank you for trying Bento! We can’t wait to hear what you think.",
                processor=Processors.wrap(),
            )
        ),
        Newline(),
        Echo(
            Multi(
                [
                    "Help and feedback: ",
                    Text("Reach out to us at ", style={"dim": True}),
                    "support@r2c.dev",
                    Text(" or file an issue on ", style={"dim": True}),
                    "GitHub",
                    Text(". We’d love to hear from you!", style={"dim": True}),
                ],
                processor=Processors.wrap_link(
                    [
                        Link("support@r2c.dev", "mailto:support@r2c.dev"),
                        Link("GitHub", "https://github.com/returntocorp/bento/issues"),
                    ],
                    extra=16,
                ),
            )
        ),
        Newline(),
        Echo(
            Multi(
                [
                    "Community: ",
                    Text("Join ", style={"dim": True}),
                    "#bento",
                    Text(
                        " on our community Slack. Get support, talk with other users, and share feedback.",
                        style={"dim": True},
                    ),
                ],
                processor=Processors.wrap_link(
                    [
                        Link(
                            "#bento",
                            "https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA",
                        )
                    ],
                    extra=16,
                ),
            )
        ),
        Newline(),
    )


class RunArchive:
    pre = Newline()
    post = Newline()


run_all = Box("Bento Initialization")
