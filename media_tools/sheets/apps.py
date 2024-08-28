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
        parser.add_argument(
            "storages",
            nargs="*",
            type=Path,
            metavar="INPUT",
            help="Load those sheet files. If no `--output` is specified, use the last declared one as output.",
        )
        parser.add_argument("output", type=Path, metavar="OUTPUT", help="Save results into this file.")

        parser.add_argument("--list-storages", action="store_true", help="List available storage formats.")

        group = parser.add_argument_group("Download")
        group.add_argument("-l", "--download-list", type=Path, help="Input URL file list to download.")
        group.add_argument("-d", "--download", type=str, nargs="*", help="Download provided urls")
        group.add_argument("--force-download", action="store_true", help="Force download of already existing sheets")

        group = parser.add_argument_group("Sheets")
        group.add_argument("-t", "--tag", type=str, nargs="*", help="Select sheets with provided tags")
        group.add_argument("--overwrite", action="store_true", help="Overwrite existing output file.")
        group.add_argument("--merge", action="store_true", help="Merge new values with existing ones of output.")

    def run(
        self,
        storages,
        list_storages=False,
        download=None,
        download_list=None,
        force_download=False,
        output=None,
        tag=None,
        overwrite=False,
        merge=False,
        **_,
    ):
        if list_storages:
            self.list_storages()
            return

        storage = self.load_storages(storages)
        logs.info(f"{len(storage)} sheets have been loaded.")

        if output:
            output = self.get_storage(output, load=merge)
            merge and logs.info(f"Output loaded with {len(output)} sheets")
            output.update(storage)

        urls = self.get_urls(download, download_list, not force_download and output)
        if urls:
            sheets = self.download(urls)
            if sheets:
                output.update(sheets)
        self.save(output, tag, overwrite=overwrite)

    def list_storages(self):
        """List available storage types (print to stdou)"""
        for storage in self.storages.values():
            print(f"{storage.file_ext}: {storage.description}")

    def load_storages(self, paths, **kwargs):
        """Load storages from provided paths iterable, returning last one
        updated with all loaded sheets."""
        kwargs["load"] = True
        last = None
        for path in paths:
            storage = self.get_storage(path, **kwargs)
            if last:
                storage.update(last)
            last = storage
        return last

    def get_storage(self, path, **kwargs):
        """Get Storage instance for the provided ``path``."""
        if path is None:
            return self.storages.Storage(path, **kwargs)

        ext = path.suffix[1:]
        if cls := self.storages.get(ext):
            return cls(path, **kwargs)
        raise ValueError(f"Storage file type {ext} not supported")

    def get_urls(self, urls, path=None, storage=None):
        """Return url list from provided urls and list-file, excluding thoses
        matching sheets of provided storage."""
        urls = set(urls or [])
        if path:
            with open(path) as stream:
                lines = stream.read().split("\n")
                urls = urls | {line.strip() for line in lines if line}

        if storage:
            urls = {url for url in urls if url not in storage}
        return urls

    def download(self, urls):
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

    def save(self, storage, tags, overwrite=False):
        if not overwrite and storage.path.exists():
            confirm = input(f"Overwrite file ({storage.path}) [N/y]? ")
            if not confirm or confirm not in "Yy":
                logs.warn("Don't write over existing file: exit.")
                return False

        filter = tags and (lambda item: any(t in item.tags for t in tags))
        storage.save(filter)
        return True

    def to_clipboard(self, mime, text):
        process = Popen(["xclip", "-t", mime, "-selection", "clipboard"], stdin=PIPE)
        process.communicate(text.encode("utf8"))
        process.kill()


apps = SheetsApp()
