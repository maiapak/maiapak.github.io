"""Takes a full-page screenshot of the SCIDR homepage for the Consumer Research page.

Run by .github/workflows/update-scidr-screenshot.yml on a schedule, or by hand:
    pip install playwright pillow
    python scripts/update_scidr_screenshot.py
Uses the Google Chrome already installed on the machine.
"""
import io
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

URL = "https://scidr.stanford.edu/"
OUT = Path(__file__).resolve().parent.parent / "images" / "scidr-site.jpg"
VIEWPORT_WIDTH = 1280   # page is laid out as on a laptop
OUTPUT_WIDTH = 1440     # sharp on Retina at the size the box is shown

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": 800}, device_scale_factor=1.5)
    page.goto(URL, wait_until="networkidle", timeout=60000)
    # scroll to the bottom and back so lazy-loaded images appear in the screenshot
    height = page.evaluate("document.body.scrollHeight")
    for y in range(0, height, 600):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(150)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)
    png = page.screenshot(full_page=True)
    browser.close()

img = Image.open(io.BytesIO(png)).convert("RGB")
img = img.resize((OUTPUT_WIDTH, round(img.height * OUTPUT_WIDTH / img.width)), Image.LANCZOS)


def looks_the_same(a, b):
    """True if the page hasn't visibly changed (ignores tiny JPEG/rendering noise)."""
    if a.size != b.size:
        return False
    small = (a.width // 8, a.height // 8)
    diff = ImageChops.difference(a.resize(small).convert("L"), b.resize(small).convert("L"))
    return max(ImageStat.Stat(diff).mean) < 1.5


if OUT.exists() and looks_the_same(img, Image.open(OUT).convert("RGB")):
    print("no visible change; keeping the existing screenshot")
else:
    img.save(OUT, "JPEG", quality=82, optimize=True, progressive=True)
    print(f"saved {OUT} ({img.width}x{img.height})")
