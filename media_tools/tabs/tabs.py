import enum
import html
import json
import re
import lxml.etree as ET

import requests


__all__ = ("Line", "Tabs", "XMLTabs")


class Line:
    class Type(enum.IntEnum):
        LYRIC = 0x00
        CHORDS = 0x01

    type = None
    """Type."""
    text = ""
    """Content plain text."""
    chords = None
    """set of extracted chords (on Type.CHORDS)"""

    def __init__(self, type, text="", chords=None):
        self.type = type
        self.text = text
        if type == self.Type.CHORDS:
            self.chords = chords and set(chords) or set()

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


class Tabs:
    hosts = []

    artist = ""
    """Artist name."""
    title = ""
    """Song title."""
    chords = set()
    """Chords discovered."""
    lines = None
    """Read lines."""

    def __init__(self, text=None, **kwargs):
        self.text = text
        self.chords = set()
        self.__dict__.update(**kwargs)
        if text:
            self.read(text)

    @classmethod
    def from_http(cls, url):
        resp = requests.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"Error loading {url}: response status: " f"{resp.status_code}.")
        return cls(resp.text)

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as file:
            return cls(text=file.read())

    @classmethod
    def from_input(cls):
        return cls(text=input())

    def read(self, text, **kwargs):
        data = self.parse(text, **kwargs)
        self.artist = self.get_artist(data, **kwargs) or ""
        self.title = self.get_title(data, **kwargs) or ""
        self.lines = self.get_lines(data, **kwargs) or []
        try:
            self.done()
        except Exception:
            import traceback

            traceback.print_exc()
            raise

    def parse(self, text, **kwargs):
        return text

    def get_artist(self, data, **kwargs):
        pass

    def get_title(self, data, **kwargs):
        pass

    def get_lines(self, data, **kwargs):
        pass

    def done(self):
        self.chords = set()
        for line in self.lines:
            if "http://" in line.text or "https://" in line.text:
                self.lines.remove(line)
                continue

            line.done()
            if line.type == line.Type.CHORDS and line.chords:
                self.chords |= set(line.chords)


class BaseXMLTabs(Tabs):
    xml_parser = ET.XMLParser
    xml_root = re.compile("<body>(.*)</body>", re.S | re.I)
    """Root node to content."""
    xml_clean = (
        re.compile("<style>(.*?)</style>", re.S | re.I),
        re.compile("<script>(.*?)</script>", re.S | re.I),
    )
    """Remove content inside root matching provided regexps."""

    def read(self, text, **kwargs):
        # should be moved to parse()
        root_match = self.xml_root.search(text)
        if root_match:
            text = root_match.group(0)
            for reg in self.xml_clean:
                text = reg.sub("", text)

        parser = self.xml_parser(recover=True)
        root = ET.fromstring(f"<section>{text}</section>", parser)

        kwargs.update(
            {
                "parser": parser,
                "root": root,
            }
        )
        return super().read(text, **kwargs)


class XMLTabs(BaseXMLTabs):
    """Parse and extract tabs from xml document."""

    artist_xpath = ""
    """xpath to artist."""
    title_xpath = ""
    """xpath to title."""
    lines_xpath = ""
    """xpath to lines."""

    def get_artist(self, data, root, **_):
        if self.artist_xpath:
            node = root.find(self.artist_xpath)
            return node.text if node is not None else ""

    def get_title(self, data, root, **_):
        if self.title_xpath:
            node = root.find(self.title_xpath)
            return node.text if node is not None else ""

    def get_lines(self, data, root, parser):
        if not self.lines_xpath:
            raise ValueError("`lines_xpath` is not provided")

        lines = []
        for line in root.findall(self.lines_xpath):
            lines += self.parse_line(line)
        return lines

    def parse_line(self, line):
        raise NotImplementedError("not implemented")


class ReactTabs(BaseXMLTabs):
    xml_parser = ET.HTMLParser
    unescape_html = True
    js_store_xpath = ""
    js_store_attr = "data-content"

    def parse(self, text, root, **_):
        if not self.js_store_xpath:
            raise ValueError("`js_store_xpath` not provided")

        node = root.find(self.js_store_xpath)
        raw = node.attrib[self.js_store_attr]
        raw = html.unescape(raw)
        breakpoint()
        return json.loads(raw)
