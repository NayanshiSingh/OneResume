"""Private file storage for generated artifacts.

Files live outside any publicly served directory and are only reachable
through authorised API routes. Keys are built by the application, never
taken from user input.
"""

import os
import shutil
from pathlib import Path

from app.config import settings


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def path(self, key: str) -> Path:
        resolved = (self.root / key).resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Storage key escapes the storage root: {key}")
        return resolved

    def save(self, key: str, data: bytes) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)

    def delete_prefix(self, prefix: str) -> None:
        shutil.rmtree(self.path(prefix), ignore_errors=True)


def get_storage() -> LocalStorage:
    return LocalStorage(settings.STORAGE_DIR)
