from enum import Enum
from pydantic import model_validator, field_validator
from pydantic_settings import BaseSettings


class CacheTypes(Enum):
    file = "file"
    redis = "redis"


class Config(BaseSettings):
    # Values can be overriden by envvars.

    USE_CACHE: bool = True
    CACHE_TYPE: CacheTypes = CacheTypes.file
    REDIS_CONNECTION_URL: str = ""

    @field_validator("USE_CACHE", mode="before")
    def validate_use_cache(cls, value):
        # Return default if value is an empty string
        if value == "":
            return True  # Default value for USE_CACHE
        return value

    @field_validator("CACHE_TYPE", mode="before")
    def validate_cache_type(cls, value):
        # Thanks https://stackoverflow.com/a/78157474
        if value == "":
            return "file"
        return value

    @model_validator(mode="after")
    def prevent_mismatched_redis_url(self):
        match self.CACHE_TYPE:
            case CacheTypes.file:
                if self.REDIS_CONNECTION_URL:
                    raise ValueError(
                        "REDIS_CONNECTION_URL provided when File cache selected. To use Redis as a cache, set CACHE_TYPE=redis."
                    )
            case CacheTypes.redis:
                if not self.REDIS_CONNECTION_URL:
                    raise ValueError(
                        "REDIS_CONNECTION_URL not provided when Redis cache selected. To use File cache, set CACHE_TYPE=file."
                    )
        return self
