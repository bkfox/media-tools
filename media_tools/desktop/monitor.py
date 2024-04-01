# TODO:
# - App:
#   - load from yaml
#   - main screen
#
import itertools
import json
import re
import subprocess


from media_tools.conf import App, ConfigFile


__all__ = ("Layout", "Layouts", "MonitorsApp")


class Layout:
    def __init__(self, lines, name=None, extras=None):
        self.name = name
        self.lines = lines
        self.outputs = set(itertools.chain(*lines))
        self.extras = extras or {}

    def matches(self, outputs: set):
        """Return True if the provided outputs matches this layout."""
        return all(name for name in outputs if name in self.outputs)

    def matches_score(self, outputs: set):
        """Return True if the provided outputs matches this layout."""
        return sum(1 for name in outputs if name in self.outputs)

    def get_args(self, outputs, extras={}):
        """Return xrandr args as a list for this layout."""
        positions = self.get_positions()
        extras = self.get_extras(extras)

        args = []
        for output, position in positions.items():
            args.extend(("--output", output))

            # extras arguments
            extras = extras.get(output) or tuple()
            if "--mode" not in extras:
                extras = extras + ("--auto",)
            args.extend(extras)

            # position
            args.extend(itertools.chain(*((f"--{pos}", target) for pos, target in position.items())))
            if not outputs.get(output):
                args.append("--off")
        return args

    def get_extras(self, extras={}):
        """Return extras arguments merged with provided one."""
        if not extras:
            return self.extras

        result = {}
        keys = set(itertools.chain(*extras.keys(), *self.extras.keys()))
        for key in keys:
            result[key] = (self.extras.get(key) or tuple()) + (extras.get(key) or tuple())
        return result

    def get_positions(self):
        """Return outputs positions as a dict."""
        positions = {}
        n_lines = len(self.lines)
        for y, row in enumerate(self.lines):
            for x, output in enumerate(row):
                pos = {}

                # above
                row_below = n_lines > y + 1 and self.lines[y + 1]
                below = row_below and len(row_below) > x and row_below[x]
                if below:
                    pos["above"] = below

                # left-of
                left = len(row) > x + 1 and row[x + 1]
                if left:
                    pos["left-of"] = left

                positions[output] = pos
        return positions


class Layouts:
    """Handle multiple layouts, matching, run."""

    app = "xrandr"

    def __init__(self, layouts=None, extras=None):
        layouts = layouts or []
        layouts = [Layout(**layout) if isinstance(layout, dict) else layout for layout in layouts]

        self.layouts = layouts
        self.extras = extras or {}

    _outputs_re = re.compile(r"(?P<name>(e?DP|HDMI)(-?[0-9])+) +(?P<status>(dis)?connected)", re.IGNORECASE)

    def get_outputs(self):
        result = subprocess.run(["xrandr"], capture_output=True)
        stdout = result.stdout.decode(encoding="utf-8")
        return {
            r["name"]: r["status"] == "connected" for r in (p.groupdict() for p in self._outputs_re.finditer(stdout))
        }

    def get_layout(self, outputs, layout=None):
        if not self.layouts:
            return None
        if layout:
            return next((obj for obj in self.layouts if obj.name == layout), None)

        connected = set(n for n, c in outputs.items() if c)
        layout = next((layout for layout in self.layouts if layout.matches(connected)), None)
        if layout is None:
            scores = [(layout.matches_score(connected), layout) for layout in self.layouts]
            scores.sort(key=lambda s: -s[0])
            layout = scores[0]
        return layout

    def run(self, layout, extras={}):
        outputs = self.get_outputs()
        print("Outputs:", outputs)

        layout = self.get_layout(outputs, layout)
        print("Layout:", layout)

        if not layout:
            raise RuntimeError("no layout has been found")

        extras = {**self.extras, **extras}
        args = layout.get_args(outputs, extras)
        print(f"{self.app}'s args:", args)

        subprocess.run([self.app] + args)


class MonitorsApp(App):
    name = "monitors"
    label = "Monitors"
    description = (
        "Handle multiple monitor setup.\n"
        "\n"
        "Layout arguments: lines (list of string), name, extras (dict of key-value xrand args)."
        "\n"
        "By default, it will try to read YAML file from '$XDG_CONFIG_HOME/.media_tools/apps/monitor.yaml'"
    )
    config_file = ConfigFile("apps/monitor.yaml", Layouts)

    def init_parser(self, parser):
        parser.add_argument("--layout", type=str, description="Run layout of provided one.")
        parser.add_argument("--extras", type=json.loads, description="Run layout of provided one.")

    def run(self, conf, **kwargs):
        layouts = conf
        layouts.run(**kwargs)
