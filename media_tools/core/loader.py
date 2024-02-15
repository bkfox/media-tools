from importlib import import_module
from pathlib import Path
import sys


__all__ = ("Loader",)


class Package:
    def __init__(self, name, path, module=None):
        self.name = name
        self.path = path
        self.module = module

    def load(self, force_reload=False):
        """ Get package module, load it if required. """
        if not self.module or force_reload:
            self.module = import_module(self.name)
        return self.module

    def find(self, lookup):
        """ Search for submodule by name and return Package. """
        path = self._find(lookup)
        return path and Package(self.name + "." + lookup, path) or None

    def _find(self, lookup):
        """ Search for module for provided submodule name and return path. """
        lookup = lookup.replace(".", "/")
        path = self.path / lookup / "__init__.py"
        if path.is_file():
            return path

        path = self.path / (lookup + ".py")
        return path.is_file() and path or None

    def find_all(self, lookup):
        """ Yield application modules names found into self's dir.
        :param str lookup: module name to lookup for into current directory
        """
        lookup = lookup + ".py" 
        for path in self.path.iterdir():
            path = path / lookup
            if path.exists():
                name = f"{self.name}.{path.parent.stem}.{path.stem}"
                yield Package(name, path)

    def as_tuple(self):
        return (self.name, self.path)

    def __eq__(self, other):
        return self.as_tuple() == other.as_tuple()

    def __hash__(self):
        return hash(self.as_tuple()) 


class Loader:
    """
    Load modules from provided directories.
    """
    filename = ""
    search_packages = None

    def __init__(self, filename, search_packages):
        self.filename = filename or self.filename
        self.search_packages = {}
        for package in search_packages:
            self.register(package)

    def register(self, package):
        if isinstance(package, (list, tuple)):
           package = Package(package[0], package[1])
        self.search_packages[package.name] = package

    def load(self, name):
        for package in self.search_packages.values():
            if package := package.find(name):
                package.load(name)
                return package

    def load_all(self, name):
        packages = []
        errors = []
        for package in self.find_all(name):
            try:
                package.load()
                packages.append(package)
            except Exception as err:
                import traceback
                traceback.print_exc()
                errors.append((package, err))

        if errors:
            errors = "\n".join(
                f"- {package.name} ({package.path}): {err}"
                for package, err in errors
            )
            msg = "Error loading packages:\n" + errors
            raise RuntimeError(msg)
        return packages

    def find(self, name):
        for package in self.search_packages.values():
            if found := package.search(name):
                return found
        return found

    def find_all(self, name):
        return (
            child for package in self.search_packages.values()
            for child in package.find_all(name)
        )
