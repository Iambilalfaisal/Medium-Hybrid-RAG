from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import pandas as pd

CSV_PATH = Path(__file__).resolve().parents[3] / "medium_data.csv"


@dataclass
class ArticleRow:
    id: str
    url: str
    title: str
    subtitle: str | None
    claps: int | None
    responses: int | None
    reading_time: float | None
    publication: str | None
    published_date: date | None


def _to_optional_int(value) -> int | None:
    return None if pd.isna(value) else int(value)


def _to_optional_float(value) -> float | None:
    return None if pd.isna(value) else float(value)


def _to_optional_str(value) -> str | None:
    return None if pd.isna(value) else str(value)


def load_rows(csv_path: Path = CSV_PATH) -> Iterator[ArticleRow]:
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        published_date = None
        if not pd.isna(row["date"]):
            published_date = datetime.strptime(str(row["date"]), "%d-%m-%Y").date()

        yield ArticleRow(
            id=str(row["id"]),
            url=str(row["url"]),
            title=str(row["title"]),
            subtitle=_to_optional_str(row.get("subtitle")),
            claps=_to_optional_int(row.get("claps")),
            responses=_to_optional_int(row.get("responses")),
            reading_time=_to_optional_float(row.get("reading_time")),
            publication=_to_optional_str(row.get("publication")),
            published_date=published_date,
        )
