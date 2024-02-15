from pathlib import Path
import sys

from .apps import apps
from .loader import Loader


default_paths = [
    Path(__file__).parent,
]


def main(argv=None, paths=None):
    argv = argv or sys.argv
    paths = paths or default_paths

    loader = Loader(paths)
    loader.load()
    apps.dispatch(argv)


