import html
import json
import re

import lxml.etree as ET
import requests

from .xml import XMLParser


from .sheet import Line, Sheet


__all__ = ("XMLSource", "ReactSource", "InterleavedXMLSource", "BACSource", "UltimateGSource")


class Source:
    hosts: list[str] = []
    """Class attribute: relevant server list."""
    url: str = ""
    """Source URL."""

    def from_http(self, url):
        resp = requests.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"Error loading {url}: response status: " f"{resp.status_code}.")
        return self.read(url, resp.text)

    def read(self, url, text, **kwargs):
        data = self.parse(text, **kwargs)
        artist = self.get_artist(data, **kwargs) or ""
        title = self.get_title(data, **kwargs) or ""
        lines = self.get_lines(data, **kwargs) or []
        sheet = Sheet(artist=artist, title=title, lines=lines, url=url)
        try:
            sheet.done()
            return sheet
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


class BaseXMLSource(XMLParser, Sheet):
    def read(self, text, **kwargs):
        # should be moved to parse()
        kwargs["root"] = self.parse_xml(text)
        return super().read(text, **kwargs)


class XMLSource(BaseXMLSource):
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

    def get_lines(self, data, root, **_):
        if not self.lines_xpath:
            raise ValueError("`lines_xpath` is not provided")

        lines = []
        for line in root.findall(self.lines_xpath):
            lines += self.parse_line(line)
        return lines

    def parse_line(self, line):
        raise NotImplementedError("not implemented")


class ReactSource(BaseXMLSource):
    """Extract data from a React application page."""

    xml_parser = ET.HTMLParser
    js_store_xpath = ""
    js_store_attr = "data-content"

    def parse(self, text, root, **_):
        if not self.js_store_xpath:
            raise ValueError("`js_store_xpath` not provided")

        node = root.find(self.js_store_xpath)
        raw = node.attrib[self.js_store_attr]
        raw = html.unescape(raw)
        return json.loads(raw)


class InterleavedXMLSource(XMLSource):
    """Read tabs interleaved from XML tree. Asssumes:

    - only accords are wrapped in tag
    """

    chord_tag = ""
    """Tag use for chord."""
    chord_class = ""
    """Class used to find chord."""
    chord_text_xpath = ""
    """Xpath to text inside chord."""
    chord_text_attr = ""
    """Attribute to get chord value from XML node."""

    def parse_line(self, line):
        chords = Line(Line.Type.CHORDS)
        lyrics = Line(Line.Type.LYRIC, (line.text or "").lstrip())
        for child in line:
            cl = child.attrib.get("class")
            match child.tag:
                case self.chord_tag if self.chord_class in cl:
                    pad = max(len(lyrics) - len(chords), 0)
                    chord = self.get_chord(child)
                    chords.add_chord(chord, pad)
                    if child.tail:
                        lyrics.add(child.tail)
                case _:
                    lyrics.add(child.tail)
        return [chords, lyrics]

    def get_chord(self, node):
        child = node
        if self.chord_text_xpath:
            child = node.find(self.chord_text_xpath)
        if child is None:
            return node

        chord = None
        if self.chord_text_attr:
            chord = child.attrib.get(self.chord_text_attr)
        if not chord:
            chord = child.text
        return chord or ""


class BACSource(InterleavedXMLSource):
    hosts = ["boiteachansons.net", "www.boiteachansons.net"]

    artist_xpath = """.//div[@id="dTitreNomArtiste"]//h2"""
    title_xpath = """.//div[@class="dTitrePartition"]/h1"""
    lines_xpath = """.//div[@class="pLgn"]"""

    chord_tag = "span"
    chord_class = "interl"
    chord_text_xpath = """span[@class="a"]"""
    chord_text_attr = "data-accord"


class UltimateGSource(ReactSource):
    hosts = [
        "tabs.ultimate-guitar.com",
        "ultimate-guitar.com",
    ]

    js_store_xpath = ".//div[@class='js-store']"
    tab_rg = re.compile(r"\[tab\](?P<tab>.*?)\[/tab\]")
    chord_rg = re.compile(r"\[chord\](?P<chord>.*?)\[/chord\]")

    def parse(self, *args, **kwargs):
        data = super().parse(*args, **kwargs)
        return data["store"]["page"]["data"]

    def get_artist(self, data, **_):
        return data["tab"]["artist_name"]

    def get_title(self, data, **_):
        return data["tab"]["song_name"]

    _clean_up = ["[tab]", "[/tab]"]

    def get_lines(self, data, **_):
        part = data["tab_view"]["wiki_tab"]["content"]
        part = part.replace("\r\n", "\n").replace("\n\n\n", "\n\n")

        lines = []
        for line in part.split("\n"):
            for m in self._clean_up:
                line = line.replace(m, "")

            if "[ch]" in line:
                line = line.replace("[ch]", "").replace("[/ch]", "")
                line = Line(Line.Type.CHORDS, line)
            else:
                line = Line(Line.Type.LYRIC, line)
            lines.append(line)
        return lines


# tabs = UltimateGSource.from_http("https://tabs.ultimate-guitar.com/tab/3649919")
# gtabs = UltimateGSource.from_http("https://tabs.ultimate-guitar.com/tab/2692788")
