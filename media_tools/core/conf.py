from pathlib import Path
import os
import yaml

from .logs import logs


class ConfigFile:
    """Base class used to load config files."""

    @staticmethod
    def default_constructor(x):
        return x

    subdir = ""

    def __init__(self, lookups: Path | str | [Path] | None, constructor=None, logs=None):
        if isinstance(lookups, (Path, str)):
            self.lookups = [
                Path(lookups),
            ]
        else:
            self.lookups = tuple(Path(lookup) for lookup in lookups)
        self.constructor = constructor or self.default_constructor

    def read(self, paths=None):
        paths = paths or self.get_paths()
        if not paths:
            return None
        for path in paths:
            if not path.exists():
                continue
            try:
                with path.open() as f:
                    data = self.parse(f)
                    return self.get_object(**data)
            except Exception as err:
                logs.warning(f"Reading file {path} raised an error: {err}")
        return None

    def get_paths(self):
        return (dir / lookup for dir in self.get_config_dirs() for lookup in self.lookups)

    def get_config_dirs(self):
        user_conf = Path(os.environ.get("XDG_CONFIG_HOME")) or Path.home() / ".config"
        return (
            user_conf / "media_tools" / self.subdir,
            "/etc/media_tools" / self.subdir,
        )

    def parse(self, value):
        return yaml.load(value)

    def get_object(self, **kwargs):
        return self.constructor(**kwargs)
