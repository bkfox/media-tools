from datetime import datetime
import inspect
from functools import cached_property
from pathlib import Path
from subprocess import Popen, PIPE
from urllib.parse import urlparse

from media_tools.core import App, logs


__all__ = ("SheetsApp", "apps")


def as_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date


class SheetsApp(App):
    name = "sheets"
    label = "Guitare Sheets"
    description = "Manage guitar sheets: download, update, merge, export."

    @cached_property
    def sources(self):
        """Source classes by host."""
        from . import sources

        items = (
            item()
            for item in vars(sources).values()
            if inspect.isclass(item) and issubclass(item, sources.Source) and item.hosts
        )
        return {host: source for source in items for host in source.hosts}

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
        parser.add_argument("--list-metadata", action="store_true", help="List all metadata fetched from storages.")
        parser.add_argument("--clean-up", action="store_true", help="Clean up doubled sheets")

        group = parser.add_argument_group("Download")
        group.add_argument("-l", "--download-list", type=Path, help="Input URL file list to download.")
        group.add_argument("-d", "--download", type=str, action="append", help="Download provided urls")
        group.add_argument("--force-download", action="store_true", help="Force download of already existing sheets")

        group = parser.add_argument_group("Sheets")
        group.add_argument("--after", type=as_date, help="Select sheets added after this date (as 'yyyy-mm-dd')")
        group.add_argument("--before", type=as_date, help="Select sheets added before this date (as 'yyyy-mm-dd')")
        group.add_argument("--artist", type=str, action="append", help="Select sheets with provided artists")
        group.add_argument("-t", "--tag", type=str, action="append", help="Select sheets with provided tags")
        group.add_argument("--overwrite", action="store_true", help="Overwrite existing output file.")
        group.add_argument("--merge", action="store_true", help="Merge new values with existing ones of output.")

    def run(
        self,
        storages,
        list_storages=False,
        list_metadata=False,
        clean_up=False,
        download=None,
        download_list=None,
        force_download=False,
        output=None,
        merge=False,
        overwrite=False,
        artist=None,
        tag=None,
        before=None,
        after=None,
        **kwargs,
    ):
        if list_storages:
            self.list_storages()
            return

        output = self.get_storage(output, storages, merge)
        if list_metadata:
            self.list_metadata(output)
            return

        urls = self.get_urls(download, download_list, not force_download and output)
        if urls:
            sheets = self.download(urls)
            if sheets:
                output.update(sheets)

        if clean_up:
            self.clean_up(output)

        self.save(output, overwrite, artists=artist, tags=tag, before=before, after=after)

    def list_storages(self):
        """List available storage types (print to stdou)"""
        for storage in self.storages.values():
            print(f"{storage.file_ext}: {storage.description}")

    def list_metadata(self, storage):
        if not len(storage):
            logs.warn("No metadata to display.")
            return

        metadatas = {}
        for item in storage:
            metadatas.setdefault("artists", set()).add(item.artist)
            metadatas.setdefault("tags", set()).update(item.tags)
            metadatas.setdefault("version", set()).add(item.version)
            metadatas.setdefault("sheets", set()).add(f"{item.artist} -- {item.title}")

        for key, values in metadatas.items():
            print(f"{key}:")
            for val in sorted(values):
                val and print(f"  - {val}")

    def clean_up(self, storage):
        from .cleaner import Cleaner

        Cleaner(storage).run()

    def get_storage(self, path, inputs, merge=False):
        from .storage import get_storage

        merge = merge or not inputs
        output = get_storage(path, load=merge)
        if merge:
            logs.info(f"Output loaded with {len(output)} sheets.")

        for path in inputs:
            logs.info(f"Load storage {path}")
            output.load(path)

        logs.info(f"{len(output)} sheets have been loaded.")
        return output

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

    def save(self, storage, overwrite=False, **filters):
        if not overwrite and storage.path.exists():
            confirm = input(f"Overwrite file ({storage.path}) [N/y]? ")
            if not confirm or confirm not in "Yy":
                logs.warn("Don't write over existing file: exit.")
                return False

        filter = self.get_filter(**filters)
        storage.save(filter)
        return True

    _tag_expr = "any(t in item.tags for t in tags)"
    _artist_expr = "item.artist.lower() in artists"
    _before_expr = "item.version < before"
    _after_expr = "item.version > after"

    def get_filter(self, artists=None, tags=None, before=None, after=None, **_):
        expr = []
        if artists:
            expr.append(self._artist_expr)
        if tags:
            expr.append(self._tag_expr)
        if before:
            expr.append(self._before_expr)
        if after:
            expr.append(self._after_expr)
        if not expr:
            return None

        expr = " and ".join(expr)
        return eval(
            f"lambda item: {expr}",
            {"artists": {a.lower() for a in artists}, "tags": tags, "before": before, "after": after},
        )

    def to_clipboard(self, mime, text):
        process = Popen(["xclip", "-t", mime, "-selection", "clipboard"], stdin=PIPE)
        process.communicate(text.encode("utf8"))
        process.kill()


apps = SheetsApp()
