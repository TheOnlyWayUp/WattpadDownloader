"""WattpadDownloader API Server."""

import asyncio
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from aiohttp import ClientResponseError
from bs4 import BeautifulSoup
from eliot import start_action
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from create_book import (
    EPUBGenerator,
    PDFGenerator,
    StoryNotFoundError,
    WattpadError,
    fetch_archive,
    fetch_cookies,
    fetch_image,
    fetch_story,
    fetch_story_content_zip,
    fetch_story_from_partId,
    fetch_library,
    fetch_list,
    fetch_username,
    logger,
    slugify,
    Story,
    List,
)
from create_book.parser import clean_tree, fetch_tree_images

app = FastAPI()
BUILD_PATH = Path(__file__).parent / "build"


class RequestCancelledMiddleware:
    # Thanks https://github.com/fastapi/fastapi/discussions/11360#discussion-6427734
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Let's make a shared queue for the request messages
        queue = asyncio.Queue()

        async def message_poller(sentinel, handler_task):
            nonlocal queue
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    handler_task.cancel()
                    return sentinel  # Break the loop

                # Puts the message in the queue
                await queue.put(message)

        sentinel = object()
        handler_task = asyncio.create_task(self.app(scope, queue.get, send))
        asyncio.create_task(message_poller(sentinel, handler_task))

        try:
            return await handler_task
        except asyncio.CancelledError:
            logger.info("Cancelling task as connection closed")


app.add_middleware(RequestCancelledMiddleware)


class DownloadFormat(Enum):
    pdf = "pdf"
    epub = "epub"


class DownloadMode(Enum):
    story = "story"
    part = "part"
    list = "list"
    archive = "archive"
    library = "library"


async def download_story(
    metadata: Story,
    download_images: bool = False,
    format: DownloadFormat = DownloadFormat.epub,
    cookies: dict = None,
) -> BytesIO:
    with start_action(
        action_type="download_story",
        story_id=metadata["id"],
        download_images=download_images,
        format=format,
    ):
        # Fetch cover image
        cover_data = await fetch_image(
            metadata["cover"].replace("-256-", "-512-")
        )  # Increase resolution
        if not cover_data:
            raise HTTPException(status_code=422)

        # Fetch parts archive
        story_zip = await fetch_story_content_zip(metadata["id"], cookies)
        archive = ZipFile(story_zip, "r")

        # Transform part metadata into an easily-indexable dictionary
        part_id_title_dictionary = {
            str(part["id"]): part["title"] for part in metadata["parts"]
        }

        part_trees: list[BeautifulSoup] = []

        for id in archive.namelist():
            if (
                id not in part_id_title_dictionary
            ):  # If a part is deleted and the old story_zip is cached, this is needed to avoid a KeyError exception
                continue

            part_trees.append(
                clean_tree(
                    part_id_title_dictionary[id],
                    id,
                    archive.read(id).decode("utf-8"),
                )
            )

        # Fetch images
        images = (
            [await fetch_tree_images(tree) for tree in part_trees]
            if download_images
            else []
        )

        # Build output file
        match format:
            case DownloadFormat.epub:
                book = EPUBGenerator(metadata, part_trees, cover_data, images)
            case DownloadFormat.pdf:
                # Fetch author profile picture
                author_image = await fetch_image(
                    metadata["user"]["avatar"].replace("-256-", "-512-")
                )
                if not author_image:
                    raise HTTPException(status_code=422)

                book = PDFGenerator(
                    metadata, part_trees, cover_data, images, author_image
                )

        logger.info(f"Retrieved story metadata and cover ({metadata['id']=})")

        book.compile()

        return book.dump()


async def download_many_stories(
    stories: list[Story],
    download_images: bool = False,
    format: DownloadFormat = DownloadFormat.epub,
    cookies: dict = None,
) -> BytesIO:
    output_buffer = BytesIO()
    with start_action(
        action_type="download_many_stories",
        stories=[story["id"] for story in stories],
        download_images=download_images,
        format=format,
    ):
        with ZipFile(output_buffer, "w") as archive:
            for story in stories:
                story_file = await download_story(
                    story, download_images, format, cookies
                )
                file_name = f"{slugify(story['title'])}_{story['id']}{'_images' if download_images else ''}.{'epub' if format==DownloadFormat.epub else 'pdf'}"
                archive.writestr(file_name, story_file.read())

        output_buffer.seek(0)

        return output_buffer


@app.get("/")
def home():
    return FileResponse(BUILD_PATH / "index.html")


