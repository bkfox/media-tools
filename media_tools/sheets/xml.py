import re
import lxml.etree as ET


__all__ = ("XMLParser",)


class XMLParser:
    xml_parser = ET.XMLParser
    xml_root = re.compile("<body [^>]*>(.*)</body>", re.S | re.I)
    """Root node to content."""
    xml_clean = (
        re.compile("<style>(.*?)</style>", re.S | re.I),
        re.compile("<script>(.*?)</script>", re.S | re.I),
    )
    """Remove content inside root matching provided regexps."""

    def __init__(self, xml_parser=xml_parser):
        self.xml_parser = xml_parser

    def parse_xml(self, text):
        root_match = self.xml_root.search(text)
        if root_match:
            text = root_match.group(0)
            for reg in self.xml_clean:
                text = reg.sub("", text)

        parser = self.xml_parser(recover=True)
        root = ET.fromstring(f"<section>{text}</section>", parser)
        return root
