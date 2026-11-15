"""Download one NASA fire/geolocation swath pair using Earthdata Login.

Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD in the process environment.
Credentials and authentication cookies are kept in memory only.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import os
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

from pipeline.common import ROOT


RANGE_SIZE = 8 * 1024 * 1024


def download_ranges(
    signed_url: str,
    target: Path,
    total: int,
    *,
    range_size: int = RANGE_SIZE,
    max_workers: int = 6,
) -> None:
    """Fetch a large CloudFront object in checked byte ranges."""
    if total <= 0 or range_size <= 0 or max_workers <= 0:
        raise ValueError("total, range_size and max_workers must be positive")
    with target.open("wb") as output:
        output.truncate(total)

    def fetch(start: int) -> None:
        end = min(start + range_size, total) - 1
        response = requests.get(signed_url, headers={"Range": f"bytes={start}-{end}"},
                                timeout=(15, 90))
        response.raise_for_status()
        if response.status_code != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{total}":
            raise RuntimeError(f"Invalid range response for bytes {start}-{end}")
        if len(response.content) != end - start + 1:
            raise RuntimeError(f"Incomplete range response for bytes {start}-{end}")
        with target.open("r+b") as output:
            output.seek(start)
            output.write(response.content)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(fetch, range(0, total, range_size)))


class EarthdataSession(requests.Session):
    """Preserve Basic authorization only across NASA Earthdata redirects."""

    def rebuild_auth(self, prepared_request: requests.PreparedRequest,
                     response: requests.Response) -> None:
        old_host = urlparse(response.request.url).hostname
        new_host = urlparse(prepared_request.url).hostname
        if old_host != new_host and "urs.earthdata.nasa.gov" not in {old_host, new_host}:
            prepared_request.headers.pop("Authorization", None)


def download_pair(inventory: Path, product: str, acquisition_key: str) -> pd.DataFrame:
    username = os.environ.get("EARTHDATA_USERNAME")
    password = os.environ.get("EARTHDATA_PASSWORD")
    if not username or not password:
        raise ValueError("Set Earthdata credentials in the process environment")
    paired = {"VNP14IMG": "VNP03IMG", "MYD14": "MYD03"}
    if product not in paired:
        raise ValueError(f"Unsupported fire product: {product}")
    source = pd.read_csv(inventory, dtype={"acquisition_key": str})
    selected = source.loc[
        source["product"].isin([product, paired[product]])
        & (source["acquisition_key"] == acquisition_key)
    ].copy()
    selected["download_order"] = (selected["product"] != product).astype(int)
    selected = selected.sort_values("download_order")
    if len(selected) != 2:
        raise ValueError("Expected exactly one matched fire and geolocation granule")
    session = EarthdataSession()
    session.auth = (username, password)
    target_dir = ROOT / "data" / "raw" / "swaths" / acquisition_key
    target_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for row in selected.itertuples(index=False):
        url = str(row.data_url)
        if not url.startswith((
            "https://data.laadsdaac.earthdatacloud.nasa.gov/",
            "https://data.lpdaac.earthdatacloud.nasa.gov/",
        )):
            raise ValueError("Unexpected download host")
        target = target_dir / Path(url).name
        if not target.exists():
            temporary = target.with_suffix(target.suffix + ".part")
            try:
                with session.get(url, timeout=(15, 45), stream=True) as response, temporary.open("wb") as output:
                    response.raise_for_status()
                    if urlparse(response.url).hostname == "urs.earthdata.nasa.gov":
                        raise RuntimeError("Earthdata Login did not authorize the data download")
                    size = int(response.headers.get("Content-Length", 0))
                    if size > 50 * 1024 * 1024:
                        output.close()
                        download_ranges(response.url, temporary, size)
                    else:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            output.write(chunk)
                if target.suffix == ".nc" and temporary.open("rb").read(8) != b"\x89HDF\r\n\x1a\n":
                    raise RuntimeError("Download is not an HDF5/NetCDF4 granule")
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        digest = sha256()
        with target.open("rb") as input_file:
            while chunk := input_file.read(1024 * 1024):
                digest.update(chunk)
        records.append({
            "product": row.product, "acquisition_key": acquisition_key,
            "file_name": target.name, "bytes": target.stat().st_size,
            "sha256": digest.hexdigest(),
        })
        print(f"Verified {row.product}: {target.stat().st_size:,} bytes")
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=ROOT / "outputs" / "tables"
                        / "day8_swath_inventory_2023-08-06.csv")
    parser.add_argument("--product", default="VNP14IMG")
    parser.add_argument("--acquisition-key", default="2023218.1330")
    args = parser.parse_args()
    manifest = download_pair(args.inventory, args.product, args.acquisition_key)
    target = ROOT / "outputs" / "tables" / f"day8_swath_checksums_{args.acquisition_key}.csv"
    manifest.to_csv(target, index=False)
    print(f"Saved reproducibility manifest: {target}")


if __name__ == "__main__":
    main()
