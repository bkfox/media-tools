from pathlib import Path

from .loader import Loader
from .app import action, App
from .logs import logs


__all__ = (
    "search_paths",
    "Apps",
    "apps",
)


search_paths = (("media_tools", Path(__file__).parent.parent),)
"""Search applications paths used by CLI tools."""


class Apps(App):
    """Handle dispatching to multiple registered applications."""

    loader = None
    """Applications loader."""
    subparsers = None
    """ArgumentParser's subparsers."""
    apps = {}
    """Registered applications."""

    def __init__(self, children=None, loader=None):
        self.loader = loader
        self.apps = {}
        if children:
            for app in children:
                self.register(app=app)

    def register(self, app=None, **app_init_kwargs):
        """Register an application.

        Two usages:
        - as class decorator: arguments are app init kwargs
        - as regular function call: app is passed as argument
        """
        if app is not None:
            self._register(app)
            return app

        def wrapper(app_class):
            self._register(app_class(**app_init_kwargs))
            return app_class

        return wrapper

    def _register(self, app, name=""):
        name = name or app.name
        if app.name in self.apps:
            raise KeyError(f'An application "{name}" is already registered')
        self.apps[name] = app
        return app

    def get(self, name):
        """Get application for the provided name.

        If not found, load it.
        """
        if name not in self.apps:
            package = self.loader.load(name + ".apps")
            package and self.load_package(package)
        return self.apps.get(name)

    def load_all(self):
        if not self.subparsers:
            self.load()
        for package in self.loader.load_all("apps"):
            self.load_package(package)

    def load_package(self, package):
        if package.name == __name__:
            return

        apps = getattr(package.module, "apps", tuple())
        if isinstance(apps, App):
            apps = (apps,)

        for app in apps:
            if app.name not in self.apps:
                self.register(app)
            app.load(subparsers=self.subparsers)
        return apps

    def load(self, subparsers=None):
        """Load Apps instance. Initialize parser and applications.

        :param Iterable[App] apps: load those apps instead
        """
        if self.parser:
            return self.parser

        super().load(subparsers=subparsers)
        self.subparsers = self.parser.add_subparsers()
        for app in self.apps.values():
            app.load(subparsers=self.subparsers)

    def dispatch(self, argv=None, app=None, **kwargs):
        if app is None and argv:
            app = self.get(argv[0])
        return super().dispatch(argv=argv, app=app, **kwargs)

    def run(self, app=None, **kwargs):
        if app:
            return app.dispatch(**kwargs)
        return super().run(**kwargs)

    @action("actions", action="store_true", help="List available subcommands")
    def print_actions(self, **_):
        if not self.apps:
            self.load_all()
        logs.out("Here is a list of available subcommand. Use `action --help` to get more info.\n")
        for name, app in self.apps.items():
            if app:
                logs.out(
                    f"**!!{app.label}!! ({app.name})**\n"
                    f"//Invokation: {self.name} {app.name}//\n"
                    f"//Help: {self.name} {app.name} --help//\n"
                    "\n"
                    f"{app.description or app.help or ''}\n"
                )


apps = Apps(loader=Loader("apps", search_paths))
