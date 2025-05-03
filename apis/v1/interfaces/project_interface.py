from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field
from ..schemas.project_schema import ProjectModel


TypeGetAllProjects = Literal["owned", "shared", "deleted"]


class ProjectResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: ProjectModel = Field(None, title="Project Data")


class ProjectsResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: list[ProjectModel] = Field(..., title="Projects Data")


class CreateProjectInterface(BaseModel):
    name: str = Field(..., title="Project Name")
    alias: str = Field(..., title="Project Alias")
    description: str = Field(None, title="Project Description")


class UpdateProjectInterface(BaseModel):
    name: str = Field(None, title="Project Name")
    alias: str = Field(None, title="Project Alias")
    description: str = Field(None, title="Project Description")


class UpdateLastOpenedProjectInterface(BaseModel):
    last_opened: str = Field(..., title="Last Opened Time")


class UpdateMemberProjectInterface(BaseModel):
    members: list[str] = Field(..., title="Project Members")
    is_add: bool = Field(True, title="Add or Remove Member")


class ProjectDashboardStats(BaseModel):
    total_positions: int
    total_cvs: int
    open_positions: int
    processing_positions: int
    closed_positions: int
    cancelled_positions: int
    recent_activities: List[Dict[str, str]]  # List of {type, description, timestamp}


class ProjectDashboardResponseInterface(BaseModel):
    data: ProjectDashboardStats
    message: Optional[str] = None
