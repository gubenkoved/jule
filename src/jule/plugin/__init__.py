import os

from .base import (
    PluginBase,
    PluginError,
    ExtractorBase,
    LdapQuery,
    LdapQuerySet,
    ScreenQuery,
    load_from_module,
)


def get_default_plugin_class_name():
    return os.environ.get('JULE_PLUGIN_CLASS') or 'jule.plugin.sample'
