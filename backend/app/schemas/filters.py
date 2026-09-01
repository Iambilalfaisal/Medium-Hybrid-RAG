from datetime import date

from pydantic import BaseModel


class FilterParams(BaseModel):
    claps_min: int | None = None
    claps_max: int | None = None
    publication: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None
    reading_time_min: float | None = None
    reading_time_max: float | None = None

    def is_empty(self) -> bool:
        return not any(self.model_dump().values())


class FilterOptionsResponse(BaseModel):
    publications: list[str]
    claps_min: int | None
    claps_max: int | None
    reading_time_min: float | None
    reading_time_max: float | None
    date_min: date | None
    date_max: date | None
