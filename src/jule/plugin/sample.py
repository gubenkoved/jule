from jule.common import load_text_attr
from jule.plugin import PluginBase, LdapQuerySet, LdapQuery, ExtractorBase


class SampleExtractor(ExtractorBase):
    def get_all_property_names(self) -> list[str]:
        return [
            'dn',
            'full_name',
            'manager_name',
            'title',
            'department',
        ]

    def extract(self, dn: str, prop: str):
        entry = self.entry_by_dn[dn]
        if prop == 'dn':
            return dn
        elif prop == 'full_name':
            return load_text_attr(entry, 'displayName')
        elif prop == 'manager_name':
            manager_dn = load_text_attr(entry, 'manager')
            if manager_dn in self.entry_by_dn:
                manager_entry = self.entry_by_dn[manager_dn]
                return load_text_attr(manager_entry, 'displayName')
            else:
                return None
        elif prop == 'title':
            return load_text_attr(entry, 'title')
        elif prop == 'department':
            return load_text_attr(entry, 'department')
        else:
            raise ValueError('Property {} not supported'.format(prop))


class SamplePlugin(PluginBase):
    @property
    def property_extractor_class(self) -> type[ExtractorBase]:
        return SampleExtractor

    @property
    def ldap_query_sets(self) -> list[LdapQuerySet]:
        return [
            LdapQuerySet('sample', [
                LdapQuery('OU=Users,DC=example,DC=org', None),
            ], None)
        ]

    @property
    def version(self):
        return '1.0.0'


PLUGIN_CLASS = SamplePlugin
