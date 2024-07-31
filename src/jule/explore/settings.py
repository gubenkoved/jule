from jule.plugin import PluginBase


class AppSettings:
    def __init__(
            self, data_dir: str, cache_dir: str, export_dir: str,
            plugin: PluginBase):
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        self.export_dir = export_dir
        self.plugin = plugin
