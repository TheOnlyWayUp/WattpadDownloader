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
)
import tempfile
from io import BytesIO
from fastapi.staticfiles import StaticFiles
from aiohttp import ClientResponseError, ClientSession
from zipfile import ZipFile

app = FastAPI()
BUILD_PATH = Path(__file__).parent / "build"

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


class URLType(Enum):
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
    mode: URLType = URLType.story,
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

    match mode:
        case URLType.story:
            ...
        case URLType.part:
            ...
        case URLType.collection:
            raise NotImplementedError()
        case _:
            return HTMLResponse(
                status_code=422,
                content="Unsupported Type. Please attempt to download a story, part, or list",
            )

    # if mode is URLType.story or mode is URLType.part:
    #     return StreamingResponse(
    #         BytesIO(data["file"]),
    #         media_type="application/epub+zip",
    #         headers={
    #             "Content-Disposition": f'attachment; filename="{slugify(data["metadata"]["title"])}_{data["metadata"]["id"]}_{"images" if download_images else ""}.epub"'  # Thanks https://stackoverflow.com/a/72729058
    #         },
    #     )

    # else:
    #     return StreamingResponse(
    #         data["file"],
    #         media_type="application/zip",
    #         headers={
    #             "Content-Disposition": f'attachment; filename="{slugify(data["name"])}_{download_id}_{"images" if download_images else ""}.zip"'  # Thanks https://stackoverflow.com/a/72729058
    #         },
    #     )


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
    response = await get_url(
        f"https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=groupId"
    )
    story_id = response["groupId"]

    data = await download_epub(story_id, download_images, cookies)
    return data


async def download_list(
    list_id: int,
    download_images: bool = False,
    cookies: Optional[dict] = None,
):

    list_data = await get_url(
        f"https://www.wattpad.com/api/v3/lists/{list_id}?fields=name,stories(id)"
    )

    # Initialize a BytesIO buffer to store the zip file in memory
    zip_buffer = BytesIO()

    with ZipFile(zip_buffer, "w") as archive:
        for story in list_data["stories"]:
            story_id = story["id"]

            # Download each story as an EPUB
            file_data = await download_epub(story_id, download_images, cookies)

            # Define a unique filename for each story in the zip archive
            file_name = f"{slugify(file_data['metadata']['title'])}_{story_id}_{'images' if download_images else ''}.epub"

            # Add the EPUB file to the zip archive in memory
            archive.writestr(file_name, file_data["file"])

    # Ensure the buffer's pointer is at the beginning before sending
    zip_buffer.seek(0)

    return {"name": list_data["name"], "file": zip_buffer}


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


async def get_url(url):
    async with ClientSession(
        headers=headers,
    ) as session:
        async with session.get(url) as response:
            if not response.ok:
                raise (ValueError)
            else:
                data = await response.json()
                return data


app.mount("/", StaticFiles(directory=BUILD_PATH), "static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
