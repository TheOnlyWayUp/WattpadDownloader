from base64 import b64encode
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper

from bs4 import BeautifulSoup
from exiftool import ExifTool
from jinja2 import Template
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from ..models import Story
from .types import AbstractGenerator

DATA_PATH = Path(__file__).parent / "pdf"
ASSET_PATH = DATA_PATH / "assets"

COPYRIGHT_DATA = {
    1: {
        "name": "All Rights Reserved",
        "statement": "©️ {published_year} by {username}. All Rights Reserved.",
        "freedoms": "No reuse, redistribution, or modification without permission.",
        "printing": "Not allowed without explicit permission.",
        "asset": None,
    },
    2: {
        "name": "Public Domain",
        "statement": "This work is in the public domain. Originally published in {published_year} by {username}.",
        "freedoms": "Free to use for any purpose without permission.",
        "printing": "Allowed for personal or commercial purposes.",
        "asset": ASSET_PATH / "cc-zero.png",
    },
    3: {
        "name": "Creative Commons Attribution (CC-BY)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution 4.0 International License.",
        "freedoms": "Allows reuse, redistribution, and modification with credit to the author.",
        "printing": "Allowed with proper credit.",
        "asset": ASSET_PATH / "by.png",
    },
    4: {
        "name": "CC Attribution NonCommercial (CC-BY-NC)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License.",
        "freedoms": "Allows reuse and modification for non-commercial purposes with credit.",
        "printing": "Allowed for non-commercial purposes with proper credit.",
        "asset": ASSET_PATH / "by-nc.png",
    },
    5: {
        "name": "CC Attribution NonCommercial NoDerivs (CC-BY-NC-ND)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial-NoDerivs 4.0 International License.",
        "freedoms": "Allows sharing in original form for non-commercial purposes with credit; no modifications allowed.",
        "printing": "Allowed for non-commercial purposes in original form with proper credit.",
        "asset": ASSET_PATH / "by-nc-nd.png",
    },
    6: {
        "name": "CC Attribution NonCommercial ShareAlike (CC-BY-NC-SA)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.",
        "freedoms": "Allows reuse and modification for non-commercial purposes under the same license, with credit.",
        "printing": "Allowed for non-commercial purposes with proper credit under the same license.",
        "asset": ASSET_PATH / "by-nc-sa.png",
    },
    7: {
        "name": "CC Attribution ShareAlike (CC-BY-SA)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License.",
        "freedoms": "Allows reuse and modification for any purpose under the same license, with credit.",
        "printing": "Allowed with proper credit under the same license.",
        "asset": ASSET_PATH / "by-sa.png",
    },
    8: {
        "name": "CC Attribution NoDerivs (CC-BY-ND)",
        "statement": "©️ {published_year} by {username}. This work is licensed under a Creative Commons Attribution-NoDerivs 4.0 International License.",
        "freedoms": "Allows sharing in original form for any purpose with credit; no modifications allowed.",
        "printing": "Allowed in original form with proper credit.",
        "asset": ASSET_PATH / "by-nd.png",
    },
}  # Maps Wattpad Copyright IDs to their corresponding data.

with open(DATA_PATH / "stylesheet.css") as reader:
    STYLESHEET = reader.read()


with open(DATA_PATH / "book.html") as reader:
    TEMPLATE = reader.read()


class PDFGenerator(AbstractGenerator):
    def __init__(
        self,
        metadata: Story,
        part_trees: list[BeautifulSoup],
        cover: bytes,
        images: list[list[bytes | None]],
        author_image: bytes,
    ):
        self.story = metadata
        self.parts = part_trees
        self.cover = cover
        self.images = images
        self.author = author_image

        self.book: _TemporaryFileWrapper = NamedTemporaryFile(suffix=".pdf")
        self.content = TEMPLATE

    def generate_chapters(self) -> dict[int, str]:
        """Return a dictionary of part_ids to content trees, with image URLs replaced with base64 encoded images if provided during initialization."""
        data: dict[int, str] = {}
        for idx, (part, tree) in enumerate(zip(self.story["parts"], self.parts)):
            if self.images:
                for img_idx, (img_data, img_tag) in enumerate(
                    zip(self.images[idx], tree.find_all("img"))
                ):
                    if not img_data:
                        continue

                    img_tag[
                        "src"
                    ] = f"data:image/jpg;base64,{b64encode(img_data).decode()}"

            data[part["id"]] = tree.prettify()

        return data

    def populate_template(self, parts: dict[int, str]):
        """Populate HTML Template with Story data."""
        copyright = COPYRIGHT_DATA[self.story["copyright"]]
        data = {
            "statement": copyright["statement"].format(
                username=self.story["user"]["username"],
                published_year=self.story["createDate"].split("-", 2)[0],
            ),
            "author": self.story["user"]["username"],
            "freedoms": copyright["freedoms"],
            "printing": copyright["printing"],
            "book_id": self.story["id"],
            "book_title": self.story["title"],
            "cover": f"data:image/jpg;base64,{b64encode(self.cover).decode()}",
            "username": self.story["user"]["username"],
            "description": self.story["description"],
            "avatar": b64encode(self.author).decode(),
            "copyright": {
                "data": b64encode(copyright["asset"].read_bytes()).decode()
                if copyright["asset"]
                else "",
                "name": copyright["name"],
            },
            "parts": parts,
        }

        self.content: str = Template(self.content).render(data)

    def generate_pdf(self):
        """Generate and write the PDF to a temporary file (self.book)."""
        font_config = FontConfiguration()

        stylesheet_obj = CSS(string=STYLESHEET, font_config=font_config)

        html_obj = HTML(string=self.content)
        html_obj.write_pdf(
            self.book.name, stylesheets=[stylesheet_obj], font_config=font_config
        )

    def add_metadata(self):
        """Write metadata to generated PDF file at self.book, using ExifTool."""

        clean_description = (
            self.story["description"].strip().replace("\n", "$/")
        )  # exiftool doesn't parse \ns correctly, they support $/ for the same instead. `&#xa;` is another option.

        metadata = {
            "Author": self.story["user"]["username"],
            "Title": self.story["title"],
            "Subject": clean_description,
            "CreationDate": self.story["createDate"],
            "ModDate": self.story["modifyDate"],
            "Keywords": ",".join(self.story["tags"]),
            "Language": self.story["language"]["name"],
            "Completed": self.story["completed"],
            "MatureContent": self.story["mature"],
            "Producer": "Dhanush Rambhatla (TheOnlyWayUp - https://rambhat.la) and WattpadDownloader",
        }  # As per https://exiftool.org/TagNames/PDF.html

        with ExifTool(config_file=DATA_PATH / "exiftool.config") as et:
            # Custom configuration adds Completed and MatureContent tags.
            # exiftool logger logs executed command
            et.execute(
                *(
                    [f"-{key}={value}" for key, value in metadata.items()]
                    + [
                        "-overwrite_original",
                        self.book.file.name,
                    ]
                )
            )

    def compile(self):
        parts = self.generate_chapters()
        self.populate_template(parts)
        self.generate_pdf()
        self.add_metadata()
        return True

    def dump(self) -> BytesIO:
        self.book.seek(0)
        buffer = BytesIO(self.book.read())
        self.book.close()

        return buffer
