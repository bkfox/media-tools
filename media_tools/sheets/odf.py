from odfdo import Element, Document, Header, Paragraph, PageBreak, Section, Style

from .sheet import Line

__all__ = ("OdfRenderer",)


column_section_style = """
    <style:style style:name="two_cols" style:family="section">
        <style:section-properties text:dont-balance-text-columns="false" style:editable="false">
            <style:columns fo:column-count="2" fo:column-gap="0.497cm">
                <style:column style:rel-width="32767*" fo:start-indent="0cm" fo:end-indent="0.248cm"/>
                <style:column style:rel-width="32768*" fo:start-indent="0.248cm" fo:end-indent="0cm"/>
            </style:columns>
        </style:section-properties>
    </style:style>
"""


class OdfRenderer:
    heading_sep = r" – "
    heading_level = 2

    chords_color = "#5983b0"
    chords_summary_label = "Accords: {chords}"

    paragraph_style = {
        "family": "paragraph",
        "font": "Liberation Mono",
        "font_family": "Liberation Mono",
        "parent_style": "Preformatted Text",
        "size": "9pt",
    }
    text_props = {
        "style:font-name": "Liberation Mono1",
        "fo:font-family": "Liberation Mono",
    }

    styles = (
        {
            "name": "chords-summary",
            **paragraph_style,
            "props": {
                "fo:border-bottom": "0.06pt solid #808080",
                "fo:margin-bottom": "0.4cm",
                "fo:padding": "0.049cm",
            },
            "text-props": {
                **text_props,
                "fo:color": chords_color,
            },
        },
        {
            "name": "chords",
            **paragraph_style,
            "props": {
                "fo:keep-with-next": "always",
            },
            "text-props": {
                **text_props,
                "fo:color": chords_color,
            },
        },
        {
            "name": "lyrics",
            **paragraph_style,
            "text-props": {
                **text_props,
            },
        },
    )
    line_styles = {
        Line.Type.LYRIC: "lyrics",
        Line.Type.CHORDS: "chords",
    }

    def render(self, target, sheets):
        document = Document("text")
        document.add_page_break_style()
        body = document.body
        body.clear()

        for style in self.get_styles():
            document.insert_style(style)

        for sheet in sheets:
            self.render_sheet(sheet, body)

        document.save(target)

    def render_sheet(self, sheet, body):
        elements = [
            self.get_heading(sheet),
            self.get_chords(sheet),
        ]
        elements += self.get_lines(sheet)
        for el in elements:
            body.append(el)
        body.append(PageBreak())

    def get_styles(self):
        styles = []
        for style in self.styles:
            styles.append(self.get_style(style))

        style = Element.from_tag(column_section_style)
        styles.append(style)
        return styles

    def get_style(self, style):
        text_props = style.pop("text-props", None)
        props = style.pop("props", None)

        style = Style(**style)
        if props:
            style.set_properties(props)
        if text_props:
            text_style = Style(family="text")
            text_style.set_properties(text_props)
            style.append(text_style.children[0])
        return style

    def get_heading(self, sheet):
        artist = ""
        if sheet.artist:
            artist = " ".join(v.capitalize() for v in sheet.artist.split(" "))

        return Header(
            self.heading_level,
            self.heading_sep.join(h for h in (artist, sheet.title) if h),
            suppress_numbering=True,
        )

    def get_chords(self, sheet):
        return Paragraph(
            self.chords_summary_label.format(chords=" ".join(sheet.chords)),
            style="chords-summary",
        )

    def get_lines(self, sheet):
        lines = [Paragraph(line.text.replace("\n", ""), style=self.line_styles[line.type]) for line in sheet.lines]
        n = max(len(line.text) for line in sheet.lines)
        if n < 45:
            section = Section(style="two_cols", name=f"{sheet.label} - content")
            for line in lines:
                section.append(line)
            return [section]
        return lines
