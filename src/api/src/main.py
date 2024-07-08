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

app = FastAPI()
BUILD_PATH = Path(__file__).parent / "build"


@app.get("/")
def home():
    return FileResponse(BUILD_PATH / "index.html")


@app.get("/download/{story_id}")
async def download_book(
    story_id: int,
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

    data = await retrieve_story(story_id, cookies=cookies)
    book = epub.EpubBook()

    try:
        set_metadata(book, data)
    except KeyError:
        return HTMLResponse(
            status_code=404,
            content='Story not found. Check the ID - Support is available on the <a href="https://discord.gg/P9RHC4KCwd" target="_blank">Discord</a>',
        )

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
    book_data = temp_file.file.read()

    return StreamingResponse(
        BytesIO(book_data),
        media_type="application/epub+zip",
        headers={
            "Content-Disposition": f'attachment; filename="{slugify(data["title"])}_{story_id}_{"images" if download_images else ""}.epub"'  # Thanks https://stackoverflow.com/a/72729058
        },
    )


app.mount("/", StaticFiles(directory=BUILD_PATH), "static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
