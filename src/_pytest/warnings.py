import os
import sys
import warnings
from contextlib import contextmanager
from typing import Generator
from typing import Optional
from typing import TYPE_CHECKING

import pytest
from _pytest.config import apply_warning_filters
from _pytest.config import Config
from _pytest.config import parse_warning_filter
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.terminal import TerminalReporter

if TYPE_CHECKING:
    from typing_extensions import Literal


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "filterwarnings(warning): add a warning filter to the given test. "
        "see https://docs.pytest.org/en/stable/how-to/capture-warnings.html#pytest-mark-filterwarnings ",
    )


@contextmanager
def catch_warnings_for_item(
    config: Config,
    ihook,
    when: "Literal['config', 'collect', 'runtest']",
    item: Optional[Item],
) -> Generator[None, None, None]:
    """Context manager that catches warnings generated in the contained execution block.

    ``item`` can be None if we are not in the context of an item execution.

    Each warning captured triggers the ``pytest_warning_recorded`` hook.
    """
    sys.stderr.write(f"start catch_warnings_for_item() 1111" + os.linesep)
    config_filters = config.getini("filterwarnings")
    cmdline_filters = config.known_args_namespace.pythonwarnings or []
    with warnings.catch_warnings(record=True) as log:
        # mypy can't infer that record=True means log is not None; help it.
        assert log is not None

        if not sys.warnoptions:
            # If user is not explicitly configuring warning filters, show deprecation warnings by default (#2908).
            warnings.filterwarnings("always", category=DeprecationWarning)
            warnings.filterwarnings("always", category=PendingDeprecationWarning)

        apply_warning_filters(config_filters, cmdline_filters)

        # apply filters from "filterwarnings" marks
        nodeid = "" if item is None else item.nodeid
        if item is not None:
            for mark in item.iter_markers(name="filterwarnings"):
                for arg in mark.args:
                    warnings.filterwarnings(*parse_warning_filter(arg, escape=False))

        sys.stderr.write(f"start catch_warnings_for_item() 2222" + os.linesep)

        yield

        sys.stderr.write(f"start catch_warnings_for_item() 3333" + os.linesep)
        for warning_message in log:
            ihook.pytest_warning_recorded.call_historic(
                kwargs=dict(
                    warning_message=warning_message,
                    nodeid=nodeid,
                    when=when,
                    location=None,
                )
            )

        sys.stderr.write(f"start catch_warnings_for_item() 4444" + os.linesep)


def warning_record_to_str(warning_message: warnings.WarningMessage) -> str:
    """Convert a warnings.WarningMessage to a string."""
    sys.stderr.write(f"start warning_record_to_str()" + os.linesep)
    warn_msg = warning_message.message
    msg = warnings.formatwarning(
        str(warn_msg),
        warning_message.category,
        warning_message.filename,
        warning_message.lineno,
        warning_message.line,
    )
    if warning_message.source is not None:
        try:
            import tracemalloc
        except ImportError:
            pass
        else:
            tb = tracemalloc.get_object_traceback(warning_message.source)
            if tb is not None:
                formatted_tb = "\n".join(tb.format())
                # Use a leading new line to better separate the (large) output
                # from the traceback to the previous warning text.
                msg += f"\nObject allocated at:\n{formatted_tb}"
            else:
                # No need for a leading new line.
                url = "https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings"
                msg += "Enable tracemalloc to get traceback where the object was allocated.\n"
                msg += f"See {url} for more info."
    return msg


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_protocol(item: Item) -> Generator[None, None, None]:
    sys.stderr.write(f"start pytest_runtest_protocol()" + os.linesep)
    with catch_warnings_for_item(
        config=item.config, ihook=item.ihook, when="runtest", item=item
    ):
        yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_collection(session: Session) -> Generator[None, None, None]:
    sys.stderr.write(f"start pytest_collection()" + os.linesep)
    config = session.config
    with catch_warnings_for_item(
        config=config, ihook=config.hook, when="collect", item=None
    ):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
) -> Generator[None, None, None]:
    sys.stderr.write(f"start pytest_terminal_summary()" + os.linesep)
    config = terminalreporter.config
    with catch_warnings_for_item(
        config=config, ihook=config.hook, when="config", item=None
    ):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session: Session) -> Generator[None, None, None]:
    sys.stderr.write(f"start pytest_sessionfinish()" + os.linesep)
    config = session.config
    with catch_warnings_for_item(
        config=config, ihook=config.hook, when="config", item=None
    ):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_load_initial_conftests(
    early_config: "Config",
) -> Generator[None, None, None]:
    sys.stderr.write(f"start pytest_load_initial_conftests()" + os.linesep)
    with catch_warnings_for_item(
        config=early_config, ihook=early_config.hook, when="config", item=None
    ):
        yield
