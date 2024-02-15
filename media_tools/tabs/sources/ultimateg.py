import re

from ..tabs import Line, ReactTabs


class UltimateGTabs(ReactTabs):
    hosts = [
        "tabs.ultimate-guitar.com",
        "ultimate-guitar.com",
    ]

    js_store_xpath = ".//div[@class='js-store']"
    tab_rg = re.compile(r"\[tab\](?P<tab>.*?)\[/tab\]")
    chord_rg = re.compile(r"\[chord\](?P<chord>.*?)\[/chord\]")

    def parse(self, *args, **kwargs):
        data = super().parse(*args, **kwargs)
        return data['store']['page']['data']

    def get_artist(self, data, **_):
        return data['tab']['artist_name']

    def get_title(self, data, **_):
        return data['tab']['song_name']

    _clean_up = ["[tab]", "[/tab]"]

    def get_lines(self, data, **_):
        part = data['tab_view']['wiki_tab']['content']
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



# tabs = UltimateGTabs.from_http("https://tabs.ultimate-guitar.com/tab/3649919")
# gtabs = UltimateGTabs.from_http("https://tabs.ultimate-guitar.com/tab/2692788")


