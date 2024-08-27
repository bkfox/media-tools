import yaml
from typing import Any, Iterable


from media_tools.core import logs
from . import renderers
from .sheet import Line, Sheet
from .xml import XMLParser


__all__ = ("Storage", "YamlStorage")


class Storage:
    mime_type = ""
    file_ext = ""
    desc = ""

    def __init__(self, path, load=True):
        self.path = path
        self.items = {}
        if load:
            self.load()

    @classmethod
    def get_key(cls, item):
        return item.url or (item.artist, item.title)

    def update(self, items):
        self.items.update((self.get_key(item), item) for item in items)

    def filter(self, pred):
        return (item for item in self.items.values() if pred(item))

    def sort_key(item):
        return item.artist, item.title

    def get_items(self, filter=None, sort=sort_key):
        if filter:
            items = filter and self.filter(filter) or self.items.values()
        else:
            items = self.items.values()

        if sort:
            items = sorted(items, key=sort)
        return list(items)

    def load(self):
        if self.path and self.path.exists():
            with open(self.path) as stream:
                it = self.deserialize(self.path, stream)
                it and self.update(it)

    def save(self, filter=None, sort=sort_key):
        if self.path:
            with open(self.path, "w") as stream:
                items = self.get_items(filter, sort)
                content = self.serialize(self.path, items)
                stream.write(content)

    def deserialize(self, path, stream) -> Iterable[Any] | None:
        return None

    def serialize(self, path, items) -> str:
        return ""

    def __contains__(self, key):
        return key in self.items


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
        return Sheet(**sheet)

    def serialize(self, path, items):
        data = []
        dir = path.parent
        for item in items:
            item.serialize()
            item.path = item.path or (dir / item.get_filename())
            item.save_to_file(item.path)
            data.append(item.serialize(lines=False, path=str(item.path.relative_to(dir))))
        return yaml.dump(data)


class YamlStorage(Storage):
    mime_type = "application/yaml"
    file_ext = "yaml"
    description = "Save sheets into YAML format file."

    def deserialize(self, path, stream):
        data = yaml.load(stream, Loader=yaml.Loader)
        return data and (Sheet(**dats) for dats in data)

    def serialize(self, path, items):
        items = [item.serialize() for item in items]
        return yaml.dump(items)


class RtfStorage(Storage):
    mime_type = "text/rtf"
    file_ext = "rtf"
    description = "Save sheets into RTF file (export only)."

    def deserialize(self, path, stream):
        pass
        # raise NotImplementedError("RTF reading is not supported")

    def serialize(self, path, items):
        renderer = renderers.RtfRenderer()
        return renderer.render(items)


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

        return Sheet(lines=lines, chords=chords, artist=artist.strip(), title=title.strip())

    def serialize(self, path, items):
        raise NotImplementedError("LibreOffice HTML writing is not supported.")
