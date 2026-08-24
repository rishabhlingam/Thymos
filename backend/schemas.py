from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Condition(str, Enum):
    melanoma = "melanoma"
    carcinoma = "carcinoma"
    healthy = "healthy"


class Treatment(str, Enum):
    miraclib = "miraclib"
    phauximab = "phauximab"
    none = "none"


class SampleType(str, Enum):
    PBMC = "PBMC"
    WB = "WB"


class SummaryRow(BaseModel):
    sample: str
    total_count: int
    population: str
    count: int
    percentage: float


class SummaryResponse(BaseModel):
    rows: list[SummaryRow]
    total_samples: int
    page: int
    page_size: int
    total_pages: int


class DataPoint(BaseModel):
    population: str
    response: Optional[str] = None
    percentage: float


class PopulationStats(BaseModel):
    population: str
    responder_median_pct: Optional[float] = None
    non_responder_median_pct: Optional[float] = None
    p_value: Optional[float] = None
    significant: bool
    effect_size: Optional[float] = None
    auc: Optional[float] = None
    fdr: Optional[float] = None
    significant_fdr: bool = False


class ComparisonResponse(BaseModel):
    data_points: list[DataPoint]
    stats: list[PopulationStats]


class BaselineSubsetResponse(BaseModel):
    total_samples: int
    samples_per_project: dict[str, int]
    subjects_by_response: dict[str, int]
    subjects_by_sex: dict[str, int]
    subjects_by_age_group: dict[str, int]


class FilterOptionsResponse(BaseModel):
    conditions: list[str]
    treatments: list[str]
    sample_types: list[str]
    timepoints: list[int]


class HealthResponse(BaseModel):
    status: str
    database: str

class PCAPoint(BaseModel):
    sample: str
    subject_id: str
    response: Optional[str] = None
    sex: str
    project_id: str
    pc1: float
    pc2: float


class PCALoading(BaseModel):
    population: str
    pc1_loading: float
    pc2_loading: float


class PCAResponse(BaseModel):
    points: list[PCAPoint]
    variance_explained: list[float]
    loadings: list[PCALoading]