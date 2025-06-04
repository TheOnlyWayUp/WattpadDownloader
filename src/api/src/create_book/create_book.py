from __future__ import annotations
from typing import Optional, Tuple
from io import BytesIO
import backoff
from pydantic import TypeAdapter
from .config import Config, CacheTypes
from .logs import logger
from eliot import start_action
from dotenv import load_dotenv
from aiohttp import ClientResponseError
from aiohttp_client_cache.session import CachedSession
from aiohttp_client_cache import FileBackend, RedisBackend
from .models import Story
from .exceptions import PartNotFoundError, StoryNotFoundError

load_dotenv(override=True)

config = Config()
story_ta = TypeAdapter(Story)

# --- #

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}

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


async def fetch_cookies(username: str, password: str) -> dict:
    # source: https://github.com/TheOnlyWayUp/WP-DM-Export/blob/dd4c7c51cb43f2108e0f63fc10a66cd24a740e4e/src/API/src/main.py#L25-L58
    """Retrieves authorization cookies from Wattpad by logging in with user creds.

    Args:
        username (str): Username.
        password (str): Password.

    Raises:
        ValueError: Bad status code.
        ValueError: No cookies returned.

    Returns:
        dict: Authorization cookies.
    """
    with start_action(action_type="api_fetch_cookies"):
        async with CachedSession(headers=headers, cache=None) as session:
            async with session.post(
                "https://www.wattpad.com/auth/login?nextUrl=%2F&_data=routes%2Fauth.login",
                data={
                    "username": username.lower(),
                    "password": password,
                },  # the username.lower() is for caching
            ) as response:
                if response.status != 204:
                    raise ValueError("Not a 204.")

                cookies = {
                    k: v.value
                    for k, v in response.cookies.items()  # Thanks https://stackoverflow.com/a/32281245
                }

                if not cookies:
                    raise ValueError("No cookies.")

                return cookies


# --- API Calls --- #


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story_from_partId(
    part_id: int, cookies: Optional[dict] = None
) -> Tuple[int, Story]:
    """Fetch Story metadata from a Part ID."""
    with start_action(action_type="api_fetch_storyFromPartId"):
        async with CachedSession(
            headers=headers, cache=None if cookies else cache
        ) as session:  # Don't cache requests with Cookies.
            async with session.get(
                f"https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=groupId,group(tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username,avatar,description),parts(id,title),cover,copyright)"
            ) as response:
                body = await response.json()

                if response.status == 400:
                    match body.get("error_code"):
                        case 1020:  # "Story part not found"
                            logger.info(f"{part_id=} not found on Wattpad, returning.")
                            raise PartNotFoundError()

                response.raise_for_status()

        return int(body["groupId"]), story_ta.validate_python(body["group"])


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story(story_id: int, cookies: Optional[dict] = None) -> Story:
    """Fetch Story metadata from a Story ID."""
    with start_action(action_type="api_fetch_story", story_id=story_id):
        async with CachedSession(
            headers=headers, cookies=cookies, cache=None if cookies else cache
        ) as session:
            async with session.get(
                f"https://www.wattpad.com/api/v3/stories/{story_id}?fields=tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username,avatar,description),parts(id,title),cover,copyright"
            ) as response:
                body = await response.json()

                if response.status == 400:
                    match body.get("error_code"):
                        case 1017:  # "Story not found"
                            logger.info(f"{story_id=} not found on Wattpad, returning.")
                            raise StoryNotFoundError()

                response.raise_for_status()

        return story_ta.validate_python(body)


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story_content_zip(
    story_id: int, cookies: Optional[dict] = None
) -> BytesIO:
    """BytesIO Stream of an Archive of Part Contents for a Story."""
    with start_action(action_type="api_fetch_storyZip", story_id=story_id):
        async with CachedSession(
            headers=headers,
            cookies=cookies,
            cache=None if cookies else cache,
        ) as session:
            async with session.get(
                f"https://www.wattpad.com/apiv2/?m=storytext&group_id={story_id}&output=zip"
            ) as response:
                response.raise_for_status()

                bytes_stream = BytesIO(await response.read())

        return bytes_stream


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_image(url: str, should_cache: bool = False) -> bytes:
    """Fetch image bytes."""
    with start_action(action_type="api_fetch_image", url=url):
        async with CachedSession(
            headers=headers, cache=cache if should_cache else None
        ) as session:  # Don't cache images.
            async with session.get(url) as response:
                response.raise_for_status()

                body = await response.read()

        return body
