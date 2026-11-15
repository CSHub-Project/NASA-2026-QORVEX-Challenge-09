from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "outputs" / "figures"


@dataclass(frozen=True)
class Region:
    id: str
    name_en: str
    name_fa: str
    bbox: tuple[float, float, float, float]
    purpose: str

    @property
    def firms_bbox(self) -> str:
        return ",".join(str(value) for value in self.bbox)


def load_regions(config_path: Path | None = None) -> list[Region]:
    path = config_path or ROOT / "configs" / "regions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Region(**{**item, "bbox": tuple(item["bbox"])}) for item in payload]


def ensure_directories() -> None:
    for path in (DATA_RAW, DATA_PROCESSED, FIGURES):
        path.mkdir(parents=True, exist_ok=True)

