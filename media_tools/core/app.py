import argparse
from pathlib import Path


__all__ = ("action", "AppMeta", "App", "FilesApp")


def action(name, flag=None, **kwargs):
    def decorator(func):
        parser_args = [f"--{name}"]
        if flag:
            parser_args.append(flag)

        action = {"name": name, "func": func, "parser_args": parser_args, "kwargs": kwargs}
        setattr(func, "action", action)
        return func

    return decorator


class AppMeta(type):
    def __new__(mcls, name, bases, attrs):
        cls = super(AppMeta, mcls).__new__(mcls, name, bases, attrs)
        mcls.init_actions(cls)
        return cls

    @classmethod
    def init_actions(mcls, cls):
        callables = (
            (key, getattr(value, "action", None))
            for key, value in ((key, getattr(cls, key)) for key in dir(cls))
            if callable(value)
        )
        cls.actions = dict(getattr(cls, "actions", {}))
        cls.actions.update((name, action) for name, action in callables if isinstance(action, dict))


class App(metaclass=AppMeta):
    # -- class attributes
    name = None
    """Name of the application as used in commands and scripts.

    Reset to `None` by inheritance.
    """
    groups = ("default",)
    """Groups of the application."""
    label = None
    """Label of the application."""
    help = None
    """Application command help message."""
    description = None
    """Provide a description to the application that cna be displayed.

    to user.
    """
    abstract = True
    """If True, this application is not discoverable and used as an
    application.

    Reset to `False` in inheritance.
    """

    parser = None
    """ArgumentParser."""
    config_file = None
    """ConfigFile instance.

    If provided, add ``--config`` argument and load config as
    ``context['conf']``.
    """

    def load(self, subparsers=None):
        """Load application."""
        if self.parser:
            return self.parser

        if subparsers:
            self.parser = subparsers.add_parser(self.name, description=self.description, help=self.help)
        else:
            self.parser = argparse.ArgumentParser(prog=self.name, description=self.description)
        self.parser.set_defaults(app=self)
        self.init_parser(self.parser)
        return self.parser

    def init_parser(self, parser):
        """Init argument parser."""
        if self.actions:
            for action in self.actions.values():
                parser.add_argument(*action["parser_args"], **action["kwargs"])
        if self.config_file:
            parser.add_argument("--config", nargs="*", help="Provide configuration file.")

    def dispatch(self, **kwargs):
        """Dispatch application."""
        context = self.get_context(**kwargs)
        return self.run(**context)

    def get_context(self, argv=None, **kwargs):
        """
        :param [str] argv: list of argument to parse using parser.
        :param **kwargs: returned as context.
        """
        if argv:
            parsed = self.parser.parse_args(argv)
            kwargs.update(vars(parsed))

        if self.config_file:
            lookups = kwargs.get("config")
            self.get_config(lookups)

        return kwargs

    def get_config(self, lookups, no_exc=False):
        conf = self.config_file(lookups)
        if not conf and not no_exc:
            lookups = lookups or self.config_file.lookups
            raise RuntimeError(
                f"Configuration file not found. Looking up for **{'**, **'.join(lookups)}**; in "
                f"**{'**, **'.join(self.config_file.get_paths())}"
            )
        return conf

    def run(self, **context):
        """By default, lookup for actions, and run them all by order of
        declaration."""
        context.setdefault("_context", {})
        for action in self.actions.values():
            value = context.get(action["name"], None)
            if value is not None:
                action["func"](self, **context)


class FilesApp(App):
    """Application taking input files as positional argument. Provide utilities
    to work with it:

    - command line argument `sources`;
    - context `files`: files read from sources
    - save method.
    """

    read_files_from = ("sources",)
    """Tuple of variable names to read one ``get_context``. Tuple values can
    be:

    - a string: name of the variable (without dash prefix). Read mode is "r".
    - a tuple of ``(variable, mode)`` where mode is reading mode.
    """
    read_files_into = "files"
    """Files will be passed to context with this parameter name, as a dict of
    ``{path: content}``."""
    read_content_arg = "sources"

    def init_parser(self, parser):
        super().init_parser(parser)
        parser.add_argument("sources", nargs="+", type=Path, metavar="SOURCES", help="Input files.")

    def get_context(self, **kwargs):
        """Remove missing files from sources and read files (returned as
        context ``files`` value)."""
        paths = list(self.iter_input_paths(kwargs))

        # missing files
        missings = {path for path in paths if not path[0].exists()}
        if missings:
            lst = "\n".join(f" - {p}" for p in missings)
            self.logs.warn(f"Following sources are missing and wont be proceed:\n{lst}")
            paths = [path for path, _ in paths if path not in missings]

        # source files
        files = {}
        for path, mode in paths:
            with path.open(mode) as f:
                files[path] = self.read_file(f)
        kwargs[self.read_content_arg] = files
        return super().get_context(**kwargs)

    def iter_input_paths(self, kwargs):
        for name in self.read_files_from:
            mode = "r"
            if isinstance(name, (tuple, list)):
                name, mode = name

            value = kwargs.get(name)
            if value:
                self._iter_as_paths(value, mode)

    def _iter_as_paths(self, value, mode):
        if isinstance(value, str):
            yield (Path(value), mode)
        elif isinstance(value, Path):
            yield (value, mode)
        else:
            for val in value:
                self._iter_as_paths(val)

    def read_file(self, file):
        """Return content of provided file."""
        return file.read()

    def save(self, files, originals=None, mode="w"):
        """Save provided files to disk.

        :param {str: []} files: files to save to disk
        :param {str: []} originals: if provided only save file if different
        """
        originals = originals or {}
        for path, value in files.items():
            if value != originals.get(path):
                with path.open(mode) as f:
                    self.write_file(f, value)

    def write_file(self, file, value):
        """Write ``value`` to file stream."""
        file.write(value)
