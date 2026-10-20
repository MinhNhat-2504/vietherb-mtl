#!/usr/bin/env python3
"""Fetch an auditable exploratory ChEMBL activity snapshot.

The ChEMBL REST service follows the current live release. Final paper runs must
use ``extract_chembl_sqlite.py`` with the release pinned in the study config.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_ROOT = "https://www.ebi.ac.uk/chembl/api/data/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def session() -> requests.Session:
    client = requests.Session()
    retries = Retry(
        total=6,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    client.mount("https://", HTTPAdapter(max_retries=retries))
    client.headers["User-Agent"] = "vietherb-mtl/0.1 (academic reproducibility)"
    return client


def fetch_target(
    client: requests.Session,
    target_id: str,
    standard_types: list[str],
    units: str,
    destination: Path,
    max_records: int | None,
) -> int:
    url = urljoin(API_ROOT, "activity.json")
    params = {
        "target_chembl_id": target_id,
        "standard_type__in": ",".join(standard_types),
        "standard_units": units,
        "limit": 1000,
    }
    count = 0
    part = destination.with_suffix(destination.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="\n") as output:
        while url:
            response = client.get(url, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            for record in payload.get("activities", []):
                if record.get("target_chembl_id") != target_id:
                    raise RuntimeError("ChEMBL returned a record for the wrong target")
                output.write(json.dumps(record, sort_keys=True) + "\n")
                count += 1
                if max_records is not None and count >= max_records:
                    url = None
                    break
            else:
                next_url = payload.get("page_meta", {}).get("next")
                url = urljoin(API_ROOT, next_url) if next_url else None
                params = None
            if count and count % 5000 == 0:
                print(f"{target_id}: {count:,} records", flush=True)
            time.sleep(0.05)
    part.replace(destination)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    client = session()
    metadata = {
        "kind": "exploratory_live_api_snapshot",
        "warning": "The REST API is live; use pinned SQLite for confirmatory results.",
        "requested_release": config.get("chembl_release"),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "api_root": API_ROOT,
        "config_sha256": sha256(args.config),
        "targets": {},
    }
    retrieval = config["retrieval"]
    for target in config["targets"]:
        target_id = target["id"]
        destination = args.out / f"{target_id}.jsonl"
        if destination.exists() and not args.overwrite:
            raise FileExistsError(f"{destination} exists; pass --overwrite explicitly")
        count = fetch_target(
            client,
            target_id,
            list(retrieval["standard_types"]),
            str(retrieval["standard_units"]),
            destination,
            args.max_records,
        )
        metadata["targets"][target_id] = {
            "name": target["name"],
            "records": count,
            "file": destination.name,
            "sha256": sha256(destination),
        }
        print(f"{target_id}: wrote {count:,} records to {destination}")
    manifest = args.out / "manifest.json"
    manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest}")


if __name__ == "__main__":
    main()
