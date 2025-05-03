from pydantic import BaseModel, Field
from ..schemas.position_schema import PositionModel, PositionMinimalModel
from typing import Optional, List, Dict


class PositionsResponseInterface(BaseModel):
    msg: str = Field(..., title="Response Message")
    data: list[PositionModel] = Field(..., title="List of Positions")


class PositionResponseInterface(BaseModel):
    msg: str = Field(..., title="Response Message")
    data: PositionModel = Field(None, title="Hiring Request")


class CreatePositionInterface(BaseModel):
    name: str = Field(..., title="Hiring Request Name")
    alias: str = Field(..., title="Hiring Request Alias")
    description: str = Field(..., title="Hiring Request Description")
    start_date: str = Field(..., title="Hiring Request Start Date")
    end_date: str = Field(..., title="Hiring Request End Date")


class UpdatePositionInterface(BaseModel):
    name: str = Field(None, title="Hiring Request Name")
    alias: str = Field(None, title="Hiring Request Alias")
    description: str = Field(None, title="Hiring Request Description")
    start_date: str = Field(None, title="Hiring Request Start Date")
    end_date: str = Field(None, title="Hiring Request End Date")


class PublicPositionInterface(BaseModel):
    msg: str = Field(..., title="Response Message")
    data: PositionMinimalModel = Field(None, title="Hiring Request")


class PositionDashboardStats(BaseModel):
    total_cvs: int
    processed_cvs: int
    pending_cvs: int
    matching_score_distribution: Dict[str, int]  # Range (e.g. "0-20") to count
    recent_activities: List[Dict[str, str]]  # List of {type, description, timestamp}
    status: str


class PositionDashboardResponseInterface(BaseModel):
    data: PositionDashboardStats
    message: Optional[str] = None
