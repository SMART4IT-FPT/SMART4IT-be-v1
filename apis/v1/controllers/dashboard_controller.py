from typing import Dict, AnyStr
from fastapi import HTTPException, status
from ..schemas.user_schema import UserSchema
from ..schemas.project_schema import ProjectSchema
from ..schemas.position_schema import PositionSchema
from ..schemas.cv_schema import CVSchema, CVStatus
from ..schemas.dashboard import (
    ProjectDashboardResponseInterface,
    PositionDashboardResponseInterface
)


async def get_project_dashboard_stats(project_id: str, user: UserSchema) -> Dict:
    """
    Get project's dashboard statistics including:
    - Total positions
    - Total CVs
    - Position status counts
    - Recent activities
    """
    # Validate project access
    if project_id not in user.projects and project_id not in user.shared:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project."
        )
    
    # Get project
    project = ProjectSchema.find_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    
    # Get all positions
    positions = PositionSchema.find_all_by_ids(project.positions)
    
    # Initialize counters
    total_cvs = 0
    position_status_counts = {
        "open": 0,
        "processing": 0,
        "closed": 0,
        "cancelled": 0
    }
    cv_status_counts = {
        "APPLYING": 0,
        "ACCEPTED": 0,
        "INTERVIEWING": 0,
        "HIRED": 0
    }
    
    # Count CVs and statuses
    for position in positions:
        # Count position statuses
        position_status_counts[position.status.value] += 1
        
        # Count CVs and their statuses
        cvs = CVSchema.find_by_ids(position.cvs)
        total_cvs += len(cvs)
        for cv in cvs:
            cv_status_counts[cv.status.value] += 1
    
    response = ProjectDashboardResponseInterface(
        total_positions=len(positions),
        total_cvs=total_cvs,
        position_status_counts=position_status_counts,
        cv_status_counts=cv_status_counts
    )
    return response.dict()


