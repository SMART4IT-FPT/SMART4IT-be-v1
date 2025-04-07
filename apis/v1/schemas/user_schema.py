from typing import Dict, AnyStr, List
from pydantic import BaseModel, Field
from ..providers import user_db
from ..utils.utils import get_current_time
from ..utils.constants import PLACEHOLDER_IMAGE


class UserModel(BaseModel):
    id: str = Field(..., title="User ID")
    name: str = Field(..., title="User Name")
    email: str = Field(..., title="User Email")
    avatar: str = Field(..., title="User Avatar")
    created_at: str = Field(..., title="User Created At")


class UserMinimalModel(BaseModel):
    id: str = Field(..., title="User ID")
    name: str = Field(..., title="User Name")
    email: str = Field(..., title="User Email")
    avatar: str = Field(..., title="User Avatar")


class UserSchema:
    def __init__(
        self,
        id: AnyStr = None,
        name: AnyStr = "",
        email: AnyStr = "",
        avatar: AnyStr = PLACEHOLDER_IMAGE,
        created_at: AnyStr = get_current_time(),
    ):
        self.user_id = id
        self.name = name
        self.email = email
        self.avatar = avatar
        self.created_at = created_at

    @property
    def user_id(self):
        return self.id
    
    @user_id.setter
    def user_id(self, value):
        self.id = value

    def to_dict(self, include_id=True, minimal=False):
        data_dict = {
            "name": self.name,
            "email": self.email,
            "avatar": self.avatar,
        }
        if not minimal:
            data_dict["created_at"] = self.created_at
        if include_id:
            data_dict["id"] = self.id
        return data_dict

    @staticmethod
    def from_dict(data: Dict):
        return UserSchema(
            id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            avatar=data.get("avatar"),
            created_at=data.get("created_at"),
        )

    @staticmethod
    def find_all():
        users = user_db.get_all()
        return [UserSchema.from_dict(user) for user in users]

    @staticmethod
    def find_by_email(email: AnyStr):
        queries = user_db.query_equal("email", email)
        if len(queries) == 0:
            return None
        return UserSchema.from_dict(queries[0])

    @staticmethod
    def find_by_id(user_id: AnyStr):
        data = user_db.get_by_id(user_id)     
        if not data:
            return None
        return UserSchema.from_dict(data)

    @staticmethod
    def find_all_by_ids(user_ids: List[AnyStr]):
        users = user_db.get_all_by_ids(user_ids)
        return [UserSchema.from_dict(user) for user in users if user]

    @staticmethod
    def find_user_by_substring(substring: AnyStr):
        users = user_db.query_similar("email", substring)
        return [UserSchema.from_dict(user) for user in users]

    def create_user(self):
        user_id = user_db.create(self.to_dict(include_id=False))
        self.id = user_id
        return self