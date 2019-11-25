import logging
import sys
import threading
import time
import traceback
from functools import partial
from multiprocessing import Lock
from multiprocessing.pool import ThreadPool
from typing import Collection, Iterable, List, Optional, Tuple, Union

import click
from tqdm import tqdm

import bento.result
import bento.util
from bento.constants import SUPPORT_EMAIL_ADDRESS
from bento.result import Baseline, Violation
from bento.tool import Tool

MAX_BAR_VALUE = 30
BAR_UPDATE_INTERVAL = 0.1

ToolResults = Union[List[Violation], Exception]
RunResults = Tuple[str, ToolResults]

MIN_BAR_VALUE = int(MAX_BAR_VALUE / 5)


class Runner:
    def __init__(self) -> None:
        self._lock = Lock()
        self._setup_latch: bento.util.CountDownLatch
        self._bars: List[tqdm]
        self._run: List[bool]
        self._show_bars = sys.stderr.isatty()

    def _update_bars(self, ix: int) -> None:
        bar_value = MIN_BAR_VALUE
        keep_going = True
        bar = self._bars[ix]
        while keep_going:
            with self._lock:
                keep_going = self._run[ix]
                if bar_value < MAX_BAR_VALUE - 1:
                    bar_value += 1
                    bar.update(1)
                else:
                    bar_value = MIN_BAR_VALUE
                    bar.update(MIN_BAR_VALUE - MAX_BAR_VALUE + 1)
            time.sleep(BAR_UPDATE_INTERVAL)
        with self._lock:
            bar.update(MAX_BAR_VALUE - bar_value)

    def _run_single_tool(
        self,
        baseline: Baseline,
        paths: Optional[Iterable[str]],
        index_and_tool: Tuple[int, Tool],
    ) -> RunResults:
        """Runs a tool and filters out existing findings using baseline"""

        ix, tool = index_and_tool
        try:
            before = time.time()
            bar = self._bars[ix] if self._show_bars else None
            self._run[ix] = True

            logging.debug(f"{tool.tool_id()} start")
            if bar:
                with self._lock:
                    bar.set_postfix_str("🍜")

            try:
                tool.setup()
            finally:
                if self._setup_latch:
                    self._setup_latch.count_down()
            if bar:
                with self._lock:
                    bar.update(MIN_BAR_VALUE)
                    bar.set_postfix_str("🍤")
            after_setup = time.time()

            th = None
            if bar:
                th = threading.Thread(
                    name=f"update_{ix}", target=partial(self._update_bars, ix)
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
                with self._lock:
                    bar.set_postfix_str("🍱")
            after = time.time()

            logging.debug(
                f"{tool.tool_id()} completed in {(after - before):2f} s (setup in {(after_setup - before):2f} s)"
            )  # TODO: Move to debug
            return (tool.tool_id(), results)
        except Exception as e:
            logging.error(traceback.format_exc())
            return (tool.tool_id(), e)

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

        if self._show_bars:
            self._bars = [
                tqdm(
                    total=MAX_BAR_VALUE,
                    position=ix,
                    ascii="□■",
                    mininterval=BAR_UPDATE_INTERVAL,
                    desc=tool.tool_id(),
                    ncols=40,
                    bar_format="  {desc:<14s} "
                    + click.style("|{bar}| {elapsed}{postfix}", dim=True),
                    leave=False,
                )
                for ix, tool in indices_and_tools
            ]
        self._run = [True for _, _ in indices_and_tools]
        self._setup_latch = bento.util.CountDownLatch(n_tools)

        with ThreadPool(n_tools) as pool:
            # using partial to pass in multiple arguments to __tool_filter
            func = partial(Runner._run_single_tool, self, baseline, files)
            all_results = pool.map(func, indices_and_tools)

        if self._show_bars:
            for _ in self._bars:
                click.echo("", err=True)
            for b in self._bars:
                b.close()

        click.echo("", err=True)

        return all_results
