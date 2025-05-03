from typing import Dict
from pydantic import BaseModel

class ProjectDashboardResponseInterface(BaseModel):
    total_positions: int
    total_cvs: int
    position_status_counts: Dict[str, int]
    cv_status_counts: Dict[str, int]


class PositionDashboardResponseInterface(BaseModel):
    total_cvs: int
    cv_status_counts: Dict[str, int]
    education_score_distribution: Dict[str, int]
    language_skills_score_distribution: Dict[str, int]
    technical_skills_score_distribution: Dict[str, int]
    personal_projects_score_distribution: Dict[str, int]
    work_experience_score_distribution: Dict[str, int]
    publications_score_distribution: Dict[str, int]
    matching_score_distribution: Dict[str, int]