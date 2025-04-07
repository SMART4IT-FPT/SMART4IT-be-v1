from pydantic import BaseModel, Field
from typing import Literal
from ..schemas.project_member_schema import ProjectMemberModel, ProjectMemberSchema

TypeGetAllRoles = Literal["OWNER", "RECRUITER"]