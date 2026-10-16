"""Durable objects in a local directory or GCS; no credentials in configuration."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import urlparse

import pyarrow as pa
import pyarrow.parquet as pq


class BronzeStore:
    def __init__(self, uri):
        if not uri.strip():
            raise ValueError("BRONZE_URI cannot be empty.")
        parsed = urlparse(uri)
        if parsed.scheme == "gs":
            if not parsed.netloc:
                raise ValueError("A GCS bucket is required.")
            from google.cloud import storage
            self.bucket = storage.Client().bucket(parsed.netloc)
            self.prefix = parsed.path.strip("/")
            self.root = None
        elif parsed.scheme:
            raise ValueError("BRONZE_URI must be a directory or gs:// URI.")
        else:
            self.root = Path(uri)
            self.bucket = None
            self.prefix = ""

    def _key(self, key):
        path = PurePosixPath(key)
        if path.is_absolute() or ".." in path.parts or "\\" in key:
            raise ValueError("Object keys must be relative and cannot contain '..'.")
        return "/".join(part for part in (self.prefix, str(path)) if part)

    def read_checkpoint(self, key):
        key = self._key(key)
        if self.bucket:
            from google.api_core.exceptions import NotFound
            blob = self.bucket.blob(key)
            try:
                blob.reload(timeout=30)
                generation = int(blob.generation)
                content = blob.download_as_bytes(if_generation_match=generation, timeout=30)
                return json.loads(content), generation
            except NotFound:
                return None, 0
        path = self.root / key
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None, None
        return json.loads(content), hashlib.sha256(content).hexdigest()

    def put_bytes(self, key, content, content_type, generation=0):
        key = self._key(key)
        if self.bucket:
            blob = self.bucket.blob(key)
            blob.upload_from_string(
                content, content_type=content_type,
                if_generation_match=generation, timeout=60,
            )
            return int(blob.generation)
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            if generation == 0:
                os.link(temporary, path)  # Publish the complete object without overwriting.
            else:
                os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return hashlib.sha256(content).hexdigest()

    def put_checkpoint(self, key, document, generation):
        if not self.bucket:
            _, current = self.read_checkpoint(key)
            if current != generation:
                raise RuntimeError("Checkpoint changed; stop concurrent extractors.")
        return self.put_bytes(
            key, (json.dumps(document, sort_keys=True) + "\n").encode(),
            "application/json", generation=generation if self.bucket else None,
        )

    def put_parquet(self, key, rows, schema):
        output = pa.BufferOutputStream()
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), output, compression="snappy")
        self.put_bytes(key, output.getvalue().to_pybytes(), "application/octet-stream")
