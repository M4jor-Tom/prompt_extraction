from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from playwright.async_api import async_playwright
from playwright_stealth.stealth import stealth_async
import asyncio
import logging
from src.constant import *

logger = logging.getLogger(__name__)

class BrowserManager:
    browser: any
    page: any
    signed_in_civitai_generation_url: str | None
    browser_ready_event: any
    browser_initialized: bool

    def __init__(self):
        self.browser = None
        self.page = None
        self.signed_in_civitai_generation_url = None
        self.browser_ready_event = asyncio.Event()
        self.browser_initialized = False

    async def init_browser(self):
        """Initializes the browser when the URL is set."""
        logger.info(WAIT_PREFIX + "Browser to initialise...")

        # Wait until an URL is set
        while self.signed_in_civitai_generation_url is None:
            await asyncio.sleep(1)

        logger.info(DONE_PREFIX + "URL received: " + str(self.signed_in_civitai_generation_url))

        # Start Playwright
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)

        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            locale="en-US",
            # locale="fr-FR",
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            ignore_https_errors=True,
            # timezone_id="America/New_York",
            timezone_id="Europe/Paris",
            # geolocation={"latitude": 43.1242, "longitude": 5.9280},
            permissions=["geolocation"]
        )
        context.set_default_timeout(global_timeout)

        self.page = await context.new_page()
        # await self.page.add_init_script(path="stealth.m#in.js")

        # Load the provided URL
        await self.page.goto(self.signed_in_civitai_generation_url)

        await self.page.wait_for_selector("#__next", timeout=global_timeout)

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=global_timeout)
        except Exception:
            logger.warn(SKIP_PREFIX + "Page load state took too long, continuing anyway.")

        await asyncio.sleep(5)

        # Apply stealth mode
        await stealth_async(self.page)

        logger.info(DONE_PREFIX + "Browser initialized with anti-bot protections")
        self.browser_ready_event.set()  # Notify that the browser is ready
        self.browser_initialized = True

    async def shutdown_if_possible(self) -> None:
        # Shutdown sequence
        if self.browser:
            await self.page.close()
            await self.browser.close()
            logger.info("🛑 Browser closed!")
