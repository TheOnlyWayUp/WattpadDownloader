from typing import Optional
from pathlib import Path
from enum import Enum
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from ebooklib import epub
from create_book import (
    retrieve_story,
    set_cover,
    set_metadata,
    add_chapters,
    slugify,
    wp_get_cookies,
    fetch_story_id,
)
import tempfile
from io import BytesIO
from fastapi.staticfiles import StaticFiles
from aiohttp import ClientResponseError

app = FastAPI()
BUILD_PATH = Path(__file__).parent / "build"

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


class DownloadMode(Enum):
    story = "story"
    part = "part"
    collection = "collection"


@app.get("/")
def home():
    return FileResponse(BUILD_PATH / "index.html")


@app.get("/download/{download_id}")
async def handle_download(
    download_id: int,
    download_images: bool = False,
    mode: DownloadMode = DownloadMode.story,
    username: Optional[str] = None,
    password: Optional[str] = None,
):

    if username and not password or password and not username:
        return HTMLResponse(
            status_code=422,
            content='Include both the username <u>and</u> password, or neither. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
        )

    if username and password:
        # username and password are URL-Encoded by the frontend. FastAPI automatically decodes them.
        try:
            cookies = await wp_get_cookies(username=username, password=password)
        except ValueError:
            return HTMLResponse(
                status_code=403,
                content='Incorrect Username and/or Password. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
            )
    else:
        cookies = None

    try:
        match mode:
            case DownloadMode.story:
                story_id = download_id
            case DownloadMode.part:
                story_id = await fetch_story_id(download_id, cookies)

        metadata = await retrieve_story(story_id, cookies)
        book = epub.EpubBook()

        set_metadata(book, metadata)
        await set_cover(book, metadata, cookies=cookies)

        async for title in add_chapters(
            book, metadata, download_images=download_images, cookies=cookies
        ):
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

    except KeyError:
        # Invalid ID
        return HTMLResponse(
            status_code=404,
            content='The story you tried to download does not exist or has been deleted. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
        )

    except ClientResponseError:
        # Rate-limit by Wattpad
        return HTMLResponse(
            status_code=429,
            content='Unfortunately, the downloader got rate-limited by Wattpad. Please try again later. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
        )


app.mount("/", StaticFiles(directory=BUILD_PATH), "static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
