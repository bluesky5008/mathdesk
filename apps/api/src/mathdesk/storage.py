"""파일 저장 어댑터(DES-10).

파일 자체는 DB에 넣지 않는다. DB에는 `stored_file` 메타데이터만 두고 바이트는 여기로 보낸다.
Phase A는 로컬 파일시스템이고 Phase B는 오브젝트 스토리지로 구현만 갈아끼운다(NFR-08).
"""
import os
from pathlib import Path
from typing import Protocol


class StorageAdapter(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes | None: ...
    def delete(self, key: str) -> None: ...
    def url(self, key: str) -> str: ...


class LocalStorage:
    """루트 아래에 키 경로 그대로 저장한다."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # 신뢰 경계다. 키가 업로드 파일명에서 오면 `../`로 루트를 벗어날 수 있다.
        if path != self.root and self.root not in path.parents:
            raise ValueError("저장 경로가 루트를 벗어납니다.")
        return path

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def url(self, key: str) -> str:
        """Phase A는 같은 오리진에서 세션으로 인가하므로 앱 경로를 그대로 준다.
        서명 URL이 필요한 것은 앱 밖에서 직접 받아 가는 Phase B다(DES-10)."""
        return f"/api/files/{key}"


def storage() -> StorageAdapter:
    return LocalStorage(os.environ.get("MATHDESK_STORAGE_ROOT", "var/files"))
