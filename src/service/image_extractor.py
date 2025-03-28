from playwright.async_api import async_playwright
import requests
import os
from urllib.parse import urlparse
import logging

from src.constant import images_selector, feed_perspective_button_selector
from src.util import DONE_PREFIX

logger = logging.getLogger(__name__)

class ImageExtractor:
    page: any

    def __init__(self, page):
        self.page = page

    async def enter_feed_view(self):
        await self.page.locator(feed_perspective_button_selector).first.click()

    async def save_images_from_page(self, output_dir_in_home: str) -> None:
        """Save all image files from a web page using Playwright.

        Args:
            output_dir_in_home: Directory where images will be saved.
        """
        output_dir: str = os.environ['HOME'] + '/' + output_dir_in_home
        await self.enter_feed_view()
        os.makedirs(output_dir, exist_ok=True)
        img_elements = await self.page.locator(images_selector).all()
        for i, img in enumerate(img_elements):
            src = await img.get_attribute("src")
            if not src:
                continue
            # Make sure to handle relative URLs
            # img_url = urljoin(url, src)
            img_url = src
            try:
                response = requests.get(img_url)
                response.raise_for_status()
                # Extract a filename from the URL or fallback to index
                filename = os.path.basename(urlparse(img_url).path) or f"image_{i}.jpg"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info(DONE_PREFIX + f"Saved: {filepath}")
            except Exception as e:
                logger.error(f"Failed to download {img_url}: {e}")
