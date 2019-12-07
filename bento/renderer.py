from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

import attr
import yaml
from click import confirm, prompt, secho, style

import bento.util

Content = Dict[str, Any]


class Keys:
    RENDER = "render"

    ANCHOR = "anchor"
    CHARACTER = "character"
    CONTENT = "content"
    EXTRA_WIDTH = "extra-width"
    HREF = "href"
    LINKS = "links"
    NEWLINE = "newline"
    OPTIONS = "options"
    PROCESSOR = "processor"
    STYLE = "style"
    TEXT = "text"


def process_ljust(text: str, value: Content) -> str:
    """
    Left-justifies text, filling width with specified character

    If content includes an integer "extra-width" value, that many characters are added to
    (or subtracted from) the print width.
    """
    extra = value.get(Keys.EXTRA_WIDTH, 0)
    char = value.get(Keys.CHARACTER, " ")
    return text.ljust(bento.util.PRINT_WIDTH + extra, char)


def process_wrap(text: str, value: Content) -> str:
    """
    Wraps text to print width

    If content includes an integer "extra-width" value, that many characters are added to
    (or subtracted from) the print width. This is useful when the content is known to include
    ANSI escape sequences (each escape sequence consumes 4 characters of width).
    """
    extra = value.get(Keys.EXTRA_WIDTH, 0)
    return bento.util.wrap(text, extra)


def process_wrap_link(text: str, value: Content) -> str:
    """
    Per wrap, except links are rendered without affecting the wrap width.

    In addition to the specification of process_wrap, a sequence of "link" values controls link processing.

    Each "link" value should contain a string "anchor" value. All instances of this value are replaced with
    a rendered link, directing to the value of the link's "href" entry.

    Links are only rendered if the terminal is a known supporting terminal for OSC8 links. If not,
    links are rendered as their anchor text only.
    """
    extra_width = value.get(Keys.EXTRA_WIDTH, 0)
    links = [(v[Keys.ANCHOR], v[Keys.HREF]) for v in value.get(Keys.LINKS, [])]
    styling = value.get(Keys.STYLE, {})
    return bento.util.wrap_link(text, extra_width, *links, **styling)


PROCESSORS = {
    "ljust": process_ljust,
    "wrap": process_wrap,
    "wrap-link": process_wrap_link,
}


def _expand_text(value: Content, *args: Any, apply_style: bool = False) -> str:
    """
    Appends a sequence of styled text elements.

    Styling is not applied to top-level elements; this is left to the renderer.
    This can be modified by calling with apply_style = True.

    See the help for render_echo for more information.
    """
    content = value.get(Keys.CONTENT)
    processor = value.get(Keys.PROCESSOR)

    if isinstance(content, list):
        items = (_expand_text(c, *args, apply_style=True) for c in content)
        text = "".join(items)
    elif isinstance(content, str):
        text = content
    elif isinstance(content, int):
        if len(args) <= content:
            raise ValueError(
                f"Not enough elements in {args} to read argument {content}"
            )
        text = str(args[content])
    else:
        text = ""

    if processor:
        if processor not in PROCESSORS:
            raise ValueError(
                f"Unknown processor {processor} (known processors are {', '.join(PROCESSORS.keys())})"
            )
        text = PROCESSORS[processor](text, value)

    if apply_style:
        styling = value.get(Keys.STYLE, {})
        return style(text, **styling)
    else:
        return text


def render_box(text: str, value: Content, **kwargs: Any) -> None:
    """
    Renders content in a Unicode-drawn box to stderr
    """
    bento.util.echo_box(text)


def render_confirm(text: str, value: Content, **kwargs: Any) -> bool:
    """
    Renders a confirmation prompt, and returns confirmation state.
    """
    styling = value.get(Keys.STYLE, {})
    options = {**value.get(Keys.OPTIONS, {}), **kwargs}
    return confirm(style(text, **styling), err=True, **options)


def render_prompt(text: str, value: Content, **kwargs: Any) -> str:
    """
    Renders a confirmation prompt, and returns confirmation state.
    """
    styling = value.get(Keys.STYLE, {})
    options = {**value.get(Keys.OPTIONS, {}), **kwargs}
    return prompt(style(text, **styling), err=True, **options)


