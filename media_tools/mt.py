from pathlib import Path
import sys

from .core.apps import search_paths, apps


__all__ = ("main",)


def main(filename="apps.py", paths=None, argv=None):
    """Run function of CLI interface."""
    argv = argv or sys.argv
    paths = paths or search_paths

    apps.name = Path(__file__).stem
    apps.load()
    apps.dispatch(argv=argv[1:])
