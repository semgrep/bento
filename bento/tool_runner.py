import logging
import multiprocessing.synchronize
import sys
import threading
import time
import traceback
from functools import partial
from multiprocessing import Lock
from multiprocessing.pool import ThreadPool
from typing import Collection, Iterable, List, Optional, Tuple, Union

import attr
import click
from tqdm import tqdm

import bento.result
import bento.util
from bento.constants import SUPPORT_EMAIL_ADDRESS
from bento.result import Baseline, Violation
from bento.tool import Tool

MAX_BAR_VALUE = 30
BAR_UPDATE_INTERVAL = 0.1

SLOW_RUN_SECONDS = 60  # Number of seconds before which a "slow run" warning is printed

ToolResults = Union[List[Violation], Exception]
RunResults = Tuple[str, ToolResults]

MIN_BAR_VALUE = int(MAX_BAR_VALUE / 5)


@attr.s
class Runner:
    show_bars = attr.ib(type=bool, default=True)
    _lock = attr.ib(type=multiprocessing.synchronize.Lock, factory=Lock, init=False)
    _setup_latch = attr.ib(type=bento.util.CountDownLatch, default=None, init=False)
    _bars = attr.ib(type=List[tqdm], factory=list, init=False)
    _run = attr.ib(type=List[bool], factory=list, init=False)
    _done = attr.ib(type=bool, default=False, init=False)

    def __attrs_post_init__(self) -> None:
        self.show_bars = self.show_bars and sys.stderr.isatty()

    def _update_bars(self, ix: int, lower: int, upper: int) -> None:
        """
        Increments a progress bar
        """
        bar_value = lower
        keep_going = True
        bar = self._bars[ix]
        while keep_going:
            with self._lock:
                keep_going = self._run[ix]
                if bar_value < upper - 1:
                    bar_value += 1
                    bar.update(1)
                else:
                    bar_value = lower
                    bar.update(lower - upper + 1)
            time.sleep(BAR_UPDATE_INTERVAL)
        with self._lock:
            bar.update(upper - bar_value)

    def _setup_bars(self, indices_and_tools: List[Tuple[int, Tool]]) -> None:
        """
        Constructs progress bars for all tools
        """
        self._bars = [
            tqdm(
                total=MAX_BAR_VALUE,
                position=ix,
                ascii="□■",
                mininterval=BAR_UPDATE_INTERVAL,
                desc=tool.tool_id().ljust(
                    bento.util.PRINT_WIDTH - 34, bento.util.LEADER_CHAR
                ),
                ncols=bento.util.PRINT_WIDTH - 2,
                bar_format=click.style("{desc:s}|{bar}| {elapsed}{postfix}", dim=True),
                leave=False,
            )
            for ix, tool in indices_and_tools
        ]

    def _echo_slow_run(self) -> None:
        """
        Echoes a warning to the screen that Bento is taking longer than expected.

        Wipes and resets any progress bars.
        """
        before = time.monotonic()

        while not self._done and time.monotonic() - before < SLOW_RUN_SECONDS:
            time.sleep(BAR_UPDATE_INTERVAL)

        if not self._done:
            with self._lock:
                if self.show_bars:
                    wipe_line = "".ljust(bento.util.PRINT_WIDTH, " ")

                    click.echo(
                        "\x1b[0G", nl=False, err=True
                    )  # Reset cursor to beginning of line
                    click.echo("\x1b[s", nl=False, err=True)  # Save cursor state
                    for _ in range(len(self._bars) - 1):
                        click.echo(wipe_line, err=True)
                    # Handling last line separately prevents screen roll
                    click.echo(wipe_line, nl=False, err=True)
                    click.echo("\x1b[u", nl=False, err=True)  # Retrieve cursor state

                click.secho(
                    bento.util.wrap(
                        f"Bento is taking longer than expected, which may mean it’s checking build or dependency "
                        f"code. This is often unintentional or unexpected.",
                        extra=-4,
                    )
                    + "\n\n"
                    + bento.util.wrap(
                        "Please make sure all build and dependency "
                        f"files are included in your `.bentoignore`, or try running Bento on specific files via `bento "
                        f"check [PATH]`",
                        extra=-4,
                    ),
                    fg=bento.util.Colors.WARNING,
                    bold=False,
                )
                bento.util.echo_newline()
        else:
            logging.debug(f"Bento run completed in less than {SLOW_RUN_SECONDS} s.")

    def _run_single_tool(
        self,
        baseline: Baseline,
        paths: Optional[Iterable[str]],
        index_and_tool: Tuple[int, Tool],
    ) -> RunResults:
        """Runs a tool and filters out existing findings using baseline"""

        ix, tool = index_and_tool
        try:
            th = None
            before = time.time()
            bar = self._bars[ix] if self.show_bars else None
            self._run[ix] = True

            logging.debug(f"{tool.tool_id()} start")
            if bar:
                with self._lock:
                    bar.set_postfix_str(bento.util.SETUP_TEXT)
                th = threading.Thread(
                    name=f"update_{ix}",
                    target=partial(self._update_bars, ix, 0, MIN_BAR_VALUE),
                )
                th.start()

            try:
                tool.setup()
                self._run[ix] = False
                if th:
                    th.join()
            finally:
                if self._setup_latch:
                    self._setup_latch.count_down()
            if bar:
                with self._lock:
                    bar.n = MIN_BAR_VALUE
                    bar.set_postfix_str(bento.util.PROGRESS_TEXT)
            after_setup = time.time()

            self._run[ix] = True
            if bar:
                th = threading.Thread(
                    name=f"update_{ix}",
                    target=partial(self._update_bars, ix, MIN_BAR_VALUE, MAX_BAR_VALUE),
                )
                th.start()
            if self._setup_latch:
                self._setup_latch.wait_for()
            results = bento.result.filtered(
                tool.tool_id(), tool.results(paths), baseline
            )
            with self._lock:
                self._run[ix] = False
            if th:
                th.join()
            if bar:
                bar.n = MAX_BAR_VALUE
                bar.update(0)
                with self._lock:
                    bar.set_postfix_str(bento.util.DONE_TEXT)
            after = time.time()

            logging.debug(
                f"{tool.tool_id()} completed in {(after - before):2f} s (setup in {(after_setup - before):2f} s)"
            )
            return tool.tool_id(), results
        except Exception as e:
            logging.error(traceback.format_exc())
            return tool.tool_id(), e

    def parallel_results(
        self, tools: Iterable[Tool], baseline: Baseline, files: Optional[List[str]]
    ) -> Collection[RunResults]:
        """Runs all tools in parallel.

        Each tool is optionally run against a list of files. For each tool, it's results are
        filtered to those results not appearing in the whitelist.

        A progress bar is emitted to stderr for each tool.

        Parameters:
            baseline (set): The set of whitelisted finding hashes
            files (list): If present, the list of files to pass to each tool

        Returns:
            (collection): For each tool, a `RunResult`, which is a tuple of (`tool_id`, `findings`)
        """
        indices_and_tools = list(enumerate(tools))
        n_tools = len(indices_and_tools)

        if n_tools == 0:
            raise Exception(
                f"No tools are configured in this project's .bento.yml.\nPlease contact {SUPPORT_EMAIL_ADDRESS} if this is incorrect."
            )

        if self.show_bars:
            self._setup_bars(indices_and_tools)
        self._run = [True for _, _ in indices_and_tools]
        self._done = False
        self._setup_latch = bento.util.CountDownLatch(n_tools)

        slow_run_thread = threading.Thread(
            name="slow_run_timer", target=self._echo_slow_run
        )
        slow_run_thread.start()

        with ThreadPool(n_tools) as pool:
            # using partial to pass in multiple arguments to __tool_filter
            func = partial(Runner._run_single_tool, self, baseline, files)
            all_results = pool.map(func, indices_and_tools)

        self._done = True
        slow_run_thread.join()

        if self.show_bars:
            for _ in self._bars:
                click.echo("", err=True)
            for b in self._bars:
                b.close()

        return all_results
