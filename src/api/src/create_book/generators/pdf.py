from typing import List, cast
import tempfile
from base64 import b64encode
import bs4
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from exiftool import ExifTool
from logs import exiftool_logger
from bs4 import BeautifulSoup
from utils import smart_trim
from models import Story
from eliot import start_action
from io import BytesIO


async def fetch_image(*args, **kwargs):
    # TODO
    raise NotImplementedError()


class PDFGenerator:
    """PDF Generation utilities"""

    def __init__(self, data: Story, cover: bytes):
        """Initialize PDGenerator, create PDF Temporary file."""
        self.data = data
        self.file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=True)
        self.cover = cover
        self.content: str = ""
        self.copyright = {
            1: {
                "name": "All Rights Reserved",
                "statement": "©️ {published_year} by {username}. All Rights Reserved.",
                "freedoms": "No reuse, redistribution, or modification without permission.",
                "printing": "Not allowed without explicit permission.",
                "image_url": None,
            },
            2: {
                "name": "Public Domain",
                "statement": "This work is in the public domain. Originally published in {published_year} by {username}.",
                "freedoms": "Free to use for any purpose without permission.",
                "printing": "Allowed for personal or commercial purposes.",
                "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/cc-zero.png",
            },
            3: {
                "name": "Creative Commons Attribution (CC-BY)",
                "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution 4.0 International License.",
                "freedoms": "Allows reuse, redistribution, and modification with credit to the author.",
                "printing": "Allowed with proper credit.",
                "image_url": "https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by.png",
            },
            4: {
                "name": "CC Attribution NonCommercial (CC-BY-NC)",
                "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License.",
                "freedoms": "Allows reuse and modification for non-commercial purposes with credit.",
                "printing": "Allowed for non-commercial purposes with proper credit.",
                "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc.png",
            },
            5: {
                "name": "CC Attribution NonCommercial NoDerivs (CC-BY-NC-ND)",
                "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial-NoDerivs 4.0 International License.",
                "freedoms": "Allows sharing in original form for non-commercial purposes with credit; no modifications allowed.",
                "printing": "Allowed for non-commercial purposes in original form with proper credit.",
                "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc-nd.png",
            },
            6: {
                "name": "CC Attribution NonCommercial ShareAlike (CC-BY-NC-SA)",
                "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.",
                "freedoms": "Allows reuse and modification for non-commercial purposes under the same license, with credit.",
                "printing": "Allowed for non-commercial purposes with proper credit under the same license.",
                "image_url": "http://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc-sa.png",
            },
            7: {
                "name": "CC Attribution ShareAlike (CC-BY-SA)",
                "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License.",
                "freedoms": "Allows reuse and modification for any purpose under the same license, with credit.",
                "printing": "Allowed with proper credit under the same license.",
                "image_url": "https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-sa.png",
            },
            8: {
                "name": "CC Attribution NoDerivs (CC-BY-ND)",
                "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NoDerivs 4.0 International License.",
                "freedoms": "Allows sharing in original form for any purpose with credit; no modifications allowed.",
                "printing": "Allowed in original form with proper credit.",
                "image_url": "https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nd.png",
            },
        }

        with open("./pdf/stylesheet.css") as reader:
            self.stylesheet = reader.read()
        with open("./pdf/book.html") as reader:
            self.template = reader.read()

    async def generate_cover_and_copyright_html(
        self,
    ) -> str:
        """Generate Cover and Copyright file, fetch copyright image (cached), use self.cover for cover."""

        copyright_data = self.copyright[self.data["copyright"]]

        template = self.template
        about_copyright = (
            template.replace(
                "{statement}",
                copyright_data["statement"].format(
                    username=self.data["user"]["username"],
                    published_year=self.data["createDate"].split("-", 2)[0],
                ),
            )
            .replace("{author}", self.data["user"]["username"])
            .replace("{freedoms}", copyright_data["freedoms"])
            .replace(
                "{printing}",
                copyright_data["printing"],
            )
            .replace("{book_id}", self.data["id"])
            .replace("{book_title}", self.data["title"])
        )

        copyright_image = (
            await fetch_image(copyright_data["image_url"], should_cache=True)
            if copyright_data["image_url"]
            else None
        )
        image_block = (
            """<img src="{image_url}" 
alt="{name}" 
width="88" 
height="31" 
id="copyright-license-image">""".format(
                image_url=f"data:image/jpg;base64,{b64encode(copyright_image).decode()}",
                name=copyright_data["name"],
            )
            if copyright_image
            else ""
        )
        about_copyright = (
            about_copyright.replace(
                "{copyright_image}",
                image_block,
            )
            if image_block
            else about_copyright.replace("{copyright_image}", "")
        )
        about_copyright = about_copyright.replace(
            "{cover}", f"data:image/jpg;base64,{b64encode(self.cover).decode()}"
        )

        self.template = about_copyright
        return about_copyright

    async def generate_about_author_chapter(self) -> str:
        """Generate About the Author file, fetch avatar."""
        author_avatar = (
            await fetch_image(
                self.data["user"]["avatar"].replace("128", "512")
            )  # Increase image resolution
            if self.data["user"]["avatar"]
            else None
        )
        about_author = self.template.replace(
            "{username}", self.data["user"]["username"]
        ).replace("{description}", smart_trim(self.data["user"]["description"]))

        about_author = (
            about_author.replace(
                "{avatar}",
                f"""
                <img src="data:image/jpg;base64,{b64encode(author_avatar).decode()}" alt="Author's profile picture" id="author-profile-picture">""",
            )
            if author_avatar
            else about_author.replace("{avatar}", "")
        )

        self.template = about_author
        return about_author

    def generate_toc(self):
        ids = [part["id"] for part in self.data["parts"]]
        clean = BeautifulSoup(
            """
        <section id="contents" class="toc">
        <h1>Table of Contents</h1>
        <ul></ul>
        </section>
        """,
            "html.parser",
        )  # html.parser doesn't create <html>/<body> tags automatically

        ul = cast(bs4.Tag, clean.find("ul"))
        for part_id in ids:
            li = clean.new_tag("li")
            a = clean.new_tag("a")
            a["href"] = f"#{part_id}"
            li.append(a)
            ul.append(li)

        insert_point = cast(bs4.Tag, self.tree.find("div", {"id": "book"}))
        insert_point.append(clean)
        return str(clean)

    async def add_chapters(
        self, contents: List[bs4.Tag], download_images: bool = False
    ):
        """Add chapters to the PDF, downloading images if necessary. Also add Cover, Copyright, and About the Author pages."""

        # # Cover and Copyright Page
        await self.generate_cover_and_copyright_html()
        await self.generate_about_author_chapter()
        self.tree = BeautifulSoup(self.template, "lxml")

        self.generate_toc()
        for part, content in zip(self.data["parts"], contents):
            insert_point = cast(bs4.Tag, self.tree.find("div", {"id": "book"}))
            insert_point.append(content)

            yield part["title"]

        # # About the Author page
        # about_author_html = await self.generate_about_author_chapter()

        # chapters.insert(0, cover_and_copyright_html)
        # chapters.append(about_author_html)

        with start_action(
            action_type="generate_pdf",
            output_filename=self.file.name,
            title=self.data["title"],
        ):
            # PDF Generation with wkhtmltopdf, written to self.file

            # At this stage, we have a bunch of HTML Files representing all the chapters that need to be generated. PDFKit handles ToC generation, so that's not included.

            font_config = FontConfiguration()

            stylesheet_obj = CSS(string=self.stylesheet, font_config=font_config)

            html_obj = HTML(string=str(self.tree))
            html_obj.write_pdf(
                self.file.name, stylesheets=[stylesheet_obj], font_config=font_config
            )

        with start_action(action_type="add_metadata") as action:
            # Metadata generation with Exiftool
            clean_description = (
                self.data["description"].strip().replace("\n", "$/")
            )  # exiftool doesn't parse \ns correctly, they support $/ for the same instead. `&#xa;` is another option.

            action.log(f"clean_description: {clean_description}")

            metadata = {
                "Author": self.data["user"]["username"],
                "Title": self.data["title"],
                "Subject": clean_description,
                "CreationDate": self.data["createDate"],
                "ModDate": self.data["modifyDate"],
                "Keywords": ",".join(self.data["tags"]),
                "Language": self.data["language"]["name"],
                "Completed": self.data["completed"],
                "MatureContent": self.data["mature"],
                "Producer": "Dhanush Rambhatla (TheOnlyWayUp - https://rambhat.la) and WattpadDownloader",
            }  # As per https://exiftool.org/TagNames/PDF.html

            action.log(f"options: {metadata}")

            with ExifTool(
                config_file="../exiftool.config", logger=exiftool_logger
            ) as et:
                # Custom configuration adds Completed and MatureContent tags.
                # exiftool logger logs executed command
                et.execute(
                    *(
                        [f"-{key}={value}" for key, value in metadata.items()]
                        + [
                            "-overwrite_original",
                            self.file.file.name,
                        ]
                    )
                )

    def dump(self) -> BytesIO:
        self.file.seek(0)
        buffer = BytesIO(self.file.read())
        self.file.close()

        return buffer
