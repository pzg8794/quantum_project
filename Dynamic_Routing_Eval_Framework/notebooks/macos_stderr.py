"""Mute one macOS allocator diagnostic without disabling stderr."""

from contextlib import ExitStack, contextmanager
import os
import re
import sys
from threading import Thread


_MALLOC_WARNING = re.compile(
    rb"[Pp]ython(?:[0-9.]+)?\([0-9]+\) MallocStackLogging: can't turn off malloc stack "
    rb"logging because it was not enabled\.[ \t]*\r?\n?"
)


def _relay_stderr(reader, destination):
    try:
        with os.fdopen(reader, "rb") as stream:
            destination_open = True
            for line in stream:
                if not destination_open or _MALLOC_WARNING.fullmatch(line):
                    continue
                remaining = memoryview(line)
                try:
                    while remaining:
                        remaining = remaining[os.write(destination, remaining):]
                except OSError:
                    destination_open = False
    finally:
        os.close(destination)


@contextmanager
def mute_malloc_stack_logging():
    """Filter native stderr for the current process and children that inherit it."""
    if sys.platform != "darwin":
        yield
        return

    relay = None
    try:
        with ExitStack() as descriptors:
            try:
                inheritable = os.get_inheritable(2)
                original = os.dup(2)
                descriptors.callback(os.close, original)
                with ExitStack() as startup:
                    reader, writer = os.pipe()
                    startup.callback(os.close, reader)
                    descriptors.callback(os.close, writer)
                    destination = os.dup(original)
                    startup.callback(os.close, destination)
                    worker = Thread(target=_relay_stderr, args=(reader, destination), daemon=True)
                    worker.start()
                    startup.pop_all()
                    relay = worker
                os.dup2(writer, 2, inheritable=inheritable)
            except (OSError, RuntimeError):
                descriptors.close()
                yield
                return

            try:
                yield
            finally:
                os.dup2(original, 2, inheritable=inheritable)
    finally:
        if relay is not None:
            relay.join(timeout=1)
