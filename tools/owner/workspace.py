"""Prevent concurrent commands from changing the same owner workspace."""

from contextlib import contextmanager
import fcntl
from pathlib import Path


@contextmanager
def workspace_lock(workspace):
    with (Path(workspace) / ".btg.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(
                "Owner workspace is already in use by another btg command"
            ) from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
