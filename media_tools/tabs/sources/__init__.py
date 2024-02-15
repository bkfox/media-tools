from .boiteachansons import BACTabs
from .ultimateg import UltimateGTabs


__all__ = ("BACTabs", "UltimateGTabs")


sources = [BACTabs, UltimateGTabs]
by_host = {}

for source in sources:
    by_host.update((host, source) for host in source.hosts)
