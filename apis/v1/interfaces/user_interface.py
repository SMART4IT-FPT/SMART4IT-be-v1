from pydantic import BaseModel, Field
from ..schemas.user_schema import UserModel, UserMinimalModel
from typing import Optional, List, Dict


class UsersResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: list[UserModel] = Field(..., title="Users")


class UserResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: UserModel = Field(..., title="User")


class UsersMinimalResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: list[UserMinimalModel] = Field(..., title="Users")


class UserMinimalResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: UserMinimalModel = Field(None, title="User")


class UserDashboardStats(BaseModel):
    total_projects: int
    total_positions: int
    total_cvs: int
    open_positions: int
    processing_positions: int
    closed_positions: int
    cancelled_positions: int


class UserDashboardResponseInterface(BaseModel):
    data: UserDashboardStats
    message: Optional[str] = None
