import abc
import logging
import typing
import importlib

from jule.state import LdapSnapshotData

LOGGER = logging.getLogger(__name__)


LdapQuery = typing.NamedTuple('LdapQuery', [
    ('root_dn', str),
    ('filter', str | None),
])


LdapQuerySet = typing.NamedTuple('LdapQuerySet', [
    ('label', str),
    ('queries', list[LdapQuery]),
    ('attributes', list[str] | None),
])


ScreenQuery = typing.NamedTuple('ScreenQuery', [
    ('label', str),
    ('query_sql', str),
])


class ExtractorBase(abc.ABC):
    def __init__(self, snapshot: LdapSnapshotData):
        self.snapshot = snapshot
        self.entry_by_dn = {
            entry_dn: entry for entry_dn, entry
            in snapshot.entries
        }

    def extract_all(self, dn: str, skip_missing=False):
        properties = self.get_all_property_names()
        data = {}
        for prop_name in properties:
            prop_value = self.extract(dn, prop_name)
            if prop_value is None and skip_missing:
                continue
            data[prop_name] = prop_value
        return data

    @abc.abstractmethod
    def get_all_property_names(self) -> list[str]:
        pass

    @abc.abstractmethod
    def extract(self, dn: str, prop: str):
        pass


class PluginError(Exception):
    pass


class PluginBase(abc.ABC):
    @property
    @abc.abstractmethod
    def ldap_query_sets(self) -> list[LdapQuerySet]:
        pass

    @property
    @abc.abstractmethod
    def property_extractor_class(self) -> type[ExtractorBase]:
        pass

    @property
    def snapshot_screen_queries(self) -> list[ScreenQuery]:
        return [
            ScreenQuery('LIGHT', 'select dn, full_name, title, department from entries'),
            ScreenQuery('ALL', 'select * from entries'),
        ]

    @property
    def changes_screen_queries(self) -> list[ScreenQuery]:
        return [
            ScreenQuery('LIGHT', 'select dn, full_name, updated_props from changes'),
            ScreenQuery('ALL', 'select * from changes'),
        ]

    @property
    def timeline_screen_queries(self) -> list[ScreenQuery]:
        return [
            ScreenQuery('ALL', 'select * from entries')
        ]

    @property
    @abc.abstractmethod
    def version(self):
        raise NotImplementedError


def load_from_module(module_name: str) -> PluginBase:
    LOGGER.info('loading plugin from module "%s"...', module_name)
    plugin_module = importlib.import_module(module_name)
    klass = plugin_module.PLUGIN_CLASS
    plugin = klass()
    if not isinstance(plugin, PluginBase):
        raise PluginError('Unexpected base class')
    return plugin
