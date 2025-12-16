#wikimedia_scraper.py
#import necessary libraries
# wikimedians_scraper.py
import os
import re
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from slugify import slugify

BASE_URL = "https://meta.wikimedia.org"
EVENTS_INDEX_URL = "https://meta.wikimedia.org/wiki/Wikimedians_of_Kerala/Activities/Events"
CONTENT_DIR = "content/events"
STATIC_IMG_DIR = "static/images/events"

os.makedirs(CONTENT_DIR, exist_ok=True)
os.makedirs(STATIC_IMG_DIR, exist_ok=True)


def clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_html(url: str) -> BeautifulSoup:
    resp = requests.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def extract_event_links() -> list:
    """
    From the events index page, collect links to individual event pages.
    Adjust selectors if Meta changes layout.
    """
    soup = fetch_html(EVENTS_INDEX_URL)
    links = []

    # Typical pattern on Meta: lists of links under content div
    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        return links

    for a in content_div.select("a[href]"):
        href = a["href"]
        title = a.get_text(strip=True)
        # Filter only event pages under Wikimedians_of_Kerala/Events
        if (
            href.startswith("/wiki/Wikimedians_of_Kerala/Events")
            or href.startswith("/wiki/Event:Wikimedians_of_Kerala")
        ):
            full_url = BASE_URL + href
            links.append((clean_title(title), full_url))

    # Deduplicate by URL
    seen = set()
    unique = []
    for title, url in links:
        if url not in seen:
            seen.add(url)
            unique.append((title, url))
    return unique


def download_image(img_url: str, event_slug: str, idx: int) -> str:
    if img_url.startswith("//"):
        img_url = "https:" + img_url
    elif img_url.startswith("/"):
        img_url = BASE_URL + img_url

    ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
    filename = f"{event_slug}-{idx}{ext}"
    local_path = os.path.join(STATIC_IMG_DIR, filename)

    try:
        r = requests.get(img_url, stream=True, timeout=20)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        # Hugo static path (without 'static/')
        return f"/images/events/{filename}"
    except Exception as e:
        print(f"[img-error] {img_url} -> {e}")
        return ""


def extract_event_page(title: str, url: str):
    soup = fetch_html(url)

    # Get the title from page if available
    h1 = soup.find("h1", id="firstHeading")
    page_title = clean_title(h1.get_text()) if h1 else title

    # Main content area
    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        html_content = ""
    else:
        # Clone to avoid mutating soup
        content_clone = BeautifulSoup(str(content_div), "lxml")

        # Strip irrelevant elements (edit sections, TOC, nav boxes)
        for el in content_clone.select(".mw-editsection, #toc, .navbox, .metadata"):
            el.decompose()

        html_content = str(content_clone)

    # Extract images
    images = []
    if content_div:
        for idx, img in enumerate(content_div.select("img"), start=1):
            src = img.get("src")
            if not src:
                continue
            local_url = download_image(src, slugify(page_title)[:40], idx)
            if local_url:
                images.append(local_url)

    # Convert HTML to Markdown
    body_md = md(html_content, heading_style="ATX")

    return page_title, body_md, images


def write_markdown_file(title: str, body_md: str, images: list, source_url: str):
    slug = slugify(title) or "event"
    filename = os.path.join(CONTENT_DIR, f"{slug}.md")

    front_matter = [
        "+++",
        f'title = "{title.replace(\'"\', "\\\"")}"',
        f'slug = "{slug}"',
        f'url = "/events/{slug}/"',
        f'source = "{source_url}"',
    ]
    if images:
        front_matter.append("images = [")
        for img in images:
            front_matter.append(f'  "{img}",')
        front_matter.append("]")
    front_matter.append("+++")
    front_matter_str = "\n".join(front_matter)

    # Optional header in content
    content = f"{front_matter_str}\n\n{body_md}\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[ok] {filename}")


def main():
    events = extract_event_links()
    print(f"Found {len(events)} event links")
    for title, url in events:
        try:
            print(f"[event] {title} -> {url}")
            page_title, body_md, images = extract_event_page(title, url)
            write_markdown_file(page_title, body_md, images, url)
        except Exception as e:
            print(f"[error] {title} ({url}): {e}")


if __name__ == "__main__":
    main()






















""
""