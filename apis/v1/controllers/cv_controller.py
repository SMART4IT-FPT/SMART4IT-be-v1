from typing import AnyStr
from fastapi import UploadFile, HTTPException, status, BackgroundTasks
import uuid
import time
import httpx
import pandas as pd
from io import BytesIO
from datetime import datetime
from dateutil import parser
from ..schemas.user_schema import UserSchema
from ..schemas.cv_schema import CVSchema
from ..schemas.project_schema import ProjectSchema
from ..schemas.position_schema import PositionSchema, PositionStatus
from ..providers import memory_cacher, storage_db
from ..utils.extractor import get_cv_content
from ..utils.formatter import build_cv_summary_file, build_cv_matching_file
from ..utils.utils import validate_file_extension, get_content_type
from fastapi.encoders import jsonable_encoder
import os
from dotenv import load_dotenv
load_dotenv

processing_api_url = os.environ.get("PROCESSING_API_URL")
matching_api_url = os.environ.get("MATCHING_API_URL")

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
            detail="Hiring Request not found."
        )

    # Check if position is open for CV uploads
    if position.status not in [PositionStatus.OPEN, PositionStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload CVs to a closed or cancelled hiring request."
        )

    return project, position


def get_all_cvs(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
    _, position = _validate_permissions(project_id, position_id, user)

    # Get CVs
    cvs = CVSchema.find_by_ids(position.cvs)
    return cvs


def get_all_cvs_summary(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
    _, position = _validate_permissions(project_id, position_id, user)

    cvs = CVSchema.find_by_ids(position.cvs)
    cvs = [cv.to_dict() for cv in cvs]
    cvs = [
        {
            "id": cv["id"],
            "upload_at": cv["upload_at"],
            "summary": cv["summary"],
            "matching": cv["matching"]
        } 
        for cv in cvs
    ]

    cvs_df = build_cv_summary_file(cvs)
    match_df = build_cv_matching_file(cvs)  # <-- assuming this is your 2nd sheet function

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Write the first sheet
        cvs_df.to_excel(writer, index=False, sheet_name="CVs Summary")
        match_df.to_excel(writer, index=False, sheet_name="Matching Scores")

        workbook = writer.book

        # Wrap text format
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

        # Adjust columns for "CVs Summary"
        summary_ws = writer.sheets["CVs Summary"]
        for i, column in enumerate(cvs_df.columns):
            col_width = max(cvs_df[column].astype(str).map(len).max(), len(column)) + 2
            summary_ws.set_column(i, i, min(col_width, 30), wrap_format)  # Max width = 50

        # Adjust columns for "Matching Scores"
        matching_ws = writer.sheets["Matching Scores"]
        for i, column in enumerate(match_df.columns):
            col_width = max(match_df[column].astype(str).map(len).max(), len(column)) + 2
            matching_ws.set_column(i, i, min(col_width, 30), wrap_format)  # Max width = 60

    output.seek(0)
    return output




def get_all_cvs_matching(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
    _, position = _validate_permissions(project_id, position_id, user)

    cvs = CVSchema.find_by_ids(position.cvs)
    cvs = [cv.to_dict() for cv in cvs]
    # Kepp only 'id' and 'summary' keys of the cv
    cvs = [
        {
            "id": cv["id"],
            "upload_at": cv["upload_at"],
            "matching": cv["matching"]
        } 
        for cv in cvs
    ]
    cvs_df = build_cv_matching_file(cvs)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        cvs_df.to_excel(writer, index=False, sheet_name=f"Matching Result_{position_id}")
    output.seek(0)
    return output


def get_cv_by_id(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema):
    _, _ = _validate_permissions(project_id, position_id, user)

    # Get CV
    cv = CVSchema.find_by_id(cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found 1."
        )

    return cv


async def upload_cvs_data(project_id: AnyStr, position_id: AnyStr, user: UserSchema, cvs: list[UploadFile], weight: dict, llm_name: str, bg_tasks: BackgroundTasks):
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

    # Update position status to PROCESSING
    position.update_status(PositionStatus.PROCESSING)

    # Upload CVs
    bg_tasks.add_task(_upload_cvs_data, files, filenames, watch_id, position, weight, llm_name)

    return watch_id


async def _upload_cvs_data(
    cvs: list[bytes],
    filenames: list[AnyStr],
    watch_id: AnyStr,
    position: PositionSchema,
    weight: dict,
    llm_name: str
):
    cv_ids = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            for cv, filename in zip(cvs, filenames):
                # Initialize percent = 0
                cache_data = memory_cacher.get(watch_id)
                if cache_data:
                    cache_data["percent"][filename] = 0
                    memory_cacher.set(watch_id, cache_data)

                # Create CV document
                cv_instance = CVSchema(name=filename).create_cv()
                cv_ids.append(cv_instance.id)
                update_cache_percent(watch_id, filename, 10)

                # Upload storage
                _upload_cv_data(cv, filename, watch_id, cv_instance)
                update_cache_percent(watch_id, filename, 10)

                # Save cache file + extract content
                cache_file_path = memory_cacher.save_cache_file(cv, filename)
                cv_content = get_cv_content(cache_file_path)
                memory_cacher.remove_cache_file(filename)
                update_cache_percent(watch_id, filename, 10)

                # Update content in DB
                cv_instance.update_content(cv_content)
                update_cache_percent(watch_id, filename, 10)

                # Add to position
                position.update_cv(cv_instance.id, is_add=True)
                update_cache_percent(watch_id, filename, 10)

            # Send to AI processing
            processing_payload = {
                "doc_ids": cv_ids,
                "doc_type": "cv",
                "llm_name": llm_name
            }
            response = await client.post(processing_api_url, json=processing_payload, timeout=len(cv_ids) * 120)
            processing_results = response.json().get("results")

            filename_by_cv_id = dict(zip(cv_ids, filenames))

            for processing_result in processing_results:
                cv_id = processing_result.get("doc_id")
                summary = processing_result.get("summary")
                labels = processing_result.get("labels")
                cv_instance = CVSchema.find_by_id(cv_id)
                cv_instance.update_weight(weight)
                cv_instance.update_summary(summary)
                cv_instance.update_labels(labels)

                filename = filename_by_cv_id.get(cv_id)
                if filename:
                    cache_data = memory_cacher.get(watch_id)
                    if cache_data and filename in cache_data["percent"]:
                        cache_data["percent"][filename] = 100
                        memory_cacher.set(watch_id, cache_data)

            # Check if end date has passed and auto-close if needed
            if position.end_date:
                try:
                    end_date = parser.parse(position.end_date)
                    if datetime.now() > end_date:
                        position.update_status(PositionStatus.CLOSED)
                except Exception as e:
                    print(f"Error parsing end date: {str(e)}")

        except Exception as e:
            # Handle errors for each file, ensure cache is updated
            for filename in filenames:
                set_cache_error(watch_id, filename, str(e))
            raise RuntimeError(f"Process stopped due to error: {str(e)}")

        # Matching after processing is complete
        matching_payload = jsonable_encoder({
            "jd_id": position.get_jd_by_cvs(cv_ids[0]),
            "cv_ids": cv_ids,
            "weight": weight,
            "llm_name": llm_name
        })
        response = await client.post(matching_api_url, json=matching_payload)
        matching_results = response.json().get("results")

        for matching_result in matching_results:
            cv_id = matching_result.get("cv_id")
            result = matching_result.get("matching_result")
            cv_instance = CVSchema.find_by_id(cv_id)
            cv_instance.update_matching(result)
            position.update_status(PositionStatus.OPEN)

        # Check completion
        cache_data = memory_cacher.get(watch_id)
        if cache_data and all(percent >= 100 for percent in cache_data["percent"].values()):
            cache_data["status"] = "completed"
            memory_cacher.set(watch_id, cache_data)

def update_cache_percent(watch_id, filename, delta):
    cache_data = memory_cacher.get(watch_id)
    if cache_data and filename in cache_data["percent"]:
        cache_data["percent"][filename] += delta
        memory_cacher.set(watch_id, cache_data)

def set_cache_error(watch_id, filename, error_msg):
    cache_data = memory_cacher.get(watch_id)
    if cache_data and filename in cache_data["percent"]:
        cache_data["error"][filename] = error_msg
        cache_data["percent"][filename] = -1
        memory_cacher.set(watch_id, cache_data)





def _upload_cv_data(data: bytes, filename: AnyStr, watch_id: AnyStr, cv: CVSchema):
    content_type = get_content_type(filename)
    path, url = storage_db.upload(data, filename, content_type)
    cache_data = memory_cacher.get(watch_id)
    if cache_data and filename in cache_data["percent"]:
        cache_data["percent"][filename] += 15
        memory_cacher.set(watch_id, cache_data)
    cv.update_path_url(path, url)
    cache_data = memory_cacher.get(watch_id)
    if cache_data and filename in cache_data["percent"]:
        cache_data["percent"][filename] += 5
        memory_cacher.set(watch_id, cache_data)



async def upload_cv_data(project_id: AnyStr, position_id: AnyStr, cv: UploadFile, user: UserSchema, bg_tasks: BackgroundTasks):
    # Validate extension
    validate_file_extension(cv.filename)

    # Validate permission and get position
    _, position = _validate_permissions(project_id, position_id, user)

    # Check if position is open for CV uploads
    if position.status not in [PositionStatus.OPEN, PositionStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload CVs to a closed or cancelled hiring request."
        )

    # Read file
    file_content = await cv.read()

    # Create watch id
    watch_id = str(uuid.uuid4())

    # Initialize cache
    memory_cacher.set(watch_id, {
        "percent": {},
        "error": {}
    })

    # Update position status to PROCESSING
    position.update_status(PositionStatus.PROCESSING)

    # Upload CV
    bg_tasks.add_task(_upload_cv_data, [file_content], [cv.filename], watch_id, position)

    return watch_id

# async def _upload_cv_data(
#     cvs: list[bytes],
#     filenames: list[AnyStr],
#     watch_id: AnyStr,
#     position: PositionSchema
# ):
#     cv_ids = []
#     try:
#         for cv, filename in zip(cvs, filenames):
#             # Initialize percent = 0
#             cache_data = memory_cacher.get(watch_id)
#             if cache_data:
#                 cache_data["percent"][filename] = 0
#                 memory_cacher.set(watch_id, cache_data)

#             # Create CV document
#             cv_instance = CVSchema(name=filename).create_cv()
#             cv_ids.append(cv_instance.id)
#             update_cache_percent(watch_id, filename, 10)

#             # Upload storage
#             _upload_cv_data_to_storage(cv, filename, watch_id, cv_instance)
#             update_cache_percent(watch_id, filename, 10)

#             # Save cache file + extract content
#             cache_file_path = memory_cacher.save_cache_file(cv, filename)
#             cv_content = get_cv_content(cache_file_path)
#             memory_cacher.remove_cache_file(filename)
#             update_cache_percent(watch_id, filename, 10)

#             # Update content in DB
#             cv_instance.update_content(cv_content)
#             update_cache_percent(watch_id, filename, 10)

#             # Add to position
#             position.update_cv(cv_instance.id, is_add=True)
#             update_cache_percent(watch_id, filename, 10)

#             # Update cache to completed
#             cache_data = memory_cacher.get(watch_id)
#             if cache_data and filename in cache_data["percent"]:
#                 cache_data["percent"][filename] = 100
#                 memory_cacher.set(watch_id, cache_data)

#             # Check if end date has passed and auto-close if needed
#             if position.end_date and datetime.now() > datetime.fromisoformat(position.end_date):
#                 position.update_status(PositionStatus.CLOSED)

#     except Exception as e:
#         # Handle errors for each file, ensure cache is updated
#         for filename in filenames:
#             set_cache_error(watch_id, filename, str(e))
#         raise RuntimeError(f"Process stopped due to error: {str(e)}")

# def _upload_cv_data_to_storage(data: bytes, filename: AnyStr, watch_id: AnyStr, cv: CVSchema):
#     content_type = get_content_type(filename)
#     path, url = storage_db.upload(data, filename, content_type)
#     cache_data = memory_cacher.get(watch_id)
#     if cache_data and filename in cache_data["percent"]:
#         cache_data["percent"][filename] += 15
#         memory_cacher.set(watch_id, cache_data)
#     cv.update_path_url(path, url)
#     cache_data = memory_cacher.get(watch_id)
#     if cache_data and filename in cache_data["percent"]:
#         cache_data["percent"][filename] += 5
#         memory_cacher.set(watch_id, cache_data)



async def rematch_cvs_data(project_id: AnyStr, position_id: AnyStr, user: UserSchema, weight: dict, llm_name: str, bg_tasks: BackgroundTasks):
    '''
    Retrieve all uploaded CVs in a project and re-match them.
    '''
    # Validate permissions
    _, position = _validate_permissions(project_id, position_id, user)

    # Get all CVs associated with the position
    cvs = CVSchema.find_by_ids(position.cvs)
    if not cvs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CVs found for this position."
        )

    # Prepare CV IDs for re-matching
    cv_ids = [cv.id for cv in cvs]

    # Add the re-matching task to background tasks
    bg_tasks.add_task(_rematch_cvs_task, cv_ids, position, weight, llm_name)


async def _rematch_cvs_task(cv_ids: list[AnyStr], position: PositionSchema, weight: dict, llm_name: str):
    '''
    Background task to perform re-matching for CVs.
    '''
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Prepare the matching payload
            matching_payload = jsonable_encoder({
                "jd_id": position.get_jd_by_cvs(cv_ids[0]),  # Use the first CV ID to get the JD
                "cv_ids": cv_ids,
                "weight": weight,  # Use the weight parameter from the frontend
                "llm_name": llm_name
            })

            # Send the payload to the matching API
            response = await client.post(matching_api_url, json=matching_payload)
            matching_results = response.json().get("results")
            print("result", matching_results)

            # Update matching results for each CV
            for matching_result in matching_results:
                cv_id = matching_result.get("cv_id")
                result = matching_result.get("matching_result")
                cv_instance = CVSchema.find_by_id(cv_id)
                cv_instance.update_matching(result)

        except Exception as e:
            # Log the error for debugging
            print(f"Re-matching failed due to error: {str(e)}")


def get_upload_progress(watch_id: AnyStr):
    progress = memory_cacher.get(watch_id)
    if progress is None:
        return {"percent": {}, "error": {}, "status": "not_found"}
    if "status" not in progress:
        progress["status"] = "processing"
    return progress



async def download_cv_content(project_id: AnyStr, position_id: AnyStr, cv_id: AnyStr, user: UserSchema) -> bytes:
    # Validate permission
    _, _ = _validate_permissions(project_id, position_id, user)

    # Get CV
    cv = CVSchema.find_by_id(cv_id)
    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found 2."
        )

    cv_content = cv.download_content()
    if not cv_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV content not found."
        )

    return cv_content


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
            detail="CV not found 3"
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
            detail="CV not found 4."
        )

    # Remove CV from position
    position.update_cv(cv_id, is_add=False)

    # Delete CV
    cv.delete_cv()
