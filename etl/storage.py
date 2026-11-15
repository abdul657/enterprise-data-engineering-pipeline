from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID


def write_json(directory: Path, filename: str, payload: Any) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    destination.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return destination


def copy_source_file(source: Path, destination_dir: Path, filename: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / filename
    shutil.copy2(source, destination)
    return destination


def upload_to_s3(paths: list[Path], bucket: str, region: str, run_id: UUID) -> list[str]:
    """Upload pipeline artifacts using boto3's standard AWS credential provider chain."""
    if not bucket:
        return []
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Install boto3 to enable AWS S3 archival") from error

    client = boto3.client("s3", region_name=region)
    uploaded: list[str] = []
    for path in paths:
        key = f"enterprise-etl/{run_id}/{path.name}"
        client.upload_file(str(path), bucket, key)
        uploaded.append(f"s3://{bucket}/{key}")
    return uploaded
