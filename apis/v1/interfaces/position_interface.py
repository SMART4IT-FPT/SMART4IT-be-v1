from pydantic import BaseModel, Field
from ..schemas.position_schema import PositionModel, PositionMinimalModel


class PositionsResponseInterface(BaseModel):
    msg: str = Field(..., title="Response Message")
    data: list[PositionModel] = Field(..., title="List of Positions")


class PositionResponseInterface(BaseModel):
    msg: str = Field(..., title="Response Message")
    data: PositionModel = Field(None, title="Position")


class CreatePositionInterface(BaseModel):
    name: str = Field(..., title="Position Name")
    alias: str = Field(..., title="Position Alias")
    description: str = Field(..., title="Position Description")
    start_date: str = Field(..., title="Position Start Date")
    end_date: str = Field(..., title="Position End Date")


class UpdatePositionInterface(BaseModel):
    name: str = Field(None, title="Position Name")
    alias: str = Field(None, title="Position Alias")
    description: str = Field(None, title="Position Description")
    start_date: str = Field(None, title="Position Start Date")
    end_date: str = Field(None, title="Position End Date")


class PublicPositionInterface(BaseModel):
    msg: str = Field(..., title="Response Message")
    data: PositionMinimalModel = Field(None, title="Position")
