from typing import AnyStr
from fastapi import UploadFile, HTTPException, status, BackgroundTasks
import uuid
import time
import requests
import httpx
from ..schemas.user_schema import UserSchema
from ..schemas.cv_schema import CVSchema
from ..schemas.project_schema import ProjectSchema
from ..schemas.position_schema import PositionSchema
# from ..schemas.criteria_schema import CriteriaSchema
from ..providers import memory_cacher, storage_db
from ..utils.extractor import get_cv_content
from ..utils.utils import validate_file_extension, get_content_type
from fastapi.encoders import jsonable_encoder

def _validate_permissions(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
    # Validate project id in user's projects
    if project_id not in user.projects and project_id not in user.shared:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project."
        )

    # Get project
    project = ProjectSchema.find_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )

    # Validate position id in project's positions
    if position_id not in project.positions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this position."
        )

    # Get position
    position = PositionSchema.find_by_id(position_id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found."
        )

    return project, position


def get_all_cvs(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
    _, position = _validate_permissions(project_id, position_id, user)

    # Get CVs
    cvs = CVSchema.find_by_ids(position.cvs)
    return cvs


def get_cv_by_id(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema):
    _, _ = _validate_permissions(project_id, position_id, user)

    # Get CV
    cv = CVSchema.find_by_id(cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found."
        )

    return cv


def _upload_cv_data(data: bytes, filename: AnyStr, watch_id: AnyStr, cv: CVSchema):
    # Get content type of file
    content_type = get_content_type(filename)
    path, url = storage_db.upload(data, filename, content_type)
    memory_cacher.get(watch_id)["percent"][filename] += 15
    cv.update_path_url(path, url)
    memory_cacher.get(watch_id)["percent"][filename] += 5


PROCESSING_API_URL = "http://localhost:8000/api/v1/process"
MATCHING_API_URL = "http://localhost:8000/api/v1/match_cvs"

async def _upload_cvs_data(cvs: list[bytes], filenames: list[AnyStr], watch_id: AnyStr, position: PositionSchema):
    cv_ids = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            for cv, filename in zip(cvs, filenames):
                memory_cacher.get(watch_id)["percent"][filename] = 0

                # Create CV document in database
                cv_instance = CVSchema(name=filename).create_cv()
                cv_ids.append(cv_instance.id)
                memory_cacher.get(watch_id)["percent"][filename] += 10

                # Upload to storage
                _upload_cv_data(cv, filename, watch_id, cv_instance)
                memory_cacher.get(watch_id)["percent"][filename] += 10

                # Save file to cache folder
                cache_file_path = memory_cacher.save_cache_file(cv, filename)
                cv_content = get_cv_content(cache_file_path)
                memory_cacher.remove_cache_file(filename)
                memory_cacher.get(watch_id)["percent"][filename] += 10

                # Update content
                cv_instance.update_content(cv_content)
                memory_cacher.get(watch_id)["percent"][filename] += 10

                # Update to position
                position.update_cv(cv_instance.id, is_add=True)
                memory_cacher.get(watch_id)["percent"][filename] += 10

            # Send CV content to AI service for document processing
            processing_payload = {
                "doc_ids": cv_ids,
                "doc_type": "cv",
            }
            response = await client.post(PROCESSING_API_URL, json=processing_payload)   # response schema: {"doc_type": "", "results": []}
            processing_results = response.json().get("results")

            for processing_result in processing_results:
                cv_id  = processing_result.get("doc_id")
                summary = processing_result.get("summary")
                cv_instance = CVSchema.find_by_id(cv_id)
                cv_instance.update_summary(summary)
                memory_cacher.get(watch_id)["percent"][filename] = 100


        except Exception as e:
            memory_cacher.get(watch_id)["error"][filename] = str(e)
            memory_cacher.get(watch_id)["percent"][filename] = -1  # Mark as failed
            raise RuntimeError(f"Process stopped due to error: {str(e)}")  # 🚨 STOP EVERYTHING

        # Perform Matching for all CVs at once
        matching_payload = jsonable_encoder({
            "jd_id": position.get_jd_by_cvs(cv_ids[0]),  # Pass the first CV ID as a string
            "cv_ids": cv_ids,
            "weight": {
                "education_score_config": {"W_education_score": 0.05},
                "language_score_config": {"W_language_score": 0.05},
                "technical_score_config": {"W_technical_score": 0.35},
                "experience_score_config": {
                    "W_experience_score": 0.55,
                    "relevance_score_w": 0.8,
                    "difficulty_score_w": 0.15,
                    "duration_score_w": 0.05
                }
            }
        })

        response = await client.post(MATCHING_API_URL, json=matching_payload)       
        matching_results = response.json().get("results")
        
        for matching_result in matching_results:
            cv_id = matching_result.get("cv_id")
            result = matching_result.get("matching_result")
            cv_instance = CVSchema.find_by_id(cv_id)
            cv_instance.update_matching(result)
            # memory_cacher.get(watch_id)["percent"][cv_instance.name] += 20

        # Mark as completed
        # for filename in filenames:
        #     memory_cacher.get(watch_id)["percent"][filename] = 100

        # Wait for 10 seconds before cleanup
        time.sleep(10)
        memory_cacher.remove(watch_id)

async def upload_cvs_data(project_id: AnyStr, position_id: AnyStr, user: UserSchema, cvs: list[UploadFile], bg_tasks: BackgroundTasks):
    # Validate permission
    _, position = _validate_permissions(project_id, position_id, user)

    # Create watch id
    watch_id = str(uuid.uuid4())

    # Read files
    files: list[bytes] = []
    filenames: list[AnyStr] = []
    for cv in cvs:
        file_content = await cv.read()
        files.append(file_content)
        filenames.append(cv.filename)

    # Initialize cache
    memory_cacher.set(watch_id, {
        "percent": {},
        "error": {}
    })

    # Upload CVs
    bg_tasks.add_task(_upload_cvs_data, files, filenames, watch_id, position)

    return watch_id


async def upload_cv_data(position_id: AnyStr, cv: UploadFile, bg_tasks: BackgroundTasks):
    # Validate extension
    validate_file_extension(cv.filename)

    # Get position
    position = PositionSchema.find_by_id(position_id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found."
        )

    if position.is_closed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position is closed."
        )

    # Validate criterias
    if len(position.criterias) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No criteria to analyze."
        )

    # Read files
    file_content = await cv.read()

    # Create watch id
    watch_id = str(uuid.uuid4())

    # Initialize cache
    memory_cacher.set(watch_id, {
        "percent": {},
        "error": {}
    })

    # Upload CV
    bg_tasks.add_task(_upload_cv_data, [file_content], [
                      cv.filename], watch_id, position)

    return watch_id


