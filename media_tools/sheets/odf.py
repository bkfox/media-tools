from odfdo import Element, Document, Header, Paragraph, PageBreak, Section, Style

from .sheet import Line

__all__ = ("OdfRenderer",)


# (code, automatic)
styles_xml = [
    # Two columns section
    (
        """
    <style:style style:name="TwoColumns" style:family="section">
        <style:section-properties text:dont-balance-text-columns="true" style:editable="false">
            <style:columns fo:column-count="2" fo:column-gap="0.4cm"/>
        </style:section-properties>
    </style:style>
    """,
        True,
    ),
    # Master Page Style
    (
        """
    <style:master-page style:name="Standard" style:page-layout-name="mpm1" draw:style-name="page-footer">
        <style:footer>
            <text:p text:style-name="page-footer">
                <text:chapter text:display="name" text:outline-level="2"/>
            </text:p>
        </style:footer>
    </style:master-page>
    """,
        False,
    ),
    # Page layout
    (
        """
    <style:page-layout style:name="mpm1">
        <style:page-layout-properties fo:page-width="21.001cm" fo:page-height="29.7cm" style:num-format="1"
        style:print-orientation="portrait" fo:margin-top="1.5cm" fo:margin-bottom="1.1cm" fo:margin-left="1.5cm"
        fo:margin-right="1.5cm" style:writing-mode="lr-tb" style:layout-grid-color="#c0c0c0"
                style:layout-grid-lines="44"
                style:layout-grid-base-height="0.55cm"
                style:layout-grid-ruby-height="0cm"
                style:layout-grid-mode="none"
                style:layout-grid-ruby-below="false"
                style:layout-grid-print="true"
                style:layout-grid-display="true"
                style:layout-grid-base-width="0.37cm"
                style:layout-grid-snap-to="true"
                style:footnote-max-height="0cm"
                loext:margin-gutter="0cm">
            <style:footnote-sep style:width="0.018cm" style:distance-before-sep="0.101cm"
            style:distance-after-sep="0.101cm" style:line-style="solid"
            style:adjustment="left" style:rel-width="25%" style:color="#000000"/>
        </style:page-layout-properties>
        <style:header-style/>
        <style:footer-style>
            <style:header-footer-properties fo:min-height="0cm" fo:margin-left="0cm" fo:margin-right="0cm"
            fo:margin-top="0.499cm" fo:background-color="transparent" draw:fill="none" draw:fill-color="#729fcf"/>
        </style:footer-style>
    </style:page-layout>
    """,
        False,
    ),
]


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
            "family": "paragraph",
            "name": "Heading 2",
            "parent_style": "Heading",
            "text-props": {
                "fo:font-weight": "bold",
                "fo:font-size": "16pt",
            },
        },
        {
            "family": "paragraph",
            "name": "page-footer",
            "parent_style": "Footer",
            "props": {
                "fo:text-align": "center",
                "style:justify-single-word": "false",
            },
        },
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

        for style, auto in self.get_styles():
            document.insert_style(style, automatic=auto)

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
            styles.append((self.get_style(style), False))

        for xml, auto in styles_xml:
            style = Element.from_tag(xml)
            styles.append((style, auto))

        return styles

    def get_style(self, style):
        props = style.pop("props", None)
        text_props = style.pop("text-props", None)

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

        header = Header(
            self.heading_level,
            self.heading_sep.join(h for h in (artist, sheet.title) if h),
            suppress_numbering=True,
            restart_numbering=True,
        )
        header.set_attribute("text:is-list-header", "true")
        return header

    def get_chords(self, sheet):
        return Paragraph(
            self.chords_summary_label.format(chords=" ".join(sheet.chords)),
            style="chords-summary",
        )

    def get_lines(self, sheet):
        lines = [Paragraph(line.text.replace("\n", ""), style=self.line_styles[line.type]) for line in sheet.lines]
        n = max(len(line.text) for line in sheet.lines)
        if n < 45:
            section = Section(style="TwoColumns", name=f"{sheet.label} - content")
            for line in lines:
                section.append(line)
            return [section]
        return lines
