from __future__ import annotations
from pathlib import Path
import inspect
from typing import Any, Iterable

import yaml

from media_tools.core import logs
from . import odf
from .sheet import Line, Sheet
from .xml import XMLParser


__all__ = ("Storage", "ISheetStorage", "YamlStorage", "OdfStorage", "LibreOfficeHTMLStorage")


class SheetCollection:
    items: dict[Any, Sheet] = None

    def __init__(self, items: dict | None = None):
        self.items = items or {}

    @staticmethod
    def sort_key(item):
        """Return key to sort items."""
        return item.artist, item.title

    @classmethod
    def get_key(cls, item):
        """Get dict key for item."""
        return item.url or (item.artist, item.title)

    def update(self, items: Iterable[Sheet] | SheetCollection):
        """Update collection with provided items."""
        if isinstance(items, Storage):
            items = items.items.values()
        self.items.update((self.get_key(item), item) for item in items)

    def filter(self, pred):
        """Return an iterator of items using provided filter predicate."""
        return (item for item in self.items.values() if pred(item))

    def keep(self, pred):
        """Keep only items matching provided predicate."""
        self.items = {key: item for key, item in self.items if pred(item)}

    def get_items(self, filter=None, sort=sort_key):
        """Return a list of items filtered by provided predicate and sorted
        using sort key."""
        if filter:
            items = filter and self.filter(filter) or self.items.values()
        else:
            items = self.items.values()

        if sort:
            items = sorted(items, key=sort)
        return list(items)

    def __iter__(self):
        return iter(self.items.values())

    def __len__(self):
        return len(self.items)

    def __contains__(self, key):
        return key in self.items


class Storage(SheetCollection):
    mime_type = ""
    file_ext = ""
    file_mode = "t"
    desc = ""
    sheet_class = Sheet

    def __init__(self, path, load=False, **kwargs):
        self.path = path
        super().__init__(**kwargs)
        if load:
            self.load()

    def load(self, path=None):
        """Load sheets from file into storage. When path is provided,
        instanciate the corresponding Storage class instance and deserialize
        from it.

        :param Path path: if provided use this source file instead of provided one.
        """
        source = get_storage(path) if path else self
        if source.path and source.path.exists():
            with open(source.path, f"r+{self.file_mode}") as stream:
                it = source.deserialize(source.path, stream)
                it and self.update(it)

    def save(self, filter=None, sort=SheetCollection.sort_key):
        """Save storage to file."""
        if self.path:
            with open(self.path, f"w+{self.file_mode}") as stream:
                items = self.get_items(filter, sort)
                self.prepare_items(items)
                logs.info(f"Save {len(items)} to {self.path}.")
                self.serialize(self.path, stream, items)

    def prepare_items(self, items):
        for item in items:
            if not item.chords:
                item.done()

    def deserialize(self, path, stream) -> Iterable[Sheet] | None:
        """Read sheets from provided stream returning an iterable of Sheets."""
        return None

    def serialize(self, path, stream, items) -> str:
        """Serialize sheets in order to save them in to file."""
        return ""


class ISheetStorage(Storage):
    file_ext = "isheet"
    description = "Load and save sheets index in .isheet yaml file. Sheets are saved under the same directory."

    def deserialize(self, path, stream):
        index = yaml.load(stream, Loader=yaml.Loader)
        if not index:
            return []
        dir = path.parent
        return [sheet for sheet in (self.load_sheet(dir, dat) for dat in index) if sheet]

    def load_sheet(self, dir, sheet):
        path = dir / sheet.get("path")
        if not path.exists:
            logs.warn(f"Missing content file for sheet {sheet}")
            return
        sheet["path"] = path
        return self.sheet_class(**sheet)

    def serialize(self, path, stream, items):
        data = []
        dir = path.parent
        for item in items:
            item.serialize()
            item.path = item.path or (dir / item.get_filename())
            item.save_to_file(item.path)
            data.append(item.serialize(lines=False, path=str(item.path.relative_to(dir))))
        yaml.dump(data, stream)


class YamlStorage(Storage):
    mime_type = "application/yaml"
    file_ext = "yaml"
    description = "Save sheets into YAML format file."

    def deserialize(self, path, stream):
        data = yaml.load(stream, Loader=yaml.Loader)
        return data and (self.sheet_class(**dats) for dats in data)

    def serialize(self, path, stream, items):
        items = [item.serialize() for item in items]
        yaml.dump(items, stream)


class OdfStorage(Storage):
    file_ext = "odt"
    file_mode = "b"
    description = "Render sheets into ODT document"

    def serialize(self, path, stream, items):
        odf.OdfRenderer().render(stream, items)


class LibreOfficeHTMLStorage(Storage):
    file_ext = "lhtml"
    description = "Parse sheet exported from libreoffice (import only)"

    heading_xpath = ".//h2"
    section_xpath = ".//a"

    def __init__(self, *args, **kwargs):
        import lxml.etree as ET

        self.parser = XMLParser(ET.HTMLParser)
        super().__init__(*args, **kwargs)

    def deserialize(self, path, stream):
        text = stream.read()
        text = text.replace("\xa0", " ")
        root = self.parser.parse_xml(text)

        sheets = []
        for heading in root.findall(self.heading_xpath):
            sheet = self.deserialize_sheet(heading)
            sheet and sheets.append(sheet)
        return sheets

    _h_split = (" – ", " - ")

    def deserialize_sheet(self, heading):
        heading_text = "".join(heading.itertext()).strip()
        artist, title = "", ""
        print(">>", heading_text)
        if "\n" in heading_text:
            breakpoint()
        for sep in self._h_split:
            if sep in heading_text:
                artist, title = heading_text.split(sep, maxsplit=1)

        if not artist:
            title = heading_text

        section = heading.getnext()
        if section is None:
            return

        chords = None
        lines = []
        for el in section.findall(".//p"):
            cl = el.attrib.get("class")
            text = "".join(el.itertext())
            match cl:
                case None:
                    continue
                case cl if text.startswith("Accords :"):
                    if ":" in text:
                        text = text.split(":", maxsplit=1)[1]
                    chords = set(c for c in text.split(" ") if c)
                    continue
                case "paragraph-accords":
                    ty = Line.Type.CHORDS
                case _:
                    ty = Line.Type.LYRIC
            line = Line(ty, text)
            lines.append(line)

        return self.sheet_class(lines=lines, chords=chords, artist=artist.strip(), title=title.strip())

    def serialize(self, path, stream, items):
        raise NotImplementedError("LibreOffice HTML writing is not supported.")


storages = (
    item for item in list(globals().values()) if inspect.isclass(item) and issubclass(item, Storage) and item.file_ext
)
storages = {item.file_ext: item for item in storages}
"""Storage classes by file extension."""


def get_storage(path: Path, **kwargs):
    """Return storage instance for the corresponding path or None."""
    ext = path.suffix[1:]
    cls = storages.get(ext)
    return cls and cls(path, **kwargs)
