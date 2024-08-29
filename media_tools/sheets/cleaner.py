from itertools import islice

from media_tools.core import logs


__all__ = ("Cleaner",)


class Cleaner:
    def __init__(self, storage):
        self.storage = storage

    def run(self):
        sheets, drop_list = {}, []

        def sk(it):
            return it.artist, it.title

        for sheet_1 in sorted(self.storage, key=sk):
            key = (sheet_1.artist, sheet_1.title)
            sheet_2 = sheets.get(key)
            if not sheet_2:
                sheets[key] = sheet_1
                continue

            self.display_conflict(sheet_1, sheet_2)
            keep, drop = self.select_action(sheet_1, sheet_2)
            if drop:
                drop_list.append(drop)

        self.run_drop(drop_list)

    def display_conflict(self, sheet_1, sheet_2):
        logs.warn(f"Sheet found twice for: {sheet_1.artist} -- {sheet_1.title}")
        logs.info(f"Sheet 1 ({sheet_1.url}):")
        self._print_lines(sheet_1)
        logs.info(f"Sheet 2 ({sheet_2.url}):")
        self._print_lines(sheet_2)

    def _print_lines(self, sheet, n=16, pad="  "):
        for line in islice(sheet.lines, 0, n):
            print(line.to_string().replace("\n", ""))

    def select_action(self, sheet_1, sheet_2):
        logs.warn("Select an action:\n" "- keep sheet 1: 1\n" "- keep sheet 2: 2\n" "- keep both: 3\n")
        action = input("default=3:")
        keep, drop = None, None
        match action:
            case "1":
                keep, drop = sheet_1, sheet_2
            case "2":
                keep, drop = sheet_2, sheet_1
            case _:
                return None, None

        keep.url = keep.url or drop.url
        return keep, drop

    def run_drop(self, drop_list):
        logs.warn(f"There are {len(drop_list)} sheets to drop")
        for sheet in drop_list:
            print(f" - {sheet.artist}: {sheet.title} ({sheet.url})")
        logs.warn("Are you sure to drop all those items?")
        if input("Please type YES if you're sure") == "YES":
            for sheet in drop_list:
                k = self.storage.get_key(sheet)
                del self.storage.items[k]
            logs.info("Items have been dropped.")
        else:
            logs.info("Do not drop: exit")
