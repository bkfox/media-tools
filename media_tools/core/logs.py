import re
import logging

__all__ = ("Logs", "logs")


class Logs:
    """Provide logging utilities."""

    logger = logging.getLogger("")
    """Logger used by the task in order to log informations."""

    _log_levels = {
        "out": (0, "", logging.INFO),
        "info": (0, "I", logging.INFO),
        "success": (92, "S", logging.INFO),
        "error": (91, "E", logging.ERROR),
        "warning": (33, "W", logging.WARNING),
    }

    def __init__(self, name):
        self.reset(name)

    def reset(self, name):
        self.logger = logging.getLogger(name)

    # ---- output
    def log(self, level, prefix, msg=None, *args, exc=None, pad=0, format=True, **kwargs):
        color, key, lev = self._log_levels[level]
        if msg is None:
            msg, prefix = prefix, ""

        if format:
            msg = self.format(msg)

        msg = f"\033[{color}m" + (f"[{key}]" if key else "") + (f"[{prefix}]" if prefix else "") + (f"{msg}\033[0m")
        print(msg, *args)

    def out(self, *args, **kw):
        self.log("out", *args, **kw)

    def info(self, *a, **kw):
        self.log("info", *a, **kw)

    def success(self, *a, **kw):
        self.log("success", *a, **kw)

    def warn(self, *a, **kw):
        self.log("warning", *a, **kw)

    def err(self, *a, **kw):
        self.log("error", *a, **kw)

    # ---- formatting
    effects = {
        "bold": (1, re.compile(r"\*\*([^\n]+)\*\*")),
        "italic": (3, re.compile(r"//([^\n]+)//")),
        "underline": (4, re.compile(r"__([^\n]+)__")),
        "strike": (4, re.compile(r"~~([^\n]+)~~")),
        "warning": (33, re.compile(r"!!([^\n]+)!!")),
        "error": (91, re.compile(r"!!!([^\n]+)!!!")),
    }

    def format(self, msg, **kwargs):
        for code, reg in self.effects.values():
            msg = reg.sub(f"\033[{code}m\\1\033[0m", msg)
        return msg


logs = Logs("media_tools")
