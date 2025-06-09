from io import BytesIO
from tempfile import _TemporaryFileWrapper
from typing import List, Literal

from bs4 import BeautifulSoup
from ebooklib.epub import EpubBook

from ..models import Story


class AbstractGenerator:
    """Compile parsed part trees to a file.

    Args:
        metadata (Story): Story Metadata.
        part_trees (List[BeautifulSoup]): Parsed part trees.
        cover (bytes): Cover image.
        images (List[List[bytes]] | None): An array of images for each chapter, if images have been downloaded.
    """

    def __init__(
        self,
        metadata: Story,
        part_trees: List[BeautifulSoup],
        cover: bytes,
        images: List[List[bytes]] | None,
    ):
        self.story = metadata
        self.parts = part_trees
        self.cover = cover
        self.images = images

        self.book: EpubBook | _TemporaryFileWrapper = None  # type: ignore

    def compile(self) -> Literal[True]:
        """Compile the part trees into the corresponding in-memory representation of the generator format.

        Returns:
            Literal[True]: Compiled successfully.
        """
        return True

    def dump(self) -> BytesIO:
        """Return a Buffer of the compiled file."""
        buffer = BytesIO()

        return buffer
