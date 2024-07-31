import gzip
import hashlib
import logging
import os.path
import pickle
from typing import Dict, Any

LOGGER = logging.getLogger(__name__)


def calculate_hash(properties: Dict[str, str]) -> str:
    hasher = hashlib.sha256()
    for key in sorted(properties):
        val = properties[key]
        hasher.update(b'KEY')
        hasher.update(key.encode('utf8'))
        hasher.update(b'VAL')
        hasher.update(val.encode('utf8'))
    return hasher.digest().hex()


class CacheStore:
    def __init__(self, dir_path: str):
        self.dir_path: str = dir_path

    def get_path(self, cache_key: str):
        return os.path.join(self.dir_path, cache_key)

    def get(self, cache_key: str) -> Any:
        path = self.get_path(cache_key)

        if not os.path.exists(path):
            return None

        try:
            with gzip.GzipFile(path, 'rb') as f:
                obj = pickle.load(f)
                return obj
        except Exception as err:
            LOGGER.warning('Cache file "%s" looks corrupted: %s', path, err)
            return None

    def set(self, cache_key: str, value: Any):
        path = self.get_path(cache_key)

        with gzip.GzipFile(path, 'wb') as f:
            pickle.dump(value, f)
