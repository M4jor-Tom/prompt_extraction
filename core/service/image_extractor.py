import requests
import os
from urllib.parse import urlparse
import logging

from core.constant import images_selector
from . import BrowserManager
from core.util import DONE_PREFIX, enter_feed_view

logger = logging.getLogger(__name__)

class ImageExtractor:
    browser_manager: BrowserManager

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager

    async def save_images_from_page(self, output_dir_in_home: str) -> None:
        """Save all image files from a web page using Playwright.

        Args:
            output_dir_in_home: Directory where images will be saved.
        """
        output_dir: str = os.environ['HOME'] + '/' + output_dir_in_home
        await enter_feed_view(self.browser_manager.page)
        os.makedirs(output_dir, exist_ok=True)
        img_elements = await self.browser_manager.page.locator(images_selector).all()
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
