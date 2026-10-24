"""JSON cache of evaluation results, keyed by file content and scoring configuration."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

from .config import Config
from .scoring import SYSTEM_PROMPT


class ResultCache:
    def __init__(self, directory: Path | str = "ref_cache"):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True)

    @staticmethod
    def key(file_bytes: bytes, config: Config) -> str:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        return f"{file_hash}_{config.fingerprint(SYSTEM_PROMPT)}"

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def load(self, key: str) -> Optional[dict]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def save(self, key: str, data: dict) -> None:
        self._path(key).write_text(json.dumps(data, indent=2))

    def clear(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)
        self.directory.mkdir(exist_ok=True)
