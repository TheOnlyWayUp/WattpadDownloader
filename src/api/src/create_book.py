from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from typing_extensions import TypedDict
import re
import json
import logging
import tempfile
import unicodedata
from os import environ
from enum import Enum
from base64 import b64encode
import backoff
import pdfkit
from ebooklib import epub
from exiftool import ExifTool
from eliot import to_file, start_action
from eliot.stdlib import EliotHandler
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import TypeAdapter, model_validator, field_validator
from pydantic_settings import BaseSettings
from aiohttp import ClientResponseError
from aiohttp_client_cache.session import CachedSession
from aiohttp_client_cache import FileBackend, RedisBackend

load_dotenv(override=True)

handler = EliotHandler()

logging.getLogger("fastapi").setLevel(logging.INFO)
logging.getLogger("fastapi").addHandler(handler)

exiftool_logger = logging.getLogger("exiftool")
exiftool_logger.addHandler(handler)

logger = logging.Logger("wpd")
logger.addHandler(handler)

if environ.get("DEBUG"):
    to_file(open("eliot.log", "wb"))


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


def smart_trim(text: str, max_length: int = 400) -> str:
    """Truncate a string intelligently at newlines. Coherence and max-length adherence."""
    chunks = [t for t in text.split("\n") if t]

    to_return = ""
    for chunk in chunks:
        if len(to_return) + len(chunk) < max_length:
            to_return = chunk + "<br />"
        else:
            to_return = to_return.rstrip("<br />")
            break

    return to_return


def clean_part_text(text: str) -> str:
    """Remove unnecessary newlines from Text"""
    soup = BeautifulSoup(text, "lxml")

    for br in soup.find_all("br"):
        # Check if no content after br
        if not br.next_sibling or br.next_sibling.name in ["br", None]:
            br.decompose()

    return str(soup)


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


class CopyrightData(TypedDict):
    name: str
    statement: str
    freedoms: str
    printing: str
    image_url: Optional[str]


class Language(TypedDict):
    name: str


class User(TypedDict):
    username: str
    avatar: str
    description: str


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
    copyright: int


story_ta = TypeAdapter(Story)

# --- PDF Dependencies --- #

wp_copyright_data: Dict[int, CopyrightData] = {
    1: {
        "name": "All Rights Reserved",
        "statement": "©️ {published_year} by {username}. All Rights Reserved.",
        "freedoms": "No reuse, redistribution, or modification without permission.",
        "printing": "Not allowed without explicit permission.",
        "image_url": None,
    },
    2: {
        "name": "Public Domain",
        "statement": "This work is in the public domain. Originally published in {published_year} by {username}.",
        "freedoms": "Free to use for any purpose without permission.",
        "printing": "Allowed for personal or commercial purposes.",
        "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/cc-zero.png",
    },
    3: {
        "name": "Creative Commons Attribution (CC-BY)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution 4.0 International License.",
        "freedoms": "Allows reuse, redistribution, and modification with credit to the author.",
        "printing": "Allowed with proper credit.",
        "image_url": "https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by.png",
    },
    4: {
        "name": "CC Attribution NonCommercial (CC-BY-NC)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License.",
        "freedoms": "Allows reuse and modification for non-commercial purposes with credit.",
        "printing": "Allowed for non-commercial purposes with proper credit.",
        "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc.png",
    },
    5: {
        "name": "CC Attribution NonCommercial NoDerivs (CC-BY-NC-ND)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial-NoDerivs 4.0 International License.",
        "freedoms": "Allows sharing in original form for non-commercial purposes with credit; no modifications allowed.",
        "printing": "Allowed for non-commercial purposes in original form with proper credit.",
        "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc-nd.png",
    },
    6: {
        "name": "CC Attribution NonCommercial ShareAlike (CC-BY-NC-SA)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.",
        "freedoms": "Allows reuse and modification for non-commercial purposes under the same license, with credit.",
        "printing": "Allowed for non-commercial purposes with proper credit under the same license.",
        "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc-sa.png",
    },
    7: {
        "name": "CC Attribution ShareAlike (CC-BY-SA)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License.",
        "freedoms": "Allows reuse and modification for any purpose under the same license, with credit.",
        "printing": "Allowed with proper credit under the same license.",
        "image_url": "https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-sa.png",
    },
    8: {
        "name": "CC Attribution NoDerivs (CC-BY-ND)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NoDerivs 4.0 International License.",
        "freedoms": "Allows sharing in original form for any purpose with credit; no modifications allowed.",
        "printing": "Allowed in original form with proper credit.",
        "image_url": "https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nd.png",
    },
}


