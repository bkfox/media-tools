from pathlib import Path

from media_tools.core import action, Apps


__all__ = ("apps", "PlaylistApp")


class PlaylistApp(Apps):
    name = "playlist"
    label = "Playlist"
    groups = ("library", "music")
    description = (
        "This tool provide utilities for M3U playlists."
    )

    def run(self, files, merge, unique=False, **kwargs):
        originals = files.copy()
        if merge:
            # when merging, only merged file is updated
            files = {merge: self.merge(files.values())}

        if unique:
            for source, playlist in files.items():
                items = self.remove_duplicates(playlist)
                if items != playlist:
                    files[source] = items

        self.save(files, originals)

    @action("merge", "-m", type=Path,
        help="Merge provided source into this file output.")
    def merge(self, playlists):
        """ Return a list from contatenated playlists iterable. """
        return list(itertools.chain(*playlists))

    @action("unique", "-u", action="store_true",
        help="Remove duplicate tracks inside the playlist.")
    def unique(self, playlist):
        """ Remove duplicate tracks from the provided list """
        return list(set(playlist))

    def read_file(self, file):
        return file.read().split("\n")

    def write_file(self, file, value):
        file.write("\n".join(l for l in value))


apps = PlaylistApp()
