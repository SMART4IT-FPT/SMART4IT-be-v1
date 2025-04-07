from ._cache_init import cacher
from .cache_provider import CacheProvider
from .jwt_provider import JWTProvider
from .db_provider import DatabaseProvider
from ..utils.constants import (
    USER_COLLECTION,
    PROJECT_COLLECTION,
    PROJECT_MEMBER_COLLECTION,
    POSITION_COLLECTION,
    JD_COLLECTION,
    CV_COLLECTION,
    JD_LABEL_COLLECTION,
    CV_LABEL_COLLECTION,
    CV_MATCHING_COLLECTION,
    CONFIG_COLLECTION,
    CV_STORAGE
)
from .storage_provider import StorageProvider


memory_cacher = CacheProvider(in_memory=True)
jwt = JWTProvider()
user_db = DatabaseProvider(collection_name=USER_COLLECTION)
project_db = DatabaseProvider(collection_name=PROJECT_COLLECTION)
project_member_db = DatabaseProvider(collection_name=PROJECT_MEMBER_COLLECTION)
position_db = DatabaseProvider(collection_name=POSITION_COLLECTION)
jd_db = DatabaseProvider(collection_name=JD_COLLECTION)
cv_db = DatabaseProvider(collection_name=CV_COLLECTION)
jd_label_db = DatabaseProvider(collection_name=JD_LABEL_COLLECTION)
cv_label_db = DatabaseProvider(collection_name=CV_LABEL_COLLECTION)
cv_matching_db = DatabaseProvider(collection_name=CV_MATCHING_COLLECTION)
config_db = DatabaseProvider(collection_name=CONFIG_COLLECTION)
storage_db = StorageProvider(directory=CV_STORAGE)
