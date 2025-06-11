from aiohttp_client_cache import FileBackend, RedisBackend
from dotenv import load_dotenv

from .config import CacheTypes, Config
from .logs import logger

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}

load_dotenv(override=True)

config = Config()

if config.USE_CACHE:
    match config.CACHE_TYPE:
        case CacheTypes.file:
            cache = FileBackend(use_temp=True, expire_after=43200)  # 12 hours
        case CacheTypes.redis:
            cache = RedisBackend(
                cache_name="wpd-aiohttp-cache",
                address=config.REDIS_CONNECTION_URL,
                expire_after=43200,  # 12 hours
            )
else:
    cache = None

logger.info(f"Using {cache=}")
