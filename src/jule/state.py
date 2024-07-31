import gzip
import io
import logging
import pickle
import tarfile
import time
import typing
from typing import BinaryIO, Optional

LOGGER = logging.getLogger(__name__)

T = typing.TypeVar('T')


class SerializableBase(typing.Generic[T]):
    def save(self, f: BinaryIO) -> None:
        pickle.dump(self, f)
        f.flush()

    @staticmethod
    def load(f: BinaryIO) -> T:
        obj = pickle.load(f)
        return obj


class LdapSnapshotData(SerializableBase['LdapSnapshotData']):
    def __init__(self, entries: list[tuple[str, dict]]):
        self.entries: list[tuple[str, dict]] = entries


class LdapSnapshotMetadata(SerializableBase['LdapSnapshotMetadata']):
    def __init__(self, label=None, timestamp=None, entries_count=None, parameters=None):
        self.label: Optional[str] = label
        self.timestamp: Optional[float] = timestamp or time.time()
        self.entries_count: Optional[int] = entries_count
        self.parameters: Optional[dict] = parameters


class LdapStorageContainer:
    # 1 - fastest, 9 - smallest (speed difference is negligible in our cases
    # according to experiments)
    COMPRESS_LEVEL = 9

    def __init__(self, data: LdapSnapshotData, metadata: LdapSnapshotMetadata):
        self.data: LdapSnapshotData = data
        self.metadata: LdapSnapshotMetadata = metadata

    def save(self, f: BinaryIO) -> None:
        if self.data is None:
            raise Exception('trying to save w/o data')

        LOGGER.info('saving container...')
        with tarfile.open(mode='w', fileobj=f) as tar:
            layout = {
                'data.bin.gz': self.data,
                'metadata.bin.gz': self.metadata,
            }
            for name, obj in layout.items():
                with io.BytesIO() as buffer:
                    obj.save(buffer)
                    buffer.seek(0)
                    raw_bytes = buffer.read()
                    compressed_bytes = gzip.compress(
                        raw_bytes, compresslevel=self.COMPRESS_LEVEL)
                    with io.BytesIO(compressed_bytes) as compressed_buffer:
                        compressed_buffer_size = compressed_buffer.getbuffer().nbytes
                        tar_info = tarfile.TarInfo(name)
                        tar_info.size = compressed_buffer_size
                        tar.addfile(
                            tar_info,
                            fileobj=compressed_buffer
                        )

    @staticmethod
    def load(f: BinaryIO, load_data: bool = True) -> 'LdapStorageContainer':
        with tarfile.open(mode='r:*', fileobj=f) as tar:

            def read(name: str, type_):
                tar_file_obj = tar.extractfile(name)
                compressed_bytes = tar_file_obj.read()
                raw_bytes = gzip.decompress(compressed_bytes)
                with io.BytesIO(raw_bytes) as obj_file:
                    obj = type_.load(obj_file)
                    assert isinstance(obj, type_)
                    return obj

            metadata = read('metadata.bin.gz', LdapSnapshotMetadata)
            data = None if not load_data else read('data.bin.gz', LdapSnapshotData)
            return LdapStorageContainer(data, metadata)


def try_load(path: str, load_data: bool = False) -> Optional[LdapStorageContainer]:
    try:
        with open(path, 'rb') as f:
            return LdapStorageContainer.load(f, load_data=load_data)
    except Exception:
        return None
