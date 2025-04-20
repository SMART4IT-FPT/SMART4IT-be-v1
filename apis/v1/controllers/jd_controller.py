import httpx
from typing import AnyStr
from pydantic import BaseModel
from fastapi import HTTPException, status, BackgroundTasks
from ..schemas.user_schema import UserSchema
from ..schemas.project_schema import ProjectSchema
from ..schemas.position_schema import PositionSchema
from ..schemas.jd_schema import JDSchema
from ..utils.extractor import get_jd_content
import logging
import os

from dotenv import load_dotenv
load_dotenv()

processing_api_url = os.environ.get("PROCESSING_API_URL")


def _validate_permission(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
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


def get_current_jd(project_id: AnyStr, position_id: AnyStr, user: UserSchema):
    _, position = _validate_permission(project_id, position_id, user)

    # Return null if no JD
    if not position.jd or position.jd == "":
        jd_instance = JDSchema().create_jd()

        # Update position
        position.update_jd(jd_instance.id)
        return jd_instance

    # Get JD
    jd = JDSchema.find_by_id(position.jd)
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="JD not found."
        )

    return jd


async def _analyse_jd_content(content: AnyStr, jd: JDSchema, position: PositionSchema, llm_name: str):
    # Define the AI service API endpoint and payload
    processing_payload = {
        "doc_ids": [jd.id],
        "doc_type": "jd",
        "llm_name": llm_name
    }

    # Call the AI service API
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(processing_api_url, json=processing_payload)

    # Check for successful response
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling AI service: {response.text}"
        )

    # Parse the response
    processing_result = response.json().get("results")
    summary = processing_result[0].get("summary")

    # Update JD extraction
    jd.update_summary(summary)


async def _upload_jd_content(content: AnyStr, position: PositionSchema, llm_name):
    # Get current JD
    jd_instance = JDSchema.find_by_id(position.jd)
    if not jd_instance:
        # Create instance
        jd_instance = JDSchema(
            content=content
        ).create_jd()
    else:
        # Update content
        jd_instance.update_content(content)

    # Update position
    if not position.jd or position.jd == "":
        position.update_jd(jd_instance.id)

    # Parse content
    content = get_jd_content(content)

    # Analyse JD content
    await _analyse_jd_content(content, jd_instance, position, llm_name)

    # Analyse JD content in the background
    # background_tasks.add_task(_analyse_jd_content, content, jd_instance, position)


async def update_current_jd(project_id: AnyStr, position_id: AnyStr, data: BaseModel, user: UserSchema, llm_name: str):
    # Validate permission
    _, position = _validate_permission(project_id, position_id, user)

    # Upload JD content
    if data.content == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JD content is required or not be empty."
        )

    await _upload_jd_content(data.content, position, llm_name)