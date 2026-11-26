"""File storage: Supabase Storage in production, a local folder in development and tests.

Buckets (docs/backend-schema.md): report-images (public), fixed-photos (public),
survey-uploads (private).
"""

from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import get_settings

REPORT_IMAGES = "report-images"
FIXED_PHOTOS = "fixed-photos"
SURVEY_UPLOADS = "survey-uploads"


class Storage(Protocol):
    def upload(self, bucket: str, path: str, data: bytes, content_type: str) -> None: ...
    def download(self, bucket: str, path: str) -> bytes: ...
    def delete(self, bucket: str, paths: list[str]) -> None: ...
    def public_url(self, bucket: str, path: str) -> str: ...


class SupabaseStorage:
    def __init__(self, url: str, service_key: str) -> None:
        self.base = url.rstrip("/") + "/storage/v1"
        self.headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}

    def upload(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        r = httpx.post(
            f"{self.base}/object/{bucket}/{path}",
            content=data,
            headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"},
            timeout=60,
        )
        r.raise_for_status()

    def download(self, bucket: str, path: str) -> bytes:
        r = httpx.get(f"{self.base}/object/{bucket}/{path}", headers=self.headers, timeout=120)
        r.raise_for_status()
        return r.content

    def delete(self, bucket: str, paths: list[str]) -> None:
        r = httpx.request(
            "DELETE",
            f"{self.base}/object/{bucket}",
            json={"prefixes": paths},
            headers=self.headers,
            timeout=30,
        )
        r.raise_for_status()

    def public_url(self, bucket: str, path: str) -> str:
        return f"{self.base}/object/public/{bucket}/{path}"


class LocalStorage:
    """Writes under a folder; served by the API at /local-storage (development only)."""

    def __init__(self, root: Path, base_url: str = "http://localhost:8000/local-storage") -> None:
        self.root = root
        self.base_url = base_url.rstrip("/")

    def _file(self, bucket: str, path: str) -> Path:
        f = (self.root / bucket / path).resolve()
        if self.root.resolve() not in f.parents:
            raise ValueError("path escapes storage root")
        return f

    def upload(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        f = self._file(bucket, path)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)

    def download(self, bucket: str, path: str) -> bytes:
        return self._file(bucket, path).read_bytes()

    def delete(self, bucket: str, paths: list[str]) -> None:
        for p in paths:
            self._file(bucket, p).unlink(missing_ok=True)

    def public_url(self, bucket: str, path: str) -> str:
        return f"{self.base_url}/{bucket}/{path}"


LOCAL_ROOT = Path(__file__).resolve().parents[2] / ".local_storage"


def make_storage() -> Storage:
    s = get_settings()
    if s.supabase_url and s.supabase_service_key:
        return SupabaseStorage(s.supabase_url, s.supabase_service_key)
    return LocalStorage(LOCAL_ROOT, s.public_api_url.rstrip("/") + "/local-storage")