with open("./pdf/cover_and_copyright.html") as reader:
    copyright_template = reader.read()
with open("./pdf/author.html") as reader:
    author_template = reader.read()

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
                f"https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=groupId,group(tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username,avatar,description),parts(id,title),cover,copyright)"
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


# --- Generation --- #


class EPUBGenerator:
    """EPUB Generation utilities"""

    def __init__(self, data: Story, cover: bytes):
        """Initialize EPUBGenerator. Create epub.EpubBook() and set metadata and cover."""
        self.epub = epub.EpubBook()
        self.data = data
        self.cover = cover

        # set metadata, defined in https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#section-2
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

        # Set cover
        self.epub.set_cover("cover.jpg", cover)
        cover_chapter = epub.EpubHtml(
            file_name="titlepage.xhtml",  # Standard for cover page
        )
        cover_chapter.set_content('<img src="cover.jpg">')
        self.epub.add_item(cover_chapter)

    async def add_chapters(self, contents: List[str], download_images: bool = False):
        """Add chapters to the Epub, downloading images if necessary. Sets the table of contents and spine."""
        chapters: List[epub.EpubHtml] = []

        for cidx, (part, content) in enumerate(zip(self.data["parts"], contents)):
            title = part["title"]

            # Thanks https://eu17.proxysite.com/process.php?d=5VyWYcoQl%2BVF0BYOuOavtvjOloFUZz2BJ%2Fepiusk6Nz7PV%2B9i8rs7cFviGftrBNll%2B0a3qO7UiDkTt4qwCa0fDES&b=1
            chapter = epub.EpubHtml(
                title=title,
                file_name=f"{cidx}_{part['id']}.xhtml",  # See issue #30
                lang=self.data["language"]["name"],
                uid=str(part["id"]).encode(),
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
            self.epub.add_item(chapter)

            chapters.append(chapter)

            yield title

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

        temp_file.seek(0)

        return temp_file


class PDFGenerator:
    """PDF Generation utilities"""

    def __init__(self, data: Story, cover: bytes):
        """Initialize PDGenerator, create PDF Temporary file."""
        self.data = data
        self.file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=True)
        self.cover = cover

    async def genernate_cover_and_copyright_file(
        self,
    ) -> tempfile._TemporaryFileWrapper:
        """Generate Cover and Copyright file, fetch copyright image (cached), use self.cover for cover."""

        copyright_data = wp_copyright_data[self.data["copyright"]]
        about_copyright = (
            copyright_template.replace(
                "{statement}",
                copyright_data["statement"].format(
                    username=self.data["user"]["username"],
                    published_year=self.data["createDate"].split("-", 2)[0],
                ),
            )
            .replace("{freedoms}", copyright_data["freedoms"])
            .replace(
                "{printing}",
                copyright_data["printing"],
            )
            .replace("{book_id}", self.data["id"])
            .replace("{book_title}", self.data["title"])
        )

        copyright_image = (
            await fetch_image(copyright_data["image_url"], should_cache=True)
            if copyright_data["image_url"]
            else None
        )
        image_block = (
            """<img src="{image_url}" 
alt="{name}" 
width="88" 
height="31" 
style="margin-bottom: 1rem;">""".format(
                image_url=f"data:image/jpg;base64,{b64encode(copyright_image).decode()}",
                name=copyright_data["name"],
            )
            if copyright_image
            else ""
        )
        about_copyright = (
            about_copyright.replace(
                "{copyright_image}",
                image_block,
            )
            if image_block
            else about_copyright.replace("{copyright_image}", "")
        )
        about_copyright = about_copyright.replace(
            "{cover}", f"data:image/jpg;base64,{b64encode(self.cover).decode()}"
        )

        cover_and_copyright_file = tempfile.NamedTemporaryFile(
            suffix=".html", delete=True
        )
        cover_and_copyright_file.write(about_copyright.encode())
        cover_and_copyright_file.seek(0)

        return cover_and_copyright_file

    async def generate_about_author_file(self) -> tempfile._TemporaryFileWrapper:
        """Generate About the Author file, fetch avatar."""
        author_avatar = (
            await fetch_image(
                self.data["user"]["avatar"].replace("128", "512")
            )  # Increase image resolution
            if self.data["user"]["avatar"]
            else None
        )
        about_author = author_template.replace(
            "{username}", self.data["user"]["username"]
        ).replace("{description}", smart_trim(self.data["user"]["description"]))

        about_author = (
            about_author.replace(
                "{avatar}",
                f"""
                <img src="data:image/jpg;base64,{b64encode(author_avatar).decode()}" alt="Author's profile picture" id="author-profile-picture">""",
            )
            if author_avatar
            else about_author.replace("{avatar}", "")
        )
        about_author_file = tempfile.NamedTemporaryFile(suffix=".html", delete=True)
        about_author_file.write(about_author.encode())
        about_author_file.seek(0)

        return about_author_file

    async def add_chapters(self, contents: List[str], download_images: bool = False):
        """Add chapters to the PDF, downloading images if necessary. Also add Cover, Copyright, and About the Author pages."""

        chapters: List[tempfile._TemporaryFileWrapper] = []

        for part, content in zip(self.data["parts"], contents):
            html = BeautifulSoup(content, features="lxml")
            image_sources: List[str] = []

            for image_container in html.find_all("p", {"data-media-type": "image"}):
                # Find all images, download them if download_images, else clear them (else wkhtmltopdf _might_ fetch them)
                img = image_container.findChild("img")
                source = img.get("src")
                if not download_images and source:
                    img["src"] = ""
                image_container.replace_with(img)
                image_sources.append(source)

            writable_html = str(html)
            if download_images:
                async with CachedSession(cache=None) as session:  # Don't cache images
                    for image_url in image_sources:
                        async with session.get(image_url) as response:
                            response.raise_for_status()

                            image = await response.read()

                            writable_html = writable_html.replace(
                                image_url,
                                f"data:image/jpg;base64,{b64encode(image).decode()}",
                            )  # Base64-encoded images are better than referencing NamedTemporaryFiles as it's less access to the local filesystem, the enable-local-file-access would be disabled if not for local fonts.

            tempie = tempfile.NamedTemporaryFile(
                suffix=".html", delete=True
            )  # tempie 🫡
            tempie.write(writable_html.encode())
            tempie.file.seek(0)

            chapters.append(tempie)

            yield part["title"]

        # Cover and Copyright Page
        cover_and_copyright_file = await self.genernate_cover_and_copyright_file()

        # About the Author page
        about_author_file = await self.generate_about_author_file()
        chapters.append(about_author_file)

        chapter_filenames = [chapter.file.name for chapter in chapters]

        with start_action(
            action_type="generate_pdf",
            chapter_filenames=chapter_filenames,
            output_filename=self.file.name,
            cover_filename=cover_and_copyright_file.file.name,
            title=self.data["title"],
        ):
            # PDF Generation with wkhtmltopdf, written to self.file

            pdfkit.from_file(
                chapter_filenames,
                self.file.name,
                cover=cover_and_copyright_file.file.name,
                toc={
                    "toc-header-text": "Table of Contents",
                    "xsl-style-sheet": "./pdf/toc.xsl",
                },
                options={
                    "footer-html": "./pdf/footer.html",
                    "margin-top": "10mm",
                    "margin-bottom": "10mm",
                    "title": self.data["title"],
                    "encoding": "UTF-8",
                    "user-style-sheet": "./pdf/stylesheet.css",
                    "enable-local-file-access": "",
                },
                cover_first=True,
            )

        with start_action(action_type="add_metadata") as action:
            # Metadata generation with Exiftool
            clean_description = (
                self.data["description"].strip().replace("\n", "$/")
            )  # exiftool doesn't parse \ns correctly, they support $/ for the same instead. `&#xa;` is another option.

            action.log(f"clean_description: {clean_description}")

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

            action.log(f"options: {metadata}")

            with ExifTool(
                config_file="../exiftool.config", logger=exiftool_logger
            ) as et:
                # Custom configuration adds Completed and MatureContent tags.
                # exiftool logger logs executed command
                et.execute(
                    *(
                        [f"-{key}={value}" for key, value in metadata.items()]
                        + [
                            "-overwrite_original",
                            self.file.file.name,
                        ]
                    )
                )

        # Close files and delete them from tmp
        for chapter in chapters:
            chapter.file.close()

    def dump(self) -> PDFGenerator:
        self.file.seek(0)

        return self


# ------ #
