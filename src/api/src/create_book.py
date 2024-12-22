from __future__ import annotations
from typing import List, Optional, Tuple, cast
from typing_extensions import TypedDict
import re
import logging
import tempfile
import unicodedata
from os import environ
from io import BytesIO
from enum import Enum
from base64 import b64encode
import bs4
import backoff
from weasyprint import HTML, CSS, default_url_fetcher
from weasyprint.text.fonts import FontConfiguration
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


def generate_clean_part_html(part: Part, content: str) -> bs4.Tag:
    chapter_title = part["title"]
    chapter_id = part["id"]

    clean = BeautifulSoup(
        f"""
    <section id="section_{chapter_id}" class="chapitre">
        <h1 id="{chapter_id}" class="chapter-title">{chapter_title}</h1>
    </section>
    """,
        "html.parser",
    )  # html.parser doesn't create <html>/<body> tags automatically

    html = BeautifulSoup(content, "lxml")
    for br in html.find_all("br"):
        # Check if no content after br
        if not br.next_sibling or br.next_sibling.name in ["br", None]:
            br.decompose()

    section = cast(bs4.Tag, clean.find("section"))
    if not section:
        raise Exception()

    for child in html.find_all("p"):
        for p_child in list(child.children):
            if not p_child:
                continue
            if isinstance(p_child, bs4.element.Tag):
                if p_child.name == "br":
                    p_child.decompose()
                elif p_child.name == "img":
                    src = p_child["src"]
                    img_tag = clean.new_tag("img")
                    img_tag["src"] = src
                    break_tag = clean.new_tag("br")
                    section.append(img_tag)
                    section.append(break_tag)
                elif p_child.name == "b":
                    content = p_child.text
                    p_tag = clean.new_tag("p")
                    bold_tag = clean.new_tag("b")
                    bold_content = clean.new_string(content)

                    bold_tag.append(bold_content)
                    p_tag.append(bold_tag)

                    section.append(p_tag)

                elif p_child.name == "i":
                    content = p_child.text
                    p_tag = clean.new_tag("p")
                    italic_tag = clean.new_tag("i")
                    italic_content = clean.new_string(content)

                    italic_tag.append(italic_content)
                    p_tag.append(italic_tag)

                    section.append(p_tag)

            elif isinstance(p_child, bs4.element.NavigableString):
                content = p_child.text
                p_tag = clean.new_tag("p")
                p_content = clean.new_string(content)
                p_tag.append(p_content)
                section.append(p_tag)

        if not list(child.children):
            # Some p tags only contain brs, once brs are removed, they are empty and can be removed as well.
            child.decompose()

    return section


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
) -> Tuple[int, Story]:
    """Fetch Story ID from Part ID."""
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
    """Fetch Story metadata using a Story ID."""
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

    async def add_chapters(
        self, contents: List[bs4.Tag], download_images: bool = False
    ):
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

            str_content = content.prettify()
            if download_images:
                soup = content

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

                            str_content = str_content.replace(
                                str(image["src"]), f"static/{cidx}/{idx}.jpeg"
                            )

            chapter.set_content(str_content)
            self.epub.add_item(chapter)

            chapters.append(chapter)

            yield title

        self.epub.toc = chapters

        # Thanks https://github.com/aerkalov/ebooklib/blob/master/samples/09_create_image/create.py
        self.epub.add_item(epub.EpubNcx())
        self.epub.add_item(epub.EpubNav())

        # create spine
        self.epub.spine = ["nav"] + chapters

    def dump(self) -> BytesIO:
        # Thanks https://stackoverflow.com/a/75398222
        buffer = BytesIO()
        epub.write_epub(buffer, self.epub)

        buffer.seek(0)

        return buffer


class PDFGenerator:
    """PDF Generation utilities"""

    def __init__(self, data: Story, cover: bytes):
        """Initialize PDGenerator, create PDF Temporary file."""
        self.data = data
        self.file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=True)
        self.cover = cover
        self.content: str = ""
        self.copyright = {
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

        with open("./pdf/stylesheet.css") as reader:
            self.stylesheet = reader.read()
        with open("./pdf/book.html") as reader:
            self.template = reader.read()

    async def generate_cover_and_copyright_html(
        self,
    ) -> str:
        """Generate Cover and Copyright file, fetch copyright image (cached), use self.cover for cover."""

        copyright_data = self.copyright[self.data["copyright"]]

        template = self.template
        about_copyright = (
            template.replace(
                "{statement}",
                copyright_data["statement"].format(
                    username=self.data["user"]["username"],
                    published_year=self.data["createDate"].split("-", 2)[0],
                ),
            )
            .replace("{author}", self.data["user"]["username"])
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
id="copyright-license-image">""".format(
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

        self.template = about_copyright
        return about_copyright

    async def generate_about_author_chapter(self) -> str:
        """Generate About the Author file, fetch avatar."""
        author_avatar = (
            await fetch_image(
                self.data["user"]["avatar"].replace("128", "512")
            )  # Increase image resolution
            if self.data["user"]["avatar"]
            else None
        )
        about_author = self.template.replace(
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

        return about_author

    def generate_toc(self):
        ids = [part["id"] for part in self.data["parts"]]
        clean = BeautifulSoup(
            """
        <section id="contents" class="toc">
        <h2>Table of Contents</h2>
        <ul></ul>
        </section>
        """,
            "html.parser",
        )  # html.parser doesn't create <html>/<body> tags automatically

        ul = cast(bs4.Tag, clean.find("ul"))
        for part_id in ids:
            li = clean.new_tag("li")
            a = clean.new_tag("a")
            a["href"] = f"#{part_id}"
            li.append(a)
            ul.append(li)

        insert_point = cast(bs4.Tag, self.tree.find("div", {"id": "book"}))
        insert_point.append(clean)
        return str(clean)

    async def add_chapters(
        self, contents: List[bs4.Tag], download_images: bool = False
    ):
        """Add chapters to the PDF, downloading images if necessary. Also add Cover, Copyright, and About the Author pages."""

        # # Cover and Copyright Page
        await self.generate_cover_and_copyright_html()
        await self.generate_about_author_chapter()
        self.tree = BeautifulSoup(self.template)

        self.generate_toc()
        for part, content in zip(self.data["parts"], contents):
            insert_point = cast(bs4.Tag, self.tree.find("div", {"id": "book"}))
            insert_point.append(content)

            yield part["title"]

        # # About the Author page
        # about_author_html = await self.generate_about_author_chapter()

        # chapters.insert(0, cover_and_copyright_html)
        # chapters.append(about_author_html)

        with start_action(
            action_type="generate_pdf",
            output_filename=self.file.name,
            title=self.data["title"],
        ):
            # PDF Generation with wkhtmltopdf, written to self.file

            # At this stage, we have a bunch of HTML Files representing all the chapters that need to be generated. PDFKit handles ToC generation, so that's not included.

            font_config = FontConfiguration()

            stylesheet_obj = CSS(string=self.stylesheet, font_config=font_config)

            html_obj = HTML(string=str(self.tree))
            html_obj.write_pdf(
                self.file.name, stylesheets=[stylesheet_obj], font_config=font_config
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

    def dump(self) -> BytesIO:
        self.file.seek(0)
        buffer = BytesIO(self.file.read())
        self.file.close()

        return buffer


# ------ #