async def get_position_dashboard_stats(project_id: str, position_id: str, user: UserSchema) -> Dict:
    """
    Get position's dashboard statistics including:
    - Total CVs
    - CV status counts
    - Matching scores distribution
    - Recent activities
    """
    # Validate project access
    if project_id not in user.projects and project_id not in user.shared:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project."
        )
    
    # Get project
    project = ProjectSchema.find_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    
    # Get position
    position = PositionSchema.find_by_id(position_id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found."
        )
    
    # Get all CVs
    cvs = CVSchema.find_by_ids(position.cvs)
    
    # Initialize counters
    cv_status_counts = {
        "APPLYING": 0,
        "ACCEPTED": 0,
        "INTERVIEWING": 0,
        "HIRED": 0
    }
    
    # Count CV statuses and collect matching scores
    matching_scores = []
    for cv in cvs:
        cv_status_counts[cv.status.value] += 1
        if cv.matching and isinstance(cv.matching, dict):
            overall_result = cv.matching.get("overall_result")
            matching_scores.append(overall_result)

    # Overall result has: education_score, language_skills_score, technical_skills_score, personal_projects_score, work_experience_score, publications_score, overall_score
    # Calculate score distribution for each score

    education_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }
    language_skills_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }   
    technical_skills_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }   
    personal_projects_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }           
    work_experience_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }               
    publications_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }              
    overall_score_distribution = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0
    }


    for matching_score in matching_scores:
        if matching_score and isinstance(matching_score, dict):
            education_score = matching_score.get("education_score")
            language_skills_score = matching_score.get("language_skills_score")
            technical_skills_score = matching_score.get("technical_skills_score")
            personal_projects_score = matching_score.get("personal_projects_score")
            work_experience_score = matching_score.get("work_experience_score")
            publications_score = matching_score.get("publications_score")
            overall_score = matching_score.get("overall_score")
            
            if education_score <= 20:
                education_score_distribution["0-20"] += 1
            elif education_score <= 40:
                education_score_distribution["21-40"] += 1
            elif education_score <= 60:
                education_score_distribution["41-60"] += 1
            elif education_score <= 80:
                education_score_distribution["61-80"] += 1
            else:
                education_score_distribution["81-100"] += 1

            if language_skills_score <= 20:
                language_skills_score_distribution["0-20"] += 1
            elif language_skills_score <= 40:
                language_skills_score_distribution["21-40"] += 1
            elif language_skills_score <= 60:
                language_skills_score_distribution["41-60"] += 1
            elif language_skills_score <= 80:
                language_skills_score_distribution["61-80"] += 1
            else:
                language_skills_score_distribution["81-100"] += 1

            if technical_skills_score <= 20:
                technical_skills_score_distribution["0-20"] += 1
            elif technical_skills_score <= 40:
                technical_skills_score_distribution["21-40"] += 1
            elif technical_skills_score <= 60:
                technical_skills_score_distribution["41-60"] += 1
            elif technical_skills_score <= 80:
                technical_skills_score_distribution["61-80"] += 1
            else:
                technical_skills_score_distribution["81-100"] += 1

            if personal_projects_score <= 20:
                personal_projects_score_distribution["0-20"] += 1
            elif personal_projects_score <= 40:
                personal_projects_score_distribution["21-40"] += 1
            elif personal_projects_score <= 60:
                personal_projects_score_distribution["41-60"] += 1
            elif personal_projects_score <= 80:
                personal_projects_score_distribution["61-80"] += 1
            else:
                personal_projects_score_distribution["81-100"] += 1

            if work_experience_score <= 20:
                work_experience_score_distribution["0-20"] += 1
            elif work_experience_score <= 40:
                work_experience_score_distribution["21-40"] += 1
            elif work_experience_score <= 60:
                work_experience_score_distribution["41-60"] += 1
            elif work_experience_score <= 80:
                work_experience_score_distribution["61-80"] += 1
            else:
                work_experience_score_distribution["81-100"] += 1

            if publications_score <= 20:
                publications_score_distribution["0-20"] += 1
            elif publications_score <= 40:
                publications_score_distribution["21-40"] += 1
            elif publications_score <= 60:
                publications_score_distribution["41-60"] += 1
            elif publications_score <= 80:
                publications_score_distribution["61-80"] += 1
            else:
                publications_score_distribution["81-100"] += 1

            if overall_score <= 20:
                overall_score_distribution["0-20"] += 1
            elif overall_score <= 40:
                overall_score_distribution["21-40"] += 1
            elif overall_score <= 60:
                overall_score_distribution["41-60"] += 1
            elif overall_score <= 80:
                overall_score_distribution["61-80"] += 1
            else:
                overall_score_distribution["81-100"] += 1

    response = PositionDashboardResponseInterface(
        total_cvs=len(cvs),
        cv_status_counts=cv_status_counts,
        education_score_distribution=education_score_distribution,
        language_skills_score_distribution=language_skills_score_distribution,
        technical_skills_score_distribution=technical_skills_score_distribution,
        personal_projects_score_distribution=personal_projects_score_distribution,
        work_experience_score_distribution=work_experience_score_distribution,
        publications_score_distribution=publications_score_distribution,
        matching_score_distribution=overall_score_distribution
    )
    return response.dict()

    # Calculate matching score distribution
    # score_distribution = {
    #     "0-20": 0,
    #     "21-40": 0,
    #     "41-60": 0,
    #     "61-80": 0,
    #     "81-100": 0
    # }
    
    # for score in matching_scores:
    #     if score <= 20:
    #         score_distribution["0-20"] += 1
    #     elif score <= 40:
    #         score_distribution["21-40"] += 1
    #     elif score <= 60:
    #         score_distribution["41-60"] += 1
    #     elif score <= 80:
    #         score_distribution["61-80"] += 1
    #     else:
    #         score_distribution["81-100"] += 1
    
    # response = PositionDashboardResponseInterface(
    #     total_cvs=len(cvs),
    #     cv_status_counts=cv_status_counts,
    #     matching_score_distribution=score_distribution
    # )
    # return response.dict() 