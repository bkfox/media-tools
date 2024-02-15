from ..tabs_interleaved import InterleavedXMLTabs


__all__ = ("BACTabs",)


class BACTabs(InterleavedXMLTabs):
    hosts = ["boiteachansons.net", "www.boiteachansons.net"]

    artist_xpath = """.//div[@id="dTitreNomArtiste"]//h2"""
    title_xpath = """.//div[@class="dTitrePartition"]/h1"""
    lines_xpath = """.//div[@class="pLgn"]"""

    chord_tag = "span"
    chord_class = "interl"
    chord_text_xpath = """span[@class="a"]"""
    chord_text_attr = "data-accord"
