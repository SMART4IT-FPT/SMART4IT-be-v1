from typing import List
import datetime
from fastapi import HTTPException, status
from langchain.pydantic_v1 import Field, create_model
# from ..schemas.criteria_schema import CriteriaSchema
from ..utils.constants import ALLOWED_EXTENSIONS


def get_current_time() -> str:
    '''
    Get the current time in the string format.
    '''
    return datetime.datetime.now().isoformat()


def validate_file_extension(file_name: str, allowed_extensions: List[str] = ALLOWED_EXTENSIONS):
    '''
    Validate the file extension.
    '''
    if not file_name.lower().endswith(tuple(allowed_extensions)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension not allowed. Allowed extensions are {', '.join(allowed_extensions)}"
        )


def get_content_type(file_name: str):
    '''
    Get the content type of the file.
    '''
    if file_name.lower().endswith(".pdf"):
        return "application/pdf"
    elif file_name.lower().endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif file_name.lower().endswith(".doc"):
        return "application/msword"
    elif file_name.lower().endswith(".txt"):
        return "text/plain"
    else:
        return "application/octet-stream"
