"""Takes full-page screenshots of the websites shown on the Consumer Research page.

Run by .github/workflows/update-scidr-screenshot.yml on a schedule, or by hand:
    pip install playwright pillow
    python scripts/update_scidr_screenshot.py
Uses the Google Chrome already installed on the machine.
"""
import io
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

IMAGES = Path(__file__).resolve().parent.parent / "images"
# (address, file to save, browser width to lay the page out at, width of the saved image)
# Wellness House is a narrow column on black, so it's captured at the column's width.
SITES = [
    ("https://scidr.stanford.edu/", "scidr-site.jpg", 1280, 1440),
    ("https://www.wellnesshouse-seoul.com/ko", "wellnesshouse-site.jpg", 600, 900),
]


def screenshot(browser, url, viewport_width):
    page = browser.new_page(viewport={"width": viewport_width, "height": 800}, device_scale_factor=1.5)
    page.goto(url, wait_until="networkidle", timeout=60000)
    # scroll to the bottom and back so lazy-loaded images appear in the screenshot
    height = page.evaluate("document.body.scrollHeight")
    for y in range(0, height, 600):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(150)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1500)
    png = page.screenshot(full_page=True)
    page.close()
    return Image.open(io.BytesIO(png)).convert("RGB")


def looks_the_same(a, b):
    """True if the page hasn't visibly changed (ignores tiny JPEG/rendering noise)."""
    if a.size != b.size:
        return False
    small = (a.width // 8, a.height // 8)
    diff = ImageChops.difference(a.resize(small).convert("L"), b.resize(small).convert("L"))
    return max(ImageStat.Stat(diff).mean) < 1.5


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    for url, name, viewport_width, width in SITES:
        out = IMAGES / name
        img = screenshot(browser, url, viewport_width)
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
        if out.exists() and looks_the_same(img, Image.open(out).convert("RGB")):
            print(f"{name}: no visible change; keeping the existing screenshot")
        else:
            img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
            print(f"{name}: saved ({img.width}x{img.height})")
    browser.close()
