#!./python

import re
import lxml.etree as ET
from fastapi import FastAPI, HTTPException, UploadFile, File
from playwright.async_api import async_playwright
from playwright_stealth.stealth import stealth_async
from contextlib import asynccontextmanager
import asyncio
import requests

from pydantic import BaseModel

# ANSI color codes for colored output
COLOR_OK = "\033[92m"       # Green
COLOR_ERROR = "\033[91m"    # Red
COLOR_WARNING = "\033[93m"  # Yellow
COLOR_RESET = "\033[0m"     # Reset color

civitai_selectors: dict[str, str] = {
    'positivePromptArea': "#input_prompt",
    'negativePromptArea': "#input_negativePrompt",
    'cfgScaleHiddenInput': "#mantine-rf-panel-advanced > div > div > div > div.relative.flex.flex-col.gap-3 > div:nth-child(1) > div > div.mantine-Slider-root.flex-1.mantine-15k342w > input[type=hidden]",
    'cfgScaleTextInput': "#mantine-rh",
    'samplerHiddenInput': "#mantine-rf-panel-advanced > div > div > div > div.relative.flex.flex-col.gap-3 > div.mantine-InputWrapper-root.mantine-Select-root.mantine-1m3pqry > div > input[type=hidden]",
    'samplerSearchInput': "#input_sampler",
    'stepsHiddenInput': "#mantine-rf-panel-advanced > div > div > div > div.relative.flex.flex-col.gap-3 > div:nth-child(3) > div > div.mantine-Slider-root.flex-1.mantine-15k342w > input[type=hidden]",
    'stepsTextInput': "#mantine-rj"
}

# Global variables
browser = None
civitai_page = None
signed_in_civitai_generation_url: str = None
civitai_generation_url: str = 'https://civitai.com/generate'
civitai_user_page_url: str = 'https://civitai.com/user/account'
browser_ready_event = asyncio.Event()
global_timeout: int = 60000

class URLInput(BaseModel):
    url: str

async def try_action(action_name: str, callback):
    try:
        print("⏳ [WAIT] " + action_name)
        await callback()
        print("✅ [DONE] " + action_name)
    except Exception as e:
        print("⚠️ [SKIP] " + action_name + ": " + str(e))

async def click_if_visible(action_name: str, locator):
    if await locator.is_visible():
        await locator.click()
        print("✅ [DONE] Clicked locator for " + action_name)
    else:
        print("⚠️ [SKIP] Locator for " + action_name + " not visible")