@app.exception_handler(ClientResponseError)
def download_error_handler(request: Request, exception: ClientResponseError):
    match exception.status:
        case 400 | 404:
            return HTMLResponse(
                status_code=404,
                content='This story does not exist, or has been deleted. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
            )
        case 429:
            # Rate-limit by Wattpad
            return HTMLResponse(
                status_code=429,
                content='The website is overloaded. Please try again in a few minutes. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
            )
        case _:
            # Unhandled error
            return HTMLResponse(
                status_code=500,
                content='Something went wrong. Yell at me on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
            )


@app.exception_handler(WattpadError)
def download_wp_error_handler(request: Request, exception: WattpadError):
    if isinstance(exception, StoryNotFoundError):
        return HTMLResponse(
            status_code=404,
            content='This story does not exist, or has been deleted. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
        )


@app.get("/download/{download_id}")
async def handle_download(
    download_id: int,
    download_images: bool = False,
    mode: DownloadMode = DownloadMode.story,
    format: DownloadFormat = DownloadFormat.epub,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    with start_action(
        action_type="handle_download",
        download_id=download_id,
        download_images=download_images,
        format=format,
        mode=mode,
    ):
        if username and not password or password and not username:
            logger.error(
                "Username with no Password or Password with no Username provided."
            )
            return HTMLResponse(
                status_code=422,
                content='Include both the username <u>and</u> password, or neither. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
            )

        if username and password:
            # username and password are URL-Encoded by the frontend. FastAPI automatically decodes them.
            try:
                cookies = await fetch_cookies(username=username, password=password)
            except ValueError:
                logger.error("Invalid username or password.")
                return HTMLResponse(
                    status_code=403,
                    content='Incorrect Username and/or Password. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
                )
        else:
            cookies = None

        match format:
            case DownloadFormat.epub:
                media_type = "application/epub+zip"
                extension = "epub"
            case DownloadFormat.pdf:
                media_type = "application/pdf"
                extension = "pdf"

        id_download = True
        match mode:
            case DownloadMode.story:
                metadata = await fetch_story(download_id, cookies)
                output_buffer = await download_story(
                    metadata, download_images, format, cookies
                )
            case DownloadMode.part:
                download_id, metadata = await fetch_story_from_partId(
                    download_id, cookies
                )
                output_buffer = await download_story(
                    metadata, download_images, format, cookies
                )
            case DownloadMode.list:
                metadata = await fetch_list(download_id, cookies)
                output_buffer = await download_many_stories(
                    metadata["stories"], download_images, format, cookies
                )

                media_type = "application/zip"
                extension = "zip"
            case DownloadMode.archive:
                id_download = False
                if not cookies:
                    return HTMLResponse(
                        status_code=422,
                        content="Login credentials required for archive downloads",
                    )
                username = await fetch_username(cookies)
                stories = await fetch_archive(username, cookies)
                output_buffer = await download_many_stories(
                    stories, download_images, format, cookies
                )
                media_type = "application/zip"
                extension = "zip"
            case DownloadMode.library:
                id_download = False
                if not cookies:
                    return HTMLResponse(
                        status_code=422,
                        content="Login credentials required for library downloads",
                    )
                username = await fetch_username(cookies)
                stories = await fetch_library(username, cookies)
                output_buffer = await download_many_stories(
                    stories, download_images, format, cookies
                )
                media_type = "application/zip"
                extension = "zip"

        async def iterfile(file_size):
            chunk_size = 512 * 4
            sleep_duration = 0.1
            num_chunks = 10 * 60 / sleep_duration  # number of chunks in 10 minutes
            if (
                num_chunks * chunk_size < file_size
            ):  # Will the download take >10 minutes
                chunk_size = int(file_size / num_chunks)
            while chunk := output_buffer.read(chunk_size):
                await asyncio.sleep(sleep_duration)  # throttle download speed
                yield chunk

        file_size = output_buffer.getbuffer().nbytes

        return StreamingResponse(
            iterfile(file_size),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{slugify(metadata["name" if mode==DownloadMode.list else "title"]) if id_download else (username+'_'+("archive" if mode == DownloadMode.archive else "library"))}{'_'+str(download_id) if id_download else ""}{"_images" if download_images else ""}{'_'+format.value if extension == "zip" else ""}.{extension}"',  # Thanks https://stackoverflow.com/a/72729058
                "Content-Length": str(file_size),
            },
        )


@app.get("/donate")
def donate():
    """Redirect to donation URL."""
    return RedirectResponse("https://buymeacoffee.com/theonlywayup")


app.mount("/", StaticFiles(directory=BUILD_PATH), "static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80)
