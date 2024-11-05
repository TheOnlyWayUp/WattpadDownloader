from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from ebooklib import epub
from create_book import (
    retrieve_story,
    set_cover,
    set_metadata,
    add_chapters,
    slugify,
    wp_get_cookies,
)
import tempfile
from io import BytesIO
from fastapi.staticfiles import StaticFiles
from aiohttp import ClientResponseError, ClientSession

app = FastAPI()
BUILD_PATH = Path(__file__).parent / "build"

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


@app.get("/")
def home():
    return FileResponse(BUILD_PATH / "index.html")


@app.get("/download/{type}/{download_id}")
async def handle_download(
    type: str,
    download_id: int,
    download_images: bool = False,
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
        if type == "story":
            data = await download_story(download_id, download_images, cookies)
        elif type == "part":
            data = await download_part(download_id, download_images, cookies)
        elif type == "list":
            data = await download_list(download_id, download_images, cookies)
        else:
            return HTMLResponse(
                status_code=422,
                content="Unsupported Type. Please attempt to download a story, part, or list",
            )
    except:
        return HTMLResponse(
            status_code=404,
            content='Invalid ID. Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
        )

    if type == "story" or type == "part":
        return StreamingResponse(
            BytesIO(data["file"]),
            media_type="application/epub+zip",
            headers={
                "Content-Disposition": f'attachment; filename="{slugify(data["metadata"]["title"])}_{data["metadata"]["id"]}_{"images" if download_images else ""}.epub"'  # Thanks https://stackoverflow.com/a/72729058
            },
        )

    else:
        return StreamingResponse(
            BytesIO(data["file"]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{slugify(data["metadata"]["title"])}_{data["metadata"]["id"]}_{"images" if download_images else ""}.zip"'  # Thanks https://stackoverflow.com/a/72729058
            },
        )


async def download_story(
    story_id: int,
    download_images: bool = False,
    cookies: Optional[dict] = None,
):
    data = await download_epub(story_id, download_images, cookies)
    return data


async def download_part(
    part_id: int,
    download_images: bool = False,
    cookies: Optional[dict] = None,
):
    # Get Story ID from Part ID
    async with ClientSession(
        headers=headers,
    ) as session:
        async with session.get(
            f"https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=groupId"
        ) as response:
            if not response.ok:
                raise (ValueError)
            else:
                data = await response.json()

    story_id = data["groupId"]
    data = await download_epub(story_id, download_images, cookies)
    return data


async def download_list(
    list_id: int,
    download_images: bool = False,
    cookies: Optional[dict] = None,
):
    print("LIST DOWNLOADING NOT IMPLEMENTED YET")
    raise (ValueError)


async def download_epub(
    story_id: int,
    download_images: bool = False,
    cookies: Optional[dict] = None,
):
    data = await retrieve_story(story_id, cookies=cookies)
    book = epub.EpubBook()

    set_metadata(book, data)

    await set_cover(book, data, cookies=cookies)
    # print("Metadata Downloaded")

    # Chapters are downloaded
    async for title in add_chapters(
        book, data, download_images=download_images, cookies=cookies
    ):
        # print(f"Part ({title}) downloaded")
        ...

    # Book is compiled
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".epub", delete=True
    )  # Thanks https://stackoverflow.com/a/75398222

    # create epub file
    epub.write_epub(temp_file, book, {})

    temp_file.file.seek(0)
    epub_file = temp_file.file.read()

    return {"file": epub_file, "metadata": data}


app.mount("/", StaticFiles(directory=BUILD_PATH), "static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
