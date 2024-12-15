from typing import List, Optional, Tuple
from typing_extensions import TypedDict
import re
import unicodedata
import logging
from os import environ
from enum import Enum
import backoff
from eliot import to_file, start_action
from eliot.stdlib import EliotHandler
from dotenv import load_dotenv
from ebooklib import epub
from ebooklib.epub import EpubBook
from bs4 import BeautifulSoup
from pydantic import TypeAdapter, model_validator, field_validator
from pydantic_settings import BaseSettings
from aiohttp import ClientResponseError
from aiohttp_client_cache.session import CachedSession
from aiohttp_client_cache import FileBackend, RedisBackend
from io import BytesIO
from zipfile import ZipFile

load_dotenv(override=True)

handler = EliotHandler()
logging.getLogger("fastapi").setLevel(logging.INFO)
logging.getLogger("fastapi").addHandler(handler)

if environ.get("DEBUG"):
    to_file(open("eliot.log", "wb"))

logger = logging.Logger("wpd")
logger.addHandler(handler)

# --- #


class CacheTypes(Enum):
    file = "file"
    redis = "redis"


class Config(BaseSettings):
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


config = Config()

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

# --- Utilities --- #


def slugify(value, allow_unicode=False) -> str:
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.

    Thanks https://stackoverflow.com/a/295466.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


async def wp_get_cookies(username: str, password: str) -> dict:
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


# --- Models --- #


class Language(TypedDict):
    name: str


class User(TypedDict):
    username: str


class Part(TypedDict):
    id: int
    title: str


class Story(TypedDict):
    id: str
    title: str
    createDate: str
    modifyDate: str
    language: Language
    user: User
    description: str
    cover: str
    completed: bool
    tags: List[str]
    mature: bool
    url: str
    parts: List[Part]
    isPaywalled: bool


story_ta = TypeAdapter(Story)

# --- API Calls --- #


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story_from_partId(
    part_id: int, cookies: Optional[dict] = None
) -> Tuple[str, Story]:
    """Return a Story ID from a Part ID."""
    with start_action(action_type="api_fetch_storyFromPartId"):
        async with CachedSession(
            headers=headers, cache=None if cookies else cache
        ) as session:  # Don't cache requests with Cookies.
            async with session.get(
                f"https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=groupId,group(tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username),parts(id,title),cover)"
            ) as response:
                response.raise_for_status()

                body = await response.json()

        return str(body["groupId"]), story_ta.validate_python(body["group"])


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def retrieve_story(story_id: int, cookies: Optional[dict] = None) -> Story:
    """Taking a story_id, return its information from the Wattpad API."""
    with start_action(action_type="api_fetch_story", story_id=story_id):
        async with CachedSession(
            headers=headers, cookies=cookies, cache=None if cookies else cache
        ) as session:
            async with session.get(
                f"https://www.wattpad.com/api/v3/stories/{story_id}?fields=tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username),parts(id,title),cover"
            ) as response:
                response.raise_for_status()

                body = await response.json()

        return story_ta.validate_python(body)


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_part_content(part_id: int, cookies: Optional[dict] = None) -> str:
    """Return the HTML Content of a Part."""
    with start_action(action_type="api_fetch_partContent", part_id=part_id):
        async with CachedSession(
            headers=headers, cookies=cookies, cache=None if cookies else cache
        ) as session:
            async with session.get(
                f"https://www.wattpad.com/apiv2/?m=storytext&id={part_id}"
            ) as response:
                response.raise_for_status()

                body = await response.text()

        return body


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story_zip(story_id: int, cookies: Optional[dict] = None) -> BytesIO:
    """Return a BytesIO stream of a .zip file containing each part's HTML content."""
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

                bytes_object = await response.read()
                bytes_stream = BytesIO(bytes_object)

        return bytes_stream


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_cover(url: str) -> bytes:
    """Fetch cover image bytes."""
    with start_action(action_type="api_fetch_cover", url=url):
        async with CachedSession(
            headers=headers, cache=None
        ) as session:  # Don't cache images.
            async with session.get(url) as response:
                response.raise_for_status()

                body = await response.read()

        return body


# --- EPUB Generation --- #


def set_metadata(book: EpubBook, data: Story) -> None:
    """Set book metadata."""
    book.add_author(data["user"]["username"])

    book.add_metadata("DC", "title", data["title"])
    book.add_metadata("DC", "description", data["description"])
    book.add_metadata("DC", "date", data["createDate"])
    book.add_metadata("DC", "modified", data["modifyDate"])
    book.add_metadata("DC", "language", data["language"]["name"])

    book.add_metadata(
        None, "meta", "", {"name": "tags", "content": ", ".join(data["tags"])}
    )
    book.add_metadata(
        None, "meta", "", {"name": "mature", "content": str(int(data["mature"]))}
    )
    book.add_metadata(
        None, "meta", "", {"name": "completed", "content": str(int(data["completed"]))}
    )


async def set_cover(book: EpubBook, data: Story) -> None:
    """Set book cover."""
    book.set_cover("cover.jpg", await fetch_cover(data["cover"]))
    chapter = epub.EpubHtml(
        file_name="titlepage.xhtml",  # Standard for cover page
    )
    chapter.set_content('<img src="cover.jpg">')


async def add_chapters(
    book: EpubBook,
    data: Story,
    download_images: bool = False,
    cookies: Optional[dict] = None,
):
    chapters = []

    story_zip = await fetch_story_zip(data["id"], cookies)
    archive = ZipFile(story_zip, "r")

    for cidx, part in enumerate(data["parts"]):
        content = archive.read(str(part["id"])).decode("utf-8")
        title = part["title"]

        # Thanks https://eu17.proxysite.com/process.php?d=5VyWYcoQl%2BVF0BYOuOavtvjOloFUZz2BJ%2Fepiusk6Nz7PV%2B9i8rs7cFviGftrBNll%2B0a3qO7UiDkTt4qwCa0fDES&b=1
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"{cidx}.xhtml",  # Used to be clean_title.xhtml, but that broke Arabic support as slugify turns arabic strings into '', leading to multiple files with the same name, breaking those chapters.
            lang=data["language"]["name"],
        )

        if download_images:
            soup = BeautifulSoup(content, "lxml")

            async with CachedSession(
                headers=headers, cache=None
            ) as session:  # Don't cache images.
                for idx, image in enumerate(soup.find_all("img")):
                    if not image["src"]:
                        continue
                    # Find all image tags and filter for those with sources

                    async with session.get(image["src"]) as response:
                        img = epub.EpubImage(
                            media_type="image/jpeg",
                            content=await response.read(),
                            file_name=f"static/{cidx}/{idx}.jpeg",
                        )
                        book.add_item(img)
                        # Fetch image and pack

                        content = content.replace(
                            str(image["src"]), f"static/{cidx}/{idx}.jpeg"
                        )

        chapter.set_content(f"<h1>{title}</h1>" + content)

        chapters.append(chapter)

        yield title  # Yield the chapter's title upon insertion preceeded by retrieval.

    for chapter in chapters:
        book.add_item(chapter)

    book.toc = chapters

    # Thanks https://github.com/aerkalov/ebooklib/blob/master/samples/09_create_image/create.py
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # create spine
    book.spine = ["nav"] + chapters
