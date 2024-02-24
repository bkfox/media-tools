from .tabs import Line


class Renderer:
    mime_type = "text/plain"

    template = "{text}"

    tabs_sep = "\n\n\n"
    tabs_template = "{heading}\n{sheet}\n\n{content}"

    heading_sep = " - "
    heading_class = ""
    heading_template = "{text}"

    sheet_sep = ", "
    sheet_prefix = "Accords: "
    sheet_class = ""
    sheet_template = "{text}"

    content_class = {}
    content_template = "{text}"

    line_class = {}
    line_template = "{text}"

    def render(self, tabs_list, **kwargs):
        kwargs["text"] = self.tabs_sep.join(self.render_tabs(tabs, **kwargs) for tabs in (tabs_list or []))
        return self.template.format(**kwargs)

    def render_tabs(self, tabs, **kwargs):
        kwargs.update(
            {
                "heading": self.get_heading(tabs),
                "sheet": self.get_sheet(tabs),
                "content": self.get_content(tabs),
            }
        )
        return self.tabs_template.format(**kwargs)

    def get_heading(self, tabs):
        artist = ""
        if tabs.artist:
            artist = " ".join(v.capitalize() for v in tabs.artist.split(" "))

        text = self.heading_sep.join(h for h in (artist, tabs.title) if h)
        text = self.encode(text)
        return self.heading_template.format(text=text, cl=self.heading_class)

    def get_sheet(self, tabs):
        text = self.sheet_prefix + self.sheet_sep.join(tabs.chords)
        text = self.encode(text)
        return self.sheet_template.format(text=text, cl=self.sheet_class)

    def get_content(self, tabs):
        lines = []
        for line in tabs.lines:
            text = self.encode(self.get_line(line))
            lines.append(text)

        text = "\n".join(lines)
        return self.content_template.format(text=text, cl=self.content_class)

    def get_line(self, line):
        cl = self.line_class.get(line.type, "")
        text = self.encode(line.text)
        return self.line_template.format(text=text, cl=cl)

    def encode(self, text):
        return text


