from .tabs import Line, XMLTabs


class InterleavedXMLTabs(XMLTabs):
    """
    Read tabs interleaved from XML tree. Asssumes:
    - only accords are wrapped in tag
    - defaults: https://boiteachansons.net/
    """
    chord_tag = ""
    """ Tag use for chord """
    chord_class = ""
    """ Class used to find chord """
    chord_text_xpath = ""
    """ Xpath to text inside chord """
    chord_text_attr = ""
    """ Attribute to get chord value from XML node. """

    def parse_line(self, line):
        chords = Line(Line.Type.CHORDS)
        lyrics = Line(Line.Type.LYRIC, line.text.lstrip())
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

