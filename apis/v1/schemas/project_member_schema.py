from typing import Dict, AnyStr, List
import enum
from pydantic import BaseModel, Field
from ..providers import project_member_db
from ..schemas.project_schema import ProjectSchema  # Import ProjectSchema


class UserRole(enum.Enum):
    owner = "OWNER"
    recruiter = "RECRUITER"

class ProjectMemberModel(BaseModel):
    uid: str = Field(..., title="Project Member ID")
    project_id: str = Field(..., title="Project ID")
    user_id: str = Field(..., title="User ID")
    role: str = Field(..., title="User Role")


class ProjectMemberSchema():
    def __init__(
        self,
        uid: AnyStr = None,
        project_id: AnyStr = "",
        user_id: AnyStr = "",
        role: AnyStr = "",
    ):
        self.uid = uid
        self.project_id = project_id
        self.user_id = user_id
        self.role = role

    def to_dict(self, include_id=True):
        data = {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
        }
        if include_id:
            data["id"] = self.id
        return data

    @staticmethod
    def from_dict(data: Dict):
        return ProjectMemberSchema(
            id=data.get("id"),
            project_id=data.get("project_id"),
            user_id=data.get("user_id"),
            role=data.get("role"),
        )

    @staticmethod
    def find_all():
        project_members = project_member_db.get_all()
        return [ProjectMemberSchema.from_dict(member) for member in project_members]
    
    @staticmethod
    def find_by_user_id(user_id: AnyStr):
        queries = project_member_db.query_equal("user_id", user_id)
        if len(queries) == 0:
            return None
        return ProjectMemberSchema.from_dict(queries[0])
    
    @staticmethod
    def find_by_project_id(project_id: AnyStr):
        queries = project_member_db.query_equal("project_id", project_id)
        if len(queries) == 0:
            return None
        return ProjectMemberSchema.from_dict(queries[0])

    @staticmethod
    def find_by_id(uid: AnyStr):
        data = project_member_db.get_by_id(uid)
        if not data:
            return None
        return ProjectMemberSchema.from_dict(data)

    @staticmethod
    def find_all_by_ids(uids: List[AnyStr]):
        project_member = project_member_db.get_all_by_ids(uids)
        return [ProjectMemberSchema.from_dict(member) for member in project_member]

    @staticmethod
    def get_projects_by_user_id(user_id: AnyStr):
        """
        Retrieve all projects associated with a specific user.
        """
        project_members = project_member_db.query_equal("user_id", user_id)
        if not project_members:
            return []
        project_ids = [member.get("project_id") for member in project_members]
        return ProjectSchema.find_all_by_ids(project_ids)
    
    def get_owned_projects_by_user_id(user_id: AnyStr):
        """
        Retrieve all projects owned by a specific user.
        """
        project_members = project_member_db.query_equal("user_id", user_id)
        if not project_members:
            return []
        project_ids = [member.get("project_id") for member in project_members if member.get("role") == UserRole.owner]
        return ProjectSchema.find_all_by_ids(project_ids)
    
    def get_shared_projects_by_user_id(user_id: AnyStr):
        """
        Retrieve all projects shared with a specific user.
        """
        project_members = project_member_db.query_equal("user_id", user_id)
        if not project_members:
            return []
        project_ids = [member.get("project_id") for member in project_members if member.get("role") == UserRole.recruiter]
        return ProjectSchema.find_all_by_ids(project_ids)
    
    @staticmethod
    def update_user_project(user_id: AnyStr, project_id: AnyStr, role: AnyStr):
        """
        Create a new record in the project member collection.
        
        Args:
            user_id (AnyStr): The ID of the user.
            project_id (AnyStr): The ID of the project.
            role (AnyStr): The role of the user in the project.
            
        Returns:
            The ID of the created record.
        """
        data = {
            "project_id": project_id,
            "user_id": user_id,
            "role": role,
        }
        project_member = ProjectMemberSchema.from_dict(data)
        record_id = project_member_db.create(project_member.to_dict(include_id=False))
        return record_id
    
    def create_user_project(self):
        """
        Create a new project member record in the database.
        
        Returns:
            The created ProjectMemberSchema instance.
        """
        project_member_id = project_member_db.create(self.to_dict(include_id=False))
        self.uid = project_member_id
        return self