class RTFRenderer(Renderer):
    mime_type = "text/rtf"

    template = (
        "\n".join(
            (
                # note: some lines are split over multiple code lines.
                r"{\rtf1\ansi\deff3\adeflang1025",
                r"{\fonttbl{\f0\froman\fprq2\fcharset0 Times New Roman;}{\f1\froman\fprq2\fcharset2"
                r"Symbol;}{\f2\fswiss\fprq2\fcharset0 Arial;}{\f3\froman\fprq2\fcharset0 Liberation Serif"
                r"{\*\falt Times New Roman};}{\f4\fmodern\fprq1\fcharset0 Liberation Mono{\*\falt Courier New};}"
                r"{\f5\fswiss\fprq2\fcharset0 Liberation Sans{\*\falt Arial};}"
                r"{\f6\fnil\fprq0\fcharset2 OpenSymbol{\*\falt Arial Unicode MS};}"
                r"{\f7\fnil\fprq2\fcharset0 DejaVu Sans;}{\f8\fswiss\fprq0\fcharset0 FreeSans;}"
                r"{\f9\fnil\fprq2\fcharset0 FreeSans;}}",
                r"{\colortbl;\red0\green0\blue0;\red0\green0\blue255;\red0\green255\blue255;\red0\green255\blue0;"
                r"\red255\green0\blue255;\red255\green0\blue0;\red255\green255\blue0;\red255\green255\blue255;"
                r"\red0\green0\blue128;\red0\green128\blue128;\red0\green128\blue0;\red128\green0\blue128;"
                r"\red128\green0\blue0;\red128\green128\blue0;\red128\green128\blue128;\red192\green192\blue192;"
                r"\red89\green131\blue176;\red114\green159\blue207;}",
                r"{\stylesheet{\s0\snext0\rtlch\af9\alang1081 \ltrch\lang2060\langfe2052\loch\widctlpar"
                r"\hyphpar0\ltrpar\cf0\fs24\lang2060\kerning1\dbch\langfe2052 Normal;}",
                r"{\s1\sbasedon32\snext31\rtlch\af7\afs48\ab \ltrch\hich\af3\loch\sb240\sa120\keepn"
                r"\f3\fs48\b\dbch\af7 Heading 1;}",
                r"{\s2\sbasedon32\snext31\rtlch\af9\afs32\ab \ltrch\hich\af5\loch\ilvl1\outlinelevel1"
                r"\sb200\sa120\keepn\f5\fs32\b\dbch\af7 Heading 2;}",
                r"{\*\cs16\snext16\loch\cf17 accord;}",
                r"{\*\cs18\snext18\rtlch\af4 \ltrch\hich\af4\loch\f4\dbch\af4 Source Text;}",
                r"{\s25\sbasedon26\snext25\rtlch\af4\afs20 \ltrch\hich\af4\loch\sb0\sa227\brdrt\brdrnone"
                r"\brdrl\brdrnone\brdrb\brdrhair\brdrw1\brdrcf15\brsp28\brdrr\brdrnone\keepn\cf17\f4\fs18\dbch\af4"
                r" accords-sheet;}",
                r"{\s26\sbasedon27\snext27\rtlch\af4\afs20 \ltrch\hich\af4"
                r"\loch\sb0\sa0\keepn\cf17\f4\fs18\dbch\af4 accords;}",
                r"{\s27\sbasedon0\snext26\rtlch\af4\afs20 \ltrch\hich\af4\loch\sb0\sa0\f4\fs18\dbch\af4"
                r" Preformatted Text;}",
                r"}",
            )
        )
        .replace("{", "{{")
        .replace("}", "}}")
        + ("{text}")
        + "}}"
    )

    tabs_template = (
        "\n{heading}\n{sheet}\n{content}\n"
        r"\par \pard\plain \s27\rtlch\af4\afs20 \ltrch\hich\af4\loch\sb0\sa0\f4\fs18\dbch\af4\ql\sb0\sa0\ltrpar\loch"
    )
    tabs_sep = "\n\\page\n"

    heading_sep = r" – "
    heading_class = r"\s2"
    heading_template = "\n".join(
        (
            r"\pgndec\pard\plain {cl}\rtlch\af9\alang1081 \ltrch\lang2060\langfe2052\loch\widctlpar"
            r"\hyphpar0\ltrpar\cf0\fs24\lang2060\kerning1\dbch\langfe2052\pagebb\ql\ltrpar{{\loch",
            r"{text}}}",
        )
    )

    sheet_prefix = "Accords\~: "
    sheet_class = r"\s25"
    sheet_template = (
        r"\par \pard\plain {cl}\rtlch\af4\afs20 \ltrch\hich\af4\loch\sb0\sa227\brdrt\brdrnone"
        r"\brdrl\brdrnone\brdrb\brdrhair\brdrw1\brdrcf15\brsp28\brdrr\brdrnone\keepn\cf17\f4"
        r"\fs18\dbch\af4\ql\sb0\sa227\brdrt\brdrnone\brdrl\brdrnone\brdrb\brdrhair\brdrw1"
        r"\brdrcf15\brsp28\brdrr\brdrnone\ltrpar{{\loch"
        "\n{text}}}"
    )

    line_class = {
        Line.Type.LYRIC: r"\s27",
        Line.Type.CHORDS: r"\s26",
    }
    line_template = "\n".join(
        (
            r"\par \pard\plain {cl}\rtlch\af4\afs20 \ltrch\hich\af4\loch\sb0\sa0\f4\fs18\dbch\af4\ql"
            r"\ltrpar{{\loch\cs18\rtlch\af4 \ltrch\hich\af4\loch\f4\dbch\af4",
            r"}}{{\loch\cs18\rtlch\af4 \ltrch\hich\af4\loch\f4\dbch\af4\loch",
            r"{text}}}",
        )
    )

    rtf_codes = {
        "’": "{\\'92}",
        "`": "{\\'60}",
        "€": "{\\'80}",
        "…": "{\\'85}",
        "‘": "{\\'91}",
        "̕": "{\\'92}",
        "“": "{\\'93}",
        "”": "{\\'94}",
        "•": "{\\'95}",
        "–": "{\\'96}",
        "—": "{\\'97}",
        "©": "{\\'a9}",
        "«": "{\\'ab}",
        "±": "{\\'b1}",
        "„": '"',
        "´": "{\\'b4}",
        "¸": "{\\'b8}",
        "»": "{\\'bb}",
        "½": "{\\'bd}",
        "Ä": "{\\'c4}",
        "È": "{\\'c8}",
        "É": "{\\'c9}",
        "Ë": "{\\'cb}",
        "Ï": "{\\'cf}",
        "Í": "{\\'cd}",
        "Ó": "{\\'d3}",
        "Ö": "{\\'d6}",
        "Ü": "{\\'dc}",
        "Ú": "{\\'da}",
        "ß": "{\\'df}",
        "à": "{\\'e0}",
        "á": "{\\'e1}",
        "ä": "{\\'e4}",
        "è": "{\\'e8}",
        "é": "{\\'e9}",
        "ê": "{\\'ea}",
        "ë": "{\\'eb}",
        "ï": "{\\'ef}",
        "í": "{\\'ed}",
        "ò": "{\\'f2}",
        "ó": "{\\'f3}",
        "ö": "{\\'f6}",
        "ú": "{\\'fa}",
        "ü": "{\\'fc}",
    }

    empty_line_template = (
        r"\par \pard\plain {cl}\rtlch\af5\afs20 \ltrch\hich\af5\loch\sb0\sa0\keepn\cf17\f5\fs18\dbch"
        r"\af5\ql\keepn\ltrpar\loch\n"
    )

    def get_line(self, line):
        if not line.text:
            cl = self.line_class.get(line.type)
            return self.empty_line_template.format(cl=cl)
        return super(type(self), self).get_line(line)

    def encode(self, text):
        r = ""
        for c in text:
            if c in self.rtf_codes:
                r += self.rtf_codes[c]
            elif 128 < ord(c) < 32768 or c in ",":
                r += r"\uc1\u" + str(ord(c)) + "*"
            elif 32768 < ord(c) < 65536:
                n = ord(c) - 65536
                r += r"\uc1\u" + str(n) + "*"
            else:
                r += c
        return r
