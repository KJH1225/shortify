"""Standard API response wrappers"""
from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """Standard success response wrapper

    Usage:
        return ApiResponse(data=video_response)
        return ApiResponse(data=videos_list, meta={"total": 10, "page": 1})
    """
    data: T
    meta: dict | None = None


class ApiError(BaseModel):
    """Standard error response

    Usage:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                code="INVALID_FILE_TYPE",
                message="Only video files are supported",
                details={"supported_types": ["mp4", "avi", "mov"]}
            ).model_dump()
        )
    """
    code: str
    message: str
    details: dict | None = None
