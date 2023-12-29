from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ebooklib import epub
from create_book import retrieve_story, set_cover, set_metadata, add_chapters
import tempfile
from io import BytesIO

app = FastAPI()


@app.get("/download/{story_id}")
async def download_book(story_id: int):
    data = await retrieve_story(story_id)
    book = epub.EpubBook()

    # Metadata and Cover are updated
    set_metadata(book, data)
    await set_cover(book, data)
    # print("Metadata Downloaded")

    # Chapters are downloaded
    async for title in add_chapters(book, data):
        # print(f"Part ({title}) downloaded")
        ...

    # Book is compiled
    temp_file = tempfile.NamedTemporaryFile(
        dir=".", suffix=".epub", delete=True
    )  # Thanks https://stackoverflow.com/a/75398222

    # create epub file
    epub.write_epub(temp_file, book, {})

    temp_file.file.seek(0)
    book_data = temp_file.file.read()

    return StreamingResponse(
        BytesIO(book_data),
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="book_{story_id}.epub"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
