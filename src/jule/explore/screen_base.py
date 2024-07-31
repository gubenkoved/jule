from textual.screen import Screen

from jule.cache import CacheStore
from jule.explore.settings import AppSettings
from jule.plugin import PluginBase


# TODO: how to type hint App w/o introducing a circular references?
class ScreenBase(Screen):
    @property
    def settings(self) -> AppSettings:
        return self.app.settings

    @property
    def plugin(self) -> PluginBase:
        return self.app.plugin

    @property
    def cache_store(self) -> CacheStore:
        return self.app.cache_store
