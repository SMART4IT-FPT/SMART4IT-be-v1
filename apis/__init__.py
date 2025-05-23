from fastapi import APIRouter
from .v1.routes.auth import router as auth_router
from .v1.routes.user import router as user_router
from .v1.routes.project import router as project_router
from .v1.routes.position import router as position_router
from .v1.routes.cv import router as cv_router
from .v1.routes.jd import router as jd_router
# from .v1.routes.match import router as matching_router
from .v1.routes.utils import router as utils_router

api_v1_router = APIRouter(prefix="/v1")

# Register routes for the API
api_v1_router.include_router(auth_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(project_router)
api_v1_router.include_router(position_router)
api_v1_router.include_router(cv_router)
api_v1_router.include_router(jd_router)
# api_v1_router.include_router(matching_router)
api_v1_router.include_router(utils_router)