def render_echo(text: str, value: Content, **kwargs: Any) -> None:
    """
    Renders content, appended together, to stderr

    Content must include a "content" key, whose value is one of:
      - a string, which is rendered verbatim
      - a sequence of mapping; each mapping must contain a string "text" value, and may also include a "style"
    mapping, which is passed directly to click.style
      - an integer, which indexes a passed argument

    Content may also include a "style" mapping, which is passed (for all content), to click.secho.

    Content may also include a boolean "newline" value. If False, no newline is emitted at the end of
    the text.
    """
    newline = value.get(Keys.NEWLINE, True)
    styling = value.get(Keys.STYLE, {})
    secho(text, err=True, nl=newline, **styling)


def render_error(text: str, value: Content, **kwargs: Any) -> None:
    """
    Renders error content to stderr
    """
    bento.util.echo_error(text)


def render_newline(text: str, value: Content, **kwargs: Any) -> None:
    """
    Renders a blank line to stderr
    """
    bento.util.echo_newline()


def render_success(text: str, value: Content, **kwargs: Any) -> None:
    """
    Renders success content to stderr
    """
    bento.util.echo_success(text)


def render_warning(text: str, value: Content, **kwargs: Any) -> None:
    """
    Renders warning content to stderr
    """
    bento.util.echo_warning(text)


def render_progress(text: str, value: Content, **kwargs: Any) -> Callable[[], None]:
    """
    Renders a progress bar

    For more information, see bento.util.echo_progress.

    The content's "extra-width" value is passed to the "extra" argument of echo_progress.

    :return: The progress done callback
    """
    extra_width = value.get(Keys.EXTRA_WIDTH, 0)
    return bento.util.echo_progress(text, extra_width, **kwargs)


PRINTERS: Mapping[str, Any] = {
    "box": render_box,
    "confirm": render_confirm,
    "echo": render_echo,
    "error": render_error,
    "newline": render_newline,
    "progress": render_progress,
    "prompt": render_prompt,
    "success": render_success,
    "warning": render_warning,
}
DEFAULT_PRINTER = render_echo


@attr.s
class Renderer(object):
    """
    Renders content from a YAML file

    To use, invoke:

      renderer.echo(path, ...)

    where path is a sequence of string keys within the YAML file that point to
    a sequence valid content descriptions.

    Each content description contains, at least, a "render" key, that indicates which
    rendering function will be used to render that piece of content. To see what keys
    each function uses, please see the documentation for that function. By convention,
    the rendering function symbol is "render_...", where the ellipses are filled with
    the value of the "render" item.

    If the content description does _not_ have a "render" key, then render_echo is used
    to render the content.

    :param content_path: Path to the YAML content file
    """

    content_path = attr.ib(type=Path)
    content = attr.ib(type=Dict[str, Any], init=False, default=False)

    def __attrs_post_init__(self) -> None:
        with self.content_path.open() as stream:
            self.content = yaml.safe_load(stream)

    def content_at(self, *path: str) -> List[Content]:
        """Returns the content specification at the specified YAML entry"""
        content: Any = self.content
        pp = path
        while pp:
            content = content[pp[0]]
            pp = pp[1:]
        return content

    def text_at(self, *path: str, args: Optional[List[Any]] = None) -> str:
        """Returns un-rendered (but styled) content text at the specified YAML entry"""
        args = [] if args is None else args
        return "".join(
            _expand_text(c, *args, apply_style=True) for c in self.content_at(*path)
        )

    def echo(self, *path: str, args: Optional[List[Any]] = None, **kwargs: Any) -> Any:
        """
        Renders content at the specified YAML entry

        :returns: First non-None render-function output
        """
        out: Any = None
        args = [] if args is None else args
        for c in self.content_at(*path):
            render_value = c.get(Keys.RENDER, "echo")
            printer = PRINTERS.get(render_value)
            if not printer:
                raise ValueError(
                    f"No renderer found for '{render_value}' (possible values are {', '.join(PRINTERS.keys())})"
                )
            text = _expand_text(c, *args)
            res = printer(text, c, **kwargs)
            if not out:
                out = res
        return out
