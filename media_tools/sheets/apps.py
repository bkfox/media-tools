import inspect
from functools import cached_property
from pathlib import Path
from subprocess import Popen, PIPE
from urllib.parse import urlparse

from media_tools.core import App, logs


__all__ = ("SheetsApp", "apps")


class SheetsApp(App):
    name = "sheets"
    label = "Guitare Sheets"
    description = "Manage guitar sheets: download, update, merge, export."

    @cached_property
    def sources(self):
        """Source classes by host."""
        from . import sources, sheet

        items = (
            item()
            for item in vars(sources).values()
            if inspect.isclass(item) and issubclass(item, sheet.Sheet) and item.hosts
        )
        return {host: source for source in items for host in source.hosts}

    @cached_property
    def storages(self):
        """Storage classes by file extension."""
        from . import storage

        items = (
            item
            for item in vars(storage).values()
            if inspect.isclass(item) and issubclass(item, storage.Storage) and item.file_ext
        )
        return {storage.file_ext: storage for storage in items}

    def init_parser(self, parser):
        parser.add_argument("urls", nargs="*", type=str, metavar="URL")
        parser.add_argument("-l", "--list", type=Path, help="Input URL list to fetch.")
        # parser.add_argument("-c", "--clipboard", action="store_true", help="Copy to clipboard.")
        parser.add_argument("-e", "--export", type=Path, help="Export all sheets to the provided file")
        parser.add_argument("--export-tag", type=str, nargs="*", help="Only export sheets with provided tags")
        parser.add_argument("--import-legacy", type=Path, help="Import legacy LibreOffice HTML export")
        parser.add_argument(
            "--storage", "-s", type=Path, help=f"Storage file (supported: {', '.join(self.storages.keys())})"
        )
        parser.add_argument("--list-storages", action="store_true", help="List available storage formats.")
        parser.add_argument("--force-download", action="store_true", help="Force download of already existing sheets")

    def run(
        self,
        urls,
        list=None,
        clipboard=False,
        storage=None,
        force_download=False,
        list_storages=False,
        export=None,
        export_tag=None,
        **_,
    ):
        if list_storages:
            self.list_storages()
            return

        urls = self.get_urls(urls, list)

        storage = self.get_storage(storage)
        if storage and not force_download:
            urls = {url for url in urls if url not in storage}

        sheets = self.get_sheets(urls)
        if sheets:
            storage.update(sheets)
            try:
                storage.save()
            except Exception as err:
                logs.err(err)

        if export:
            self.export(export, export_tag, storage)

    def list_storages(self):
        for storage in self.storages.values():
            print(f"{storage.file_ext}: {storage.description}")

    def get_urls(self, urls, path=None):
        urls = set(urls or [])
        if path:
            with open(path) as stream:
                lines = stream.read().split("\n")
                urls = urls | {line.strip() for line in lines if line}
        return urls

    def get_sheets(self, urls):
        if not urls:
            logs.info("Nothing to download")
            return

        logs.info(f"Downloading {len(urls)} sheets...")
        sheets = []
        for url in urls:
            logs.info(f"- fetch: {url}")
            host = urlparse(url).hostname
            if source := self.sources.get(host):
                try:
                    sheet = source.from_http(url)
                    sheets.append(sheet)
                    logs.success("  done!")
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    logs.err(f"  error: {e}")
            else:
                print(f"No source for host {host} ({url}): skip.")

        return sheets

    def export(self, path, tags, source):
        storage = self.get_storage(path)
        storage.update(source.items.values())
        filter = tags and (lambda item: any(t in item.tags for t in tags))
        storage.save(filter)

    def get_storage(self, path):
        if path is None:
            return self.storages.Storage(path)

        ext = path.suffix[1:]
        if cls := self.storages.get(ext):
            return cls(path)
        raise ValueError(f"Storage file type {ext} not supported")

    def to_clipboard(self, mime, text):
        process = Popen(["xclip", "-t", mime, "-selection", "clipboard"], stdin=PIPE)
        process.communicate(text.encode("utf8"))
        process.kill()


apps = SheetsApp()
