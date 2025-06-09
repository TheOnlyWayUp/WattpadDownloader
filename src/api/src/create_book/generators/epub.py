from io import BytesIO
from typing import Generator, List

from bs4 import BeautifulSoup
from ebooklib import epub

from ..models import Story
from .types import AbstractGenerator


class EPUBGenerator(AbstractGenerator):
    def __init__(
        self,
        metadata: Story,
        part_trees: List[BeautifulSoup],
        cover: bytes,
        images: List[Generator[bytes]] | None,
    ):
        self.story = metadata
        self.parts = part_trees
        self.cover = cover
        self.images = images

        self.book: epub.EpubBook = epub.EpubBook()

    def add_metadata(self):
        """Add metadata to epub."""
        self.book.add_author(self.story["user"]["username"])

        self.book.add_metadata("DC", "title", self.story["title"])
        self.book.add_metadata("DC", "description", self.story["description"])
        self.book.add_metadata("DC", "date", self.story["createDate"])
        self.book.add_metadata("DC", "modified", self.story["modifyDate"])
        self.book.add_metadata("DC", "language", self.story["language"]["name"])

        self.book.add_metadata(
            None, "meta", "", {"name": "tags", "content": ", ".join(self.story["tags"])}
        )
        self.book.add_metadata(
            None,
            "meta",
            "",
            {"name": "mature", "content": str(int(self.story["mature"]))},
        )
        self.book.add_metadata(
            None,
            "meta",
            "",
            {"name": "completed", "content": str(int(self.story["completed"]))},
        )

    def add_cover(self):
        """Add cover to epub."""
        self.book.set_cover("cover.jpg", self.cover)
        cover_chapter = epub.EpubHtml(
            file_name="titlepage.xhtml",  # Standard for cover page
        )
        cover_chapter.set_content('<img src="cover.jpg">')
        self.book.add_item(cover_chapter)

    def add_chapters(self):
        """Add chapters to epub, replacing references to image urls to static image paths if images are provided during initialization."""
        chapters = []

        for idx, (part, tree) in enumerate(zip(self.story["parts"], self.parts)):
            chapter = epub.EpubHtml(
                title=part["title"], file_name=f"{idx}_{part['id']}.xhtml"
            )

            if self.images:
                for img_idx, (img_data, img_tag) in enumerate(
                    zip(self.images[idx], tree.find_all("img"))
                ):
                    path = f"static/{idx}_{part['id']}/{img_idx}.jpeg"
                    img = epub.EpubImage(
                        media_type="image/jpeg", content=img_data, file_name=path
                    )
                    self.book.add_item(img)

                    img_tag["src"] = path

            chapter.set_content(tree.prettify())
            self.book.add_item(chapter)
            chapters.append(chapter)

        # ! Review, are these needed? #11
        self.book.toc = chapters

        # Thanks https://github.com/aerkalov/ebooklib/blob/master/samples/09_create_image/create.py
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # create spine
        self.book.spine = ["nav"] + chapters

    def compile(self):
        self.add_metadata()
        self.add_cover()
        self.add_chapters()
        return True

    def dump(self) -> BytesIO:
        # Thanks https://stackoverflow.com/a/75398222
        buffer = BytesIO()
        epub.write_epub(buffer, self.book)

        buffer.seek(0)

        return buffer
