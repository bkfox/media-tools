from pathlib import Path
from subprocess import Popen, PIPE
from urllib.parse import urlparse

from media_tools.core import App
from . import sources, renderers


__all__ = ("TabsApp", "apps")


class TabsApp(App):
    name = "tabs"
    label = "Guitare parts"
    description = (
        "Fetch and handle guitar parts from provided list of URL and output "
        "aggregated result (to file if provided, clipboard, or stdout)."
    )
    
    def init_parser(self, parser):
        parser.add_argument("urls", nargs="*", type=str, metavar="URL")
        parser.add_argument("-l", "--list", type=Path, help="Input URL list to fetch.")
        parser.add_argument("-c", "--clipboard", action="store_true", help="Copy to clipboard.")
        parser.add_argument("-o", "--output", type=Path, help="Output result to file.")
        parser.add_argument("--rtf", action="store_true", help="Output to RTF format (following LibreOffice convention)")

    def run(self, urls, list=None, clipboard=False, output=None, rtf=False, **_):
        if list:
            with open(list) as f:
                lines = f.read().split("\n")
                urls.extend(l.strip() for l in lines if l)

        tabs_list = self.get_tabs_list(urls)
        renderer = self.get_renderer(rtf=rtf)
        text = renderer.render(tabs_list)

        if output:
            with open(output, "w+") as f:
                f.write(text)
        if clipboard:
            self.to_clipboard(renderer.mime_type, text)
        if not output and not clipboard:
            print("-" * 80)
            print(text)
            print("-" * 80)

    def get_tabs_list(self, urls):
        self.logs.info("Downloading tabs...")
        tabs_list = []
        for url in urls:
            self.logs.info(f"- fetch: {url}")
            host = urlparse(url).hostname
            cl = sources.by_host[host]

            try:
                tabs = cl.from_http(url)
                tabs_list.append(tabs)
                self.logs.success("  done!")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.logs.error(f"  error: {e}")
        return tabs_list

    def get_renderer(self, rtf=False):
        if rtf:
            return renderers.RTFRenderer()
        return renderers.Renderer()
    
    def to_clipboard(self, mime, text):
        process = Popen(["xclip", "-t", mime, "-selection", "clipboard"], stdin=PIPE)
        process.communicate(text.encode("utf8"))
        process.kill()


apps = TabsApp()