def fetch_xsd(xsd_url: str) -> ET.XMLSchema:
    """Fetches an XSD file from a URL and returns an XMLSchema object.

    Args:
        xsd_url: URL of the XSD schema.

    Returns:
        XMLSchema object if successfully fetched, else None.
    """
    try:
        response = requests.get(xsd_url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP failures

        xsd_tree = ET.XML(response.content)
        return ET.XMLSchema(xsd_tree)
    except requests.RequestException as e:
        print(f"{COLOR_ERROR}[ERROR] Failed to fetch XSD from {xsd_url}: {e}{COLOR_RESET}")
        return None
    except ET.XMLSyntaxError as e:
        print(f"{COLOR_ERROR}[ERROR] Invalid XSD format from {xsd_url}: {e}{COLOR_RESET}")
        return None

async def remove_cookies():
    async def interact():
        await civitai_page.get_by_text("Customise choices").wait_for(state="visible", timeout=global_timeout)
        await civitai_page.get_by_text("Customise choices").click()
        await civitai_page.get_by_text("Save preferences").click()
    await try_action("remove_cookies", interact)

async def enter_parameters_perspective():
    async def interact():
        await civitai_page.locator('div[title]').first.click()
        await civitai_page.locator('a[href="/user/account"]').first.click()
    await try_action("enter_parameters_perspective", interact)

async def enable_mature_content():
    async def interact():
        await civitai_page.locator('div:has-text("Show mature content")').first.click()
        await civitai_page.locator('div:has-text("Blur mature content")').first.click()
        # await civitai_page.locator('div:has-text("PG")').first.click()
        await civitai_page.locator('div:has-text("Safe for work. No naughty stuff")').first.click()
        # await civitai_page.locator('div:has-text("PG-13")').first.click()
        await civitai_page.locator('div:has-text("Revealing clothing, violence, or light gore")').first.click()
        # await civitai_page.locator('div:has-text("R")').first.click()
        await civitai_page.locator('div:has-text("Adult themes and situations, partial nudity, graphic violence, or death")').first.click()
        # await civitai_page.locator('div:has-text("X")').first.click()
        await civitai_page.locator('div:has-text("Graphic nudity, adult objects, or settings")').first.click()
        # await civitai_page.locator('div:has-text("XXX")').first.click()
        await civitai_page.locator('div:has-text("Overtly sexual or disturbing graphic content")').first.click()
    await try_action("enable_mature_content", interact)

async def enter_generation_perspective():
    async def interact():
        await civitai_page.locator('button[data-activity="create:navbar"]').first.click()
        await civitai_page.locator('a[href="/generate"]').first.click()
    await try_action("enter_generation_perspective", interact)
    # await civitai_page.goto(civitai_generation_url)

async def skip_getting_started():
    async def interact():
        await civitai_page.get_by_role("button", name="Skip").wait_for(state="visible", timeout=global_timeout)
        await civitai_page.get_by_role("button", name="Skip").click()
    await try_action("skip_getting_started", interact)

async def confirm_start_generating_yellow_button():
    await click_if_visible("confirm_start_generating_yellow_button", civitai_page.get_by_role("button", name="I Confirm, Start Generating"))

async def claim_buzz():
    await click_if_visible("claim_buzz", civitai_page.locator('button:has-text("Claim 25 Buzz")'))

async def prepare_session():
    await remove_cookies()
    await skip_getting_started()
    await confirm_start_generating_yellow_button()
    await claim_buzz()
    # await enter_parameters_perspective()
    # await enable_mature_content()
    await enter_generation_perspective()

async def init_browser():
    """Initializes the browser when the URL is set."""
    global browser, civitai_page, signed_in_civitai_generation_url

    print(f"⏳ Waiting for URL to initialize the browser...")

    # Wait until an URL is set
    while signed_in_civitai_generation_url is None:
        await asyncio.sleep(1)

    print(f"✅ URL received: {signed_in_civitai_generation_url}")

    # Start Playwright
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        locale="en-US",
        viewport={"width": 1920, "height": 1080},
        java_script_enabled=True,
        ignore_https_errors=True,
        timezone_id="America/New_York",
        permissions=["geolocation"],
    )

    civitai_page = await context.new_page()

    # Load the provided URL
    await civitai_page.goto(signed_in_civitai_generation_url)

    await civitai_page.wait_for_selector("#__next", timeout=global_timeout)

    try:
        await civitai_page.wait_for_load_state("domcontentloaded", timeout=global_timeout)
    except Exception:
        print("⚠️ Warning: Page load state took too long, continuing anyway.")

    await asyncio.sleep(5)

    # Apply stealth mode
    await stealth_async(civitai_page)

    print("✅ Browser initialized with anti-bot protections")
    browser_ready_event.set()  # Notify that the browser is ready
    await prepare_session()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan function that starts FastAPI without blocking Swagger and browser startup."""
    print("🚀 FastAPI is starting...")

    # Start the browser initialization in a background task
    asyncio.create_task(init_browser())

    yield  # Allow FastAPI to run

    # Shutdown sequence
    if browser:
        await civitai_page.close()
        await browser.close()
        print("🛑 Browser closed!")

app = FastAPI(lifespan=lifespan)

@app.post("/set_generation_url")
async def set_generation_url(data: URLInput):
    """Sets the signed-in CivitAI generation URL and unblocks the browser startup."""
    global signed_in_civitai_generation_url

    if not data.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    signed_in_civitai_generation_url = data.url
    return {"message": "URL set successfully; Session prepared for xml injection", "url": signed_in_civitai_generation_url}

@app.post("/inject_prompt")
async def inject_prompt(file: UploadFile = File(...)):
    """Validates an uploaded XML file against an XSD schema from a given URL.

    Returns:
        A JSON response indicating whether the XML is valid or not.
    """
    try:
        # Read XML content
        xml_content = await file.read()
        xml_tree = ET.ElementTree(ET.fromstring(xml_content))
        root = xml_tree.getroot()

        # Extract xsi:noNamespaceSchemaLocation (URL or file path)
        xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
        xsd_location = root.attrib.get(f"{{{xsi_ns}}}noNamespaceSchemaLocation")

        # Parse the XSD schema
        if xsd_location.startswith(("http://", "https://")):
            xsd_schema = fetch_xsd(xsd_location)
            if not xsd_schema:
                return {"message": "Failed to fetch the XSD"}

        # Validate XML against the schema
        if xsd_schema.validate(xml_tree):
            return {"message": "XML is valid against the provided XSD"}
        else:
            errors = xsd_schema.error_log
            return {"message": "XML validation failed", "errors": errors.last_error}

    except ET.XMLSyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/open_settings_pre_menu")
async def open_settings_pre_menu():
    await civitai_page.get_by_role("button").filter(has_text="EA125").click()

@app.get("/open_settings_menu")
async def open_settings_menu():
    await civitai_page.get_by_label("EA125").get_by_role("link").filter(has_text=re.compile(r"^$")).click()

@app.get("/write_positive_prompt")
async def write_positive_prompt():
    await civitai_page.get_by_role("textbox", name="Your prompt goes here...").click()
    await civitai_page.get_by_role("textbox", name="Your prompt goes here...").fill("positive prompt")

@app.get("/write_negative_prompt")
async def write_negative_prompt():
    await civitai_page.get_by_role("textbox", name="Negative Prompt").click()
    await civitai_page.get_by_role("textbox", name="Negative Prompt").fill("negative prompt")

@app.get("/set_ratio_portrait")
async def set_ratio_portrait():
    await civitai_page.locator("label").filter(has_text="Portrait832x1216").click()

@app.get("/set_ratio_landscape")
async def set_ratio_landscape():
    await civitai_page.locator("label").filter(has_text="Landscape1216x832").click()

@app.get("/set_ratio_square")
async def set_ratio_square():
    await civitai_page.locator("label").filter(has_text="Square1024x1024").click()

@app.get("/toggle_image_properties_accordion")
async def toggle_image_properties_accordion():
    await civitai_page.get_by_role("button", name="Advanced").click()

@app.get("/set_cfg_scale")
async def set_cfg_scale():
    await civitai_page.locator("#mantine-r63").fill("4")

@app.get("/set_steps")
async def set_steps():
    await civitai_page.locator("#mantine-r65").fill("50")

@app.get("/set_seed")
async def set_seed():
    await civitai_page.get_by_role("textbox", name="Random").fill("5555")

global previous_priority, next_priority
previous_priority: str = "Standard"
next_priority: str = "High +"
@app.get("/set_priority")
async def set_priority():
    standard: str = "Standard"
    high: str = "High +"
    highest: str = "Highest +"
    await civitai_page.get_by_role("button", name=previous_priority).click()
    await civitai_page.get_by_role("option", name=next_priority).locator("div").first.click()
    previous_priority=next_priority

@app.get("/enter_base_model_selection")
async def enter_base_model_selection():
    await civitai_page.get_by_role("button", name="Swap").click()

@app.get("/enter_advanced_mode")
async def enter_advanced_mode():
    await civitai_page.locator("#mantine-r9q-body label").first.click()

@app.get("/select_base_model_by_normal_click")
async def select_base_model_by_normal_click():
    await civitai_page.locator("div").filter(has_text=re.compile(r"^Pony Diffusion V6 XLSelect$")).get_by_role("button").click()

@app.get("/select_base_model_by_create_button")
async def select_base_model_by_create_button():
    await civitai_page.goto("https://civitai.com/models/257749?modelVersionId=290640")
    await civitai_page.get_by_role("main").get_by_role("button", name="Create").click()

@app.get("/reopen_generation_perspective_after_selecting_model_by_create_button")
async def reopen_generation_perspective_after_selecting_model_by_create_button():
    await civitai_page.locator("div:nth-child(3) > button").first.click()

@app.get("/toggle_additional_resources_accordion")
async def toggle_additional_resources_accordion():
    await civitai_page.get_by_role("button", name="Additional Resources 1/9 Add").click()

@app.get("/set_additional_resource_wheight")
async def set_additional_resource_wheight():
    await civitai_page.locator("#mantine-rim").fill("6")

@app.get("/generate")
async def generate():
    await civitai_page.get_by_role("button", name="Generate").click()

async def codegen():
    await civitai_page.get_by_role("button", name="BA 100").click()
    await civitai_page.get_by_label("BA100").get_by_role("link").filter(has_text=re.compile(r"^$")).click()
    await civitai_page.locator(".flex > .mantine-Switch-root > .mantine-uetonu > .mantine-h12aau > .mantine-155cra4").click()
    await civitai_page.locator("#content-moderation label").first.click()
    await civitai_page.locator("div:nth-child(2) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-69c9zd").first.click()
    await civitai_page.locator("div:nth-child(2) > div:nth-child(2) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-155cra4").click()
    await civitai_page.locator(".mantine-Paper-root > div:nth-child(3) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12").click()
    await civitai_page.locator("div:nth-child(4) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-155cra4").first.click()
    await civitai_page.locator("div:nth-child(5) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-155cra4").click()
    await civitai_page.get_by_role("button", name="Create").click()
    # await civitai_page.get_by_role("button", name="Skip").click() REST
    # await civitai_page.locator("div:nth-child(3) > button").first.click() REST
    await civitai_page.get_by_role("button", name="Swap").click()
    await civitai_page.locator("div").filter(has_text=re.compile(r"^Pony Diffusion V6 XLSelect$")).get_by_role("button").click()
    await civitai_page.get_by_role("button", name="Claim 25 Buzz").click()
    # await civitai_page.get_by_role("button", name="I Confirm, Start Generating").click() REST
    # await civitai_page.get_by_role("textbox", name="Your prompt goes here...").click()
    # await civitai_page.get_by_role("textbox", name="Your prompt goes here...").fill("positive prompt")
    # await civitai_page.get_by_role("textbox", name="Negative Prompt").click()
    # await civitai_page.get_by_role("textbox", name="Negative Prompt").fill("negative prompt")
    await civitai_page.get_by_text("Portrait").click()
    await civitai_page.locator("label").filter(has_text="Portrait832x1216").click()
    await civitai_page.locator(".mantine-69c9zd").first.click()
    await civitai_page.get_by_role("button", name="Advanced").click()
    await civitai_page.locator("#mantine-rfl").dblclick()
    await civitai_page.locator("#mantine-rfl").fill("4.0")
    await civitai_page.get_by_role("searchbox", name="Sampler Fast Popular").click()
    await civitai_page.get_by_role("option", name="DPM++ 2M Karras").click()
    await civitai_page.locator("#mantine-rfn").dblclick()
    await civitai_page.locator("#mantine-rfn").fill("30")
    await civitai_page.get_by_text("WorkflowNewModel *Pony").click()
    await civitai_page.get_by_role("searchbox", name="Sampler Fast Popular").click()
    await civitai_page.locator("#mantine-rkt-target").click()
    await civitai_page.locator("#mantine-rl0").dblclick()
    await civitai_page.locator("#mantine-rl0").fill("0%")
    await civitai_page.locator("#input_quantity").dblclick()
    await civitai_page.locator("#input_quantity").fill("4")
    await civitai_page.get_by_role("button", name="Generate Blue: 19 | Yellow: 0").click()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("civitaikido:app", host="127.0.0.1", port=8000, reload=True)
