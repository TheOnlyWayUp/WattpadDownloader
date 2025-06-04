import re
import bs4
import unicodedata
from bs4 import BeautifulSoup
from typing import cast
from models import Part


def smart_trim(text: str, max_length: int = 400) -> str:
    """Truncate a string intelligently at newlines. Coherence and max-length adherence."""
    chunks = [t for t in text.split("\n") if t]

    to_return = ""
    for chunk in chunks:
        if len(to_return) + len(chunk) < max_length:
            to_return = chunk + "<br />"
        else:
            to_return = to_return.rstrip("<br />")
            break

    return to_return


def generate_clean_part_html(part: Part, content: str) -> bs4.Tag:
    """Rebuild HTML Structure for a Part."""
    chapter_title = part["title"]
    chapter_id = part["id"]

    clean = BeautifulSoup(
        f"""
    <section id="section_{chapter_id}" class="chapitre">
        <h1 id="{chapter_id}" class="chapter-title">{chapter_title}</h1>
    </section>
    """,
        "html.parser",
    )  # html.parser doesn't create <html>/<body> tags automatically

    html = BeautifulSoup(content, "lxml")
    for br in html.find_all("br"):
        # Check if no content after br
        if not br.next_sibling or br.next_sibling.name in ["br", None]:
            br.decompose()

    section = cast(bs4.Tag, clean.find("section"))
    if not section:
        raise Exception()

    for child in html.find_all("p"):
        current_paragraph = clean.new_tag("p")

        # Attempt to carry over paragraph styling
        current_paragraph["style"] = child.get("style", "text-align: left;")

        for p_child in list(child.children):
            if not p_child:
                continue
            if isinstance(p_child, bs4.element.Tag):
                if p_child.name == "br":
                    p_child.decompose()
                elif p_child.name == "img":
                    src = p_child["src"]
                    img_tag = clean.new_tag("img")
                    img_tag["src"] = src
                    section.append(img_tag)
                    section.append(clean.new_tag("br"))
                elif p_child.name in ["b", "i"]:
                    styled_tag = clean.new_tag(p_child.name)
                    styled_content = clean.new_string(p_child.text)
                    styled_tag.append(styled_content)
                    current_paragraph.append(styled_tag)
                else:
                    # Append any other tags as-is
                    current_paragraph.append(p_child)
            elif isinstance(p_child, bs4.element.NavigableString):
                content = clean.new_string(p_child)
                current_paragraph.append(content)

        if current_paragraph.contents:
            section.append(current_paragraph)

        if not list(child.children):
            # Some p tags only contain brs, once brs are removed, they are empty and can be removed as well.
            child.decompose()

    return section


def slugify(value, allow_unicode=False) -> str:
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.

    Thanks https://stackoverflow.com/a/295466.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")
