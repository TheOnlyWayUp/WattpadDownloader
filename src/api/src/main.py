"""WattpadDownloader API Server."""

from typing import Optional
import asyncio
import tempfile
from pathlib import Path
from io import BytesIO
from enum import Enum
from eliot import start_action
from aiohttp import ClientResponseError
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from ebooklib import epub
from create_book import (
    retrieve_story,
    set_cover,
    set_metadata,
    add_chapters,
    slugify,
    wp_get_cookies,
    fetch_story_id,
    logger,
)


app = FastAPI()
BUILD_PATH = Path(__file__).parent / "build"

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


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


class DownloadMode(Enum):
    story = "story"
    part = "part"
    collection = "collection"


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


@app.get("/download/{download_id}")
async def handle_download(
    download_id: int,
    download_images: bool = False,
    mode: DownloadMode = DownloadMode.story,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    with start_action(
        action_type="download",
        download_id=download_id,
        download_images=download_images,
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
                cookies = await wp_get_cookies(username=username, password=password)
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
            case DownloadMode.part:
                story_id = await fetch_story_id(download_id, cookies)

        logger.error(f"Retrieved story id ({story_id=})")

        book = epub.EpubBook()

        metadata = await retrieve_story(story_id, cookies)
        set_metadata(book, metadata)

        await set_cover(book, metadata, cookies=cookies)

        async for title in add_chapters(
            book, metadata, download_images=download_images, cookies=cookies
        ):
            print(title)
            ...

        # Book is compiled
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".epub", delete=True
        )  # Thanks https://stackoverflow.com/a/75398222

        # create epub file
        epub.write_epub(temp_file, book, {})

        temp_file.file.seek(0)
        book_data = temp_file.file.read()

        return StreamingResponse(
            BytesIO(book_data),
            media_type="application/epub+zip",
            headers={
                "Content-Disposition": f'attachment; filename="{slugify(metadata["title"])}_{story_id}_{"images" if download_images else ""}.epub"'  # Thanks https://stackoverflow.com/a/72729058
            },
        )


app.mount("/", StaticFiles(directory=BUILD_PATH), "static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8086, workers=24)
