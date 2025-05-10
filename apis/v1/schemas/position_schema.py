from typing import AnyStr, List, Dict
from pydantic import BaseModel, Field
from enum import Enum
from .jd_schema import JDModel, JDSchema
from ..providers import position_db
from ..utils.utils import get_current_time


class PositionStatus(str, Enum):
    OPEN = "open"
    PROCESSING = "processing"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PositionModel(BaseModel):
    id: str = Field(None, title="Hiring Request ID")
    name: str = Field("", title="Hiring Request Name")
    description: str = Field("", title="Hiring Request Description")
    alias: str = Field("", title="Hiring Request Alias")
    status: PositionStatus = Field(PositionStatus.OPEN, title="Hiring Request Status")
    start_date: str = Field(get_current_time(), title="Hiring Request Start Date")
    end_date: str = Field(None, title="Hiring Request End Date")
    cvs: list[str] = Field([], title="CVs")
    jd: str | JDModel = Field("", title="Job Description")
    # question_banks: list[str] = Field([], title="Question Banks")
    # criterias: list[CriteriaModel] = Field([], title="Criterias")
    re_analyzing: bool = Field(False, title="Re-analyzing")
    match_detail: dict = Field({}, title="Match Detail")


class PositionMinimalModel(BaseModel):
    id: str = Field(None, title="Hiring Request ID")
    name: str = Field("", title="Hiring Request Name")
    description: str = Field("", title="Hiring Request Description")
    alias: str = Field("", title="Hiring Request Alias")
    status: PositionStatus = Field(PositionStatus.OPEN, title="Hiring Request Status")
    jd: str | JDModel = Field("", title="Job Description")


class PositionSchema:
    '''
    Schema and Validation for Position.
    '''

    def __init__(
        self,
        position_id: AnyStr = None,
        name: AnyStr = "",
        description: AnyStr = "",
        alias: AnyStr = "",
        status: PositionStatus = PositionStatus.OPEN,
        start_date: AnyStr = get_current_time(),
        end_date: AnyStr = None,
        cvs: List[AnyStr] = [],
        jd: AnyStr | JDSchema = "",
        # question_banks: List[AnyStr] = [],
        # criterias: List[CriteriaSchema] = [],
        re_analyzing: bool = False,
        match_detail: Dict = {},
    ):
        self.id = position_id
        self.name = name
        self.description = description
        self.alias = alias
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
        self.cvs = cvs
        self.jd = jd
        # self.question_banks = question_banks
        # self.criterias = criterias
        self.re_analyzing = re_analyzing
        self.match_detail = match_detail

    def to_dict(self, include_id=True, minimal=False):
        data_dict = {
            "name": self.name,
            "description": self.description,
            "alias": self.alias,
            "status": self.status,
            "jd": self.jd if isinstance(self.jd, str) else self.jd.to_dict(minimal=minimal),
        }
        if not minimal:
            data_dict["start_date"] = self.start_date
            data_dict["end_date"] = self.end_date
            data_dict["cvs"] = self.cvs
            # data_dict["question_banks"] = self.question_banks
            # data_dict["criterias"] = [criteria.to_dict()
            #                         for criteria in self.criterias]
            data_dict["re_analyzing"] = self.re_analyzing
            data_dict["match_detail"] = self.match_detail
        if include_id:
            data_dict["id"] = self.id
        return data_dict

    @staticmethod
    def from_dict(data: Dict):
        return PositionSchema(
            position_id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            alias=data.get("alias"),
            status=PositionStatus(data.get("status", PositionStatus.OPEN)),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            cvs=data.get("cvs"),
            jd=data.get("jd"),
            # question_banks=data.get("question_banks"),
            # criterias=[CriteriaSchema.from_dict(
            #     criteria) for criteria in data.get("criterias")],
            re_analyzing=data.get("re_analyzing"),
            match_detail=data.get("match_detail")
        )

    @staticmethod
    def find_all_by_ids(position_ids: List[AnyStr]):
        '''
        Find all positions by list of position ids.
        '''
        positions = position_db.get_all_by_ids(position_ids)
        return [PositionSchema.from_dict(position) for position in positions]

    @staticmethod
    def find_by_id(position_id: AnyStr):
        '''
        Find position by id.
        '''
        position = position_db.get_by_id(position_id)
        return PositionSchema.from_dict(position)


    def create_position(self):
        position_id = position_db.create(self.to_dict(include_id=False))
        self.id = position_id
        # Add data to cache
        position_db.cacher.set(
            f"{position_db.collection_name}:{position_id}", self.to_dict(include_id=True))
        return self

    def update_position(self, data: Dict):
        position_db.update(self.id, data)

    def update_status(self, new_status:PositionStatus):
        data = {"status": new_status}  # Fix: wrap string in dict
        position_db.update(self.id, data)

    def delete_position(self):
        position_db.delete(self.id)

    def update_cv(self, cv_id: AnyStr, is_add: bool = True):
        '''
        Update CVs in position.
        '''
        if is_add:
            self.cvs.append(cv_id)
            # Update status to PROCESSING when CVs are added
            if self.status == PositionStatus.OPEN:
                self.update_status(PositionStatus.PROCESSING)
        else:
            self.cvs.remove(cv_id)
            # Update status to OPEN if no CVs left
            if not self.cvs and self.status == PositionStatus.PROCESSING:
                self.update_status(PositionStatus.OPEN)
        self.update_position({"cvs": self.cvs})

    def update_jd(self, jd_id: AnyStr):
        '''
        Update JD in position.
        '''
        self.update_position({"jd": jd_id})

    def update_match_detail(self, detail: Dict):
        '''
        Update match detail.
        '''
        self.update_position({"match_detail": detail})

    def get_jd_by_cvs(self, cv_id: AnyStr):
        """
        Retrieve the Job Description (JD) based on the inputted CVs.
        """
        if cv_id in self.cvs:
            return self.jd
        return None 