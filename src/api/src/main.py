"""WattpadDownloader API Server."""

import asyncio
from enum import Enum
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from aiohttp import ClientResponseError
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
    StoryNotFoundError,
    WattpadError,
    fetch_cookies,
    fetch_image,
    fetch_story,
    fetch_story_content_zip,
    fetch_story_from_partId,
    generate_clean_part_html,
    logger,
    slugify,
)

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
    # pdf = "pdf"
    epub = "epub"


class DownloadMode(Enum):
    story = "story"
    part = "part"


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
        action_type="download",
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

        match mode:
            case DownloadMode.story:
                story_id = download_id
                metadata = await fetch_story(story_id, cookies)
            case DownloadMode.part:
                story_id, metadata = await fetch_story_from_partId(download_id, cookies)

        cover_data = await fetch_image(
            metadata["cover"].replace("-256-", "-512-")
        )  # Increase resolution
        if not cover_data:
            raise HTTPException(status_code=422)

        match format:
            case DownloadFormat.epub:
                book = EPUBGenerator(metadata, cover_data)
                media_type = "application/epub+zip"
            # case DownloadFormat.pdf:
            #     book = PDFGenerator(metadata, cover_data)
            #     media_type = "application/pdf"

        logger.info(f"Retrieved story metadata and cover ({story_id=})")

        story_zip = await fetch_story_content_zip(story_id, cookies)
        archive = ZipFile(story_zip, "r")

        part_contents = [
            generate_clean_part_html(
                part, archive.read(str(part["id"])).decode("utf-8")
            )
            for part in metadata["parts"]
        ]

        async for title in book.add_chapters(
            part_contents, download_images=download_images
        ):
            ...

        book_buffer = book.dump()

        async def iterfile():
            while chunk := book_buffer.read(512 * 4):  # 4 kb/s
                await asyncio.sleep(0.1)  # throttle download speed
                yield chunk

        return StreamingResponse(
            iterfile(),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{slugify(metadata["title"])}_{story_id}{"_images" if download_images else ""}.{format.value}"'  # Thanks https://stackoverflow.com/a/72729058
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