def get_upload_progress(watch_id: AnyStr):
    return memory_cacher.get(watch_id)


async def download_cv_content(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema) -> bytes:
    # Validate permission
    _, _ = _validate_permissions(project_id, position_id, user)

    # Get CV
    cv = CVSchema.find_by_id(cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found."
        )

    cv_content = cv.download_content()
    if not cv_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV content not found."
        )

    return cv_content


# def get_cv_detail_control(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema):
#     # Validate permission
#     _, position = _validate_permissions(project_id, position_id, user)

#     # Get Match detail from position
#     match_detail = position.match_detail

#     # Format detail
#     fmt_detail = {}
#     for cri, cri_v in match_detail.items():
#         for jdw, jdw_v in cri_v["detail"].items():
#             if cv_id in jdw_v:
#                 fmt_detail[f"{cri}:{jdw}"] = jdw_v[cv_id]["detail"]
#                 fmt_detail[f"{cri}:{jdw}"]["overall"] = jdw_v[cv_id]["overall"]

#     return fmt_detail

def get_cv_detail_control(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema):
    _, _ = _validate_permissions(project_id, position_id, user)

    # Get CV
    cv = CVSchema.find_by_id(cv_id)
    # Return CV' 'detail' and 'matching' keys of the cv
    cv_summary = cv.to_dict().get('summary')
    print(cv_summary)
    cv_matching = cv.to_dict().get('matching')
    print(cv_matching)
    cv = { 'summary': cv_summary, 'matching': cv_matching }
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )
    return cv


def delete_cvs_by_ids(cv_ids: list[AnyStr]):
    for cv_id in cv_ids:
        cv = CVSchema.find_by_id(cv_id)
        if cv:
            cv.delete_cv()


def delete_current_cv(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema):
    # Validate permission
    _, position = _validate_permissions(project_id, position_id, user)

    # Get CV
    cv = CVSchema.find_by_id(cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found."
        )

    # Remove CV from position
    position.update_cv(cv_id, is_add=False)

    # Delete vectors
    # VectorEmbeddingSchema.from_query(
    #     collection=position_id,
    #     key="id",
    #     value=cv_id
    # ).delete(position_id)

    # Delete CV
    cv.delete_cv()
