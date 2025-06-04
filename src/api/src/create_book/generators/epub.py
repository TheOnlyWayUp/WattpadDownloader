from ebooklib import epub
from typing import List
from models import Story
from io import BytesIO
import bs4
from aiohttp_client_cache.session import CachedSession

headers = {}


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
            if download_images:  # ! TODO : Download images elsewhere
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
