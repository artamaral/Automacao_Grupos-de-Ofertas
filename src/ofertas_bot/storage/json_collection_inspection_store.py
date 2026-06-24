from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CollectionInspectionStoreWriteError(OSError):
    """Raised when local inspection storage cannot write data."""


class JsonCollectionInspectionStore:
    """Optional local JSON storage for collection inspection artifacts."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, payload: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write collection inspection JSON to {self.path}"
            raise CollectionInspectionStoreWriteError(msg) from error
