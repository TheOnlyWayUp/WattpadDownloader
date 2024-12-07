from __future__ import annotations
from typing import List, Optional, Tuple
from typing_extensions import TypedDict
import re
import json
import logging
import tempfile
import unicodedata
from io import BytesIO, StringIO
from os import environ
from enum import Enum
from base64 import b64encode
import backoff
import pdfkit
from eliot import to_file, start_action
from eliot.stdlib import EliotHandler
from dotenv import load_dotenv
from ebooklib import epub
from ebooklib.epub import EpubBook
from exiftool import ExifTool
from bs4 import BeautifulSoup
from pydantic import TypeAdapter, model_validator, field_validator
from pydantic_settings import BaseSettings
from aiohttp import ClientResponseError
from aiohttp_client_cache.session import CachedSession
from aiohttp_client_cache import FileBackend, RedisBackend

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

# --- Exceptions --- #


class WattpadError(Exception):
    """Base Exception class for Wattpad related errors."""


class StoryNotFoundError(WattpadError):
    """Display the "This story was not found" error to the user."""

    ...


class PartNotFoundError(StoryNotFoundError): ...


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
                body = await response.json()

                if response.status == 400:
                    match body.get("error_code"):
                        case 1020:  # "Story part not found"
                            logger.info(f"{part_id=} not found on Wattpad, returning.")
                            raise PartNotFoundError()

                response.raise_for_status()

        return str(body["groupId"]), story_ta.validate_python(body["group"])


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story(story_id: int, cookies: Optional[dict] = None) -> Story:
    """Taking a story_id, return its information from the Wattpad API."""
    with start_action(action_type="api_fetch_story", story_id=story_id):
        async with CachedSession(
            headers=headers, cookies=cookies, cache=None if cookies else cache
        ) as session:
            async with session.get(
                f"https://www.wattpad.com/api/v3/stories/{story_id}?fields=tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username),parts(id,title),cover"
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
async def fetch_part_content(part_id: int, cookies: Optional[dict] = None) -> str:
    """Return the HTML Content of a Part."""
    with start_action(action_type="api_fetch_partContent", part_id=part_id):
        async with CachedSession(
            headers=headers, cookies=cookies, cache=None if cookies else cache
        ) as session:
            async with session.get(
                f"https://www.wattpad.com/apiv2/?m=storytext&id={part_id}"
            ) as response:
                body = await response.text()

                if response.status == 400:
                    data = json.loads(body)
                    match data.get("code"):
                        case 463:  # ""Could not find any parts for that story""
                            logger.info(
                                f"{part_id=} for text not found on Wattpad, returning."
                            )
                            raise PartNotFoundError()

                response.raise_for_status()

        return body


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


class EPUBGenerator:
    def __init__(self, data: Story, cover: bytes):
        self.epub = epub.EpubBook()
        self.data = data
        self.cover = cover

        # set metadata
        self.epub.add_author(data["user"]["username"])

        self.epub.add_metadata("DC", "title", data["title"])
        self.epub.add_metadata("DC", "description", data["description"])
        self.epub.add_metadata("DC", "date", data["createDate"])
        self.epub.add_metadata("DC", "modified", data["modifyDate"])
        self.epub.add_metadata("DC", "language", data["language"]["name"])

        self.epub.add_metadata(
            None, "meta", "", {"name": "tags", "content": ", ".join(data["tags"])}
        )
        self.epub.add_metadata(
            None, "meta", "", {"name": "mature", "content": str(int(data["mature"]))}
        )
        self.epub.add_metadata(
            None,
            "meta",
            "",
            {"name": "completed", "content": str(int(data["completed"]))},
        )

        # Set book cover
        self.epub.set_cover("cover.jpg", cover)
        cover_chapter = epub.EpubHtml(
            file_name="titlepage.xhtml",  # Standard for cover page
        )
        cover_chapter.set_content('<img src="cover.jpg">')
        self.epub.add_item(cover_chapter)

    async def add_chapters(self, contents: List[str], download_images: bool = False):
        chapters = []

        for cidx, (part, content) in enumerate(zip(self.data["parts"], contents)):
            title = part["title"]

            # Thanks https://eu17.proxysite.com/process.php?d=5VyWYcoQl%2BVF0BYOuOavtvjOloFUZz2BJ%2Fepiusk6Nz7PV%2B9i8rs7cFviGftrBNll%2B0a3qO7UiDkTt4qwCa0fDES&b=1
            chapter = epub.EpubHtml(
                title=title,
                file_name=f"{cidx}.xhtml",  # Used to be clean_title.xhtml, but that broke Arabic support as slugify turns arabic strings into '', leading to multiple files with the same name, breaking those chapters.
                lang=self.data["language"]["name"],
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
                            self.epub.add_item(img)
                            # Fetch image and pack

                            content = content.replace(
                                str(image["src"]), f"static/{cidx}/{idx}.jpeg"
                            )

            chapter.set_content(content)

            chapters.append(chapter)

            yield title  # Yield the chapter's title upon insertion preceeded by retrieval.

        for chapter in chapters:
            self.epub.add_item(chapter)

        self.epub.toc = chapters

        # Thanks https://github.com/aerkalov/ebooklib/blob/master/samples/09_create_image/create.py
        self.epub.add_item(epub.EpubNcx())
        self.epub.add_item(epub.EpubNav())

        # create spine
        self.epub.spine = ["nav"] + chapters

    def dump(self) -> tempfile._TemporaryFileWrapper[bytes]:
        # Thanks https://stackoverflow.com/a/75398222
        temp_file = tempfile.NamedTemporaryFile(suffix=".epub", delete=True)
        epub.write_epub(temp_file, self.epub)

        temp_file.file.seek(0)

        return temp_file


class PDFGenerator:
    def __init__(self, data: Story, cover: bytes):
        self.data = data
        self.file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=True)
        self.cover = cover
        # self.canvas = Canvas(self.file)

    async def add_chapters(self, contents: List[str], download_images: bool = False):
        chapters = []

        for part, content in zip(self.data["parts"], contents):
            html = BeautifulSoup(content, features="lxml")

            image_sources: List[str] = []
            for image_container in html.find_all("p", {"data-media-type": "image"}):
                img = image_container.findChild("img")
                source = img.get("src")
                image_container.replace_with(img)
                image_sources.append(source)

            writable_html = str(html)
            if download_images:
                async with CachedSession(cache=None) as session:  # Don't cache images
                    for image_url in image_sources:
                        async with session.get(image_url) as response:
                            response.raise_for_status()

                            image = await response.read()
                            # temp_img = tempfile.NamedTemporaryFile(
                            #     suffix=".jpg", delete=False
                            # )
                            # temp_img.write(image)

                            writable_html = writable_html.replace(
                                image_url,
                                f"data:image/jpg;base64,{b64encode(image).decode()}",
                            )
                            print("Replaced", image_url, "with bytes")

            tempie = tempfile.NamedTemporaryFile(suffix=".html", delete=True)
            tempie.write(writable_html.encode())
            # print(writable_html)

            chapters.append(tempie)

            yield part["title"]

        cover_file = tempfile.NamedTemporaryFile(suffix=".html")
        cover_file.write(
            f'<html><body><img width="993" height="1404" src="data:image/jpg;base64,{b64encode(self.cover).decode()}"></img></body></html>'.encode()
        )

        pdfkit.from_file(
            [chapter.file.name for chapter in chapters],
            self.file.name,
            cover=cover_file.file.name,
            toc={"toc-header-text": "Table of Contents"},
            options={
                "images" if download_images else "no-images": ""
                # "margin-top": "-10mm",
                # "margin-left": "-10mm",
                # "margin-right": "0mm",
                # "margin-bottom": "0mm",
                # "dump-default-toc-xsl": "",
                # "dump-outline": "",
            },
            cover_first=True,
        )

        clean_description = self.data["description"].strip().replace("\n", "$/")
        metadata = {
            "Author": self.data["user"]["username"],
            "Title": self.data["title"],
            "Subject": clean_description,
            "CreationDate": self.data["createDate"],
            "ModDate": self.data["modifyDate"],
            "Keywords": ",".join(self.data["tags"]),
            "Language": self.data["language"]["name"],
            "Completed": self.data["completed"],
            "MatureContent": self.data["mature"],
            "Producer": "Dhanush Rambhatla (TheOnlyWayUp - https://rambhat.la) and WattpadDownloader",
        }  # As per https://exiftool.org/TagNames/PDF.html
        with ExifTool(config_file="../exiftool.config", logger=logger) as et:
            et.execute(
                *(
                    [f"-{key}={value}" for key, value in metadata.items()]
                    + [
                        "-overwrite_original",
                        self.file.file.name,
                    ]
                )
            )

    def dump(self) -> PDFGenerator:
        self.file.seek(0)

        return self
