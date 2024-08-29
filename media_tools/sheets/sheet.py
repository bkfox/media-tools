from datetime import date, datetime
import enum
from pathlib import Path
from typing import Iterable


__all__ = (
    "Line",
    "Sheet",
)


class Line:
    class Type(enum.StrEnum):
        LYRIC = "l"
        CHORDS = "c"
        TAB = "t"
        INFO = "i"

    type = None
    """Type."""
    text = ""
    """Content plain text."""
    chords = None
    """set of extracted chords (on Type.CHORDS)"""

    def __init__(self, type, text="", chords=None):
        self.type = type
        self.text = text.replace(" ", " ")
        if type == self.Type.CHORDS:
            self.chords = chords and set(chords) or set()

    @classmethod
    def from_string(cls, text):
        if not text:
            return cls(cls.Type.LYRIC, "")
        if " > " in text:
            type, text = text.split(" > ", maxsplit=1)
        else:
            type, text = cls.Type.LYRIC, text
        return cls(cls.Type(type), text)

    def to_string(self):
        return f"{self.type.value} > {self.text}"

    _not_a_chord = {"N.C.", "|"}

    def done(self):
        if not self.text:
            return

        # clean up
        if self.text[-1] == "\n":
            self.text = self.text[:-1]
        if self.text.count(" ") == len(self.text):
            self.text = ""

        # chords
        if self.type == self.Type.CHORDS:
            chords = set(c.replace("|", "") for c in self.text.split(" ") if c and c not in self._not_a_chord)
            self.chords = chords

    def add(self, text):
        self.text += text

    def add_chord(self, chord, pad):
        if self.chords:
            pad = max(pad, 1)
        self.text += " " * pad + chord

    def __len__(self):
        return len(self.text)


class Sheet:
    artist: str = ""
    """Artist name."""
    title: str = ""
    """Song title."""
    tags: list[str] = None
    """User defined tags."""
    chords: set[str] = set()
    """Discovered chords."""
    path: Path | None = None
    """Path to lyrics file."""
    version: date | None = None
    """Add date."""

    @property
    def label(self):
        if self.artist:
            return f"{self.artist} -- {self.title}"
        return self.title

    def __init__(
        self,
        lines: list[str] = "",
        chords: str | set[str] = None,
        tags: str | set[str] = None,
        version: date | None = None,
        **kwargs,
    ):
        self.chords = self._as_set(chords)
        self.tags = self._as_set(tags)
        if lines:
            self.lines = lines
        if isinstance(date, str):
            self.version = datetime.strptime(date, "%Y-%m-%d").date
        else:
            self.version = version or date.today()

        self.__dict__.update(**kwargs)

    def _as_set(self, value):
        if isinstance(value, str):
            value = value.split(", ")
        else:
            value = value or []
        return {v for v in value if v}

    _lines = None

    @property
    def lines(self):
        if self._lines is None:
            self.lines = self.path and self.load_from_file(self.path) or []
        return self._lines

    @lines.setter
    def lines(self, value: Iterable[str] | Iterable[Line]):
        self._lines = [Line.from_string(line) if isinstance(line, str) else line for line in value]

    def load_from_file(self, path: Path) -> Iterable[Line]:
        """Load lines from file."""
        if not path.exists():
            return []
        with open(path) as stream:
            return (Line.from_string(line) for line in stream.readlines())

    def save_to_file(self, path: Path, force=False):
        if not force and path.exists():
            return
        with open(path, "w") as stream:
            stream.write("\n".join(line.to_string() for line in self.lines))

    def get_filename(self):
        if self.artist:
            path = f"{self.artist} -- {self.title}"
        else:
            path = f"{self.title}"

        if self.url:
            post = self.url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "")
            path += f" -- {post}"
        return path + ".txt"

    def serialize(self, lines=True, **kwargs):
        """Return serialized version of sheet."""
        res = {
            "artist": self.artist,
            "title": self.title,
            "version": self.version,
            "tags": ", ".join(self.tags),
            "url": self.url,
            "chords": ", ".join(self.chords),
            **kwargs,
        }
        if lines:
            res["lines"] = [line.to_string() for line in self.lines]
        return res

    # TODO: move to external class

    def done(self):
        self.chords = set()
        try:
            for line in self.lines:
                if "http://" in line.text or "https://" in line.text:
                    self.lines.remove(line)
                    continue

                line.done()
                if line.type == line.Type.CHORDS and line.chords:
                    self.chords |= set(line.chords)
        except Exception:
            breakpoint()
            raise
