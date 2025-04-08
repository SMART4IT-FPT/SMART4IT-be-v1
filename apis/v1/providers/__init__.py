from ._cache_init import cacher
from .cache_provider import CacheProvider
from .jwt_provider import JWTProvider
from .db_provider import DatabaseProvider
from ..utils.constants import (
    USER_COLLECTION,
    PROJECT_COLLECTION,
    POSITION_COLLECTION,
    CV_COLLECTION,
    JD_COLLECTION,
    CV_STORAGE
)
from .storage_provider import StorageProvider


memory_cacher = CacheProvider(in_memory=True)
jwt = JWTProvider()
user_db = DatabaseProvider(collection_name=USER_COLLECTION)
project_db = DatabaseProvider(collection_name=PROJECT_COLLECTION)
position_db = DatabaseProvider(collection_name=POSITION_COLLECTION)
cv_db = DatabaseProvider(collection_name=CV_COLLECTION)
jd_db = DatabaseProvider(collection_name=JD_COLLECTION)
storage_db = StorageProvider(directory=CV_STORAGE)
