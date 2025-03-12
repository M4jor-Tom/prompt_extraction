#!./python

import re
from fastapi import FastAPI
from playwright.async_api import async_playwright
from playwright_stealth.stealth import stealth_async
from contextlib import asynccontextmanager
import asyncio

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

# civitai_generation_url: str = "https://civitai.com/generate"
civitai_generation_url: str = "https://civitai.com/api/auth/callback/email?callbackUrl=https%3A%2F%2Fcivitai.com%2Fgenerate&token=bd2e552373b0d5dbf15628c4bbf7b0a9a73c06ad7c585312db7ec631c49703bf&email=eastern.panther.zzbr%40letterhaven.net"
# adguard_mails_page_url: str = "https://adguard.com/fr/adguard-temp-mail/overview.html"

# Global variables
browser = None
civitai_page = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and close Playwright browser properly."""
    global browser, civitai_page

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        locale="en-US",
        viewport={"width": 1920, "height": 1080},
        java_script_enabled=True,  # Keep JS enabled
        ignore_https_errors=True,  # Bypass HTTPS issues
        timezone_id="America/New_York",  # Set a realistic timezone
        permissions=["geolocation"],  # Allow real geolocation
    )

    civitai_page = await context.new_page()

    # ✅ Ensure opts is defined to prevent ReferenceError
    await civitai_page.add_init_script("window.opts = {};")

    # ✅ Set auth headers (if required)
    await civitai_page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    })

    await civitai_page.goto(civitai_generation_url)

    # ✅ Ensure React fully loads before injecting scripts
    await civitai_page.wait_for_selector("#__next", timeout=15000)  # Wait for Next.js root

    try:
        await civitai_page.wait_for_load_state("domcontentloaded", timeout=15000)  # Avoids networkidle timeout
    except Exception:
        print("⚠️ Warning: Page load state took too long, continuing anyway.")

    await asyncio.sleep(5)  # Ensure JavaScript finishes executing

    # ✅ Apply stealth AFTER page has fully loaded
    await stealth_async(civitai_page)

    print("✅ Browser running with anti-bot protections")
    yield

    await browser.close()
    await playwright.stop()
    print("🛑 Browser closed!")

app = FastAPI(lifespan=lifespan)

@app.get("/extract-prompt")
async def extract_prompt():
    """Scrapes and returns text content from CivitAI using predefined selectors."""
    if not civitai_page:
        return {"error": "Browser not initialized"}

    prompt_scraps = {}

    for field, selector in civitai_selectors.items():
        try:
            element = await civitai_page.query_selector(selector)
            text = await element.inner_text() if element else "Not found"
            prompt_scraps[field] = text
        except Exception as e:
            prompt_scraps[field] = f"Error: {e}"

    return {"content": prompt_scraps}

@app.get("/remove_cookies")
async def remove_cookies():
    await civitai_page.get_by_text("Customise choices").click()
    await civitai_page.get_by_text("Save preferences").click()

@app.get("/skip_getting_started")
async def skip_getting_started():
    await civitai_page.get_by_role("button", name="Skip").click()

@app.get("/confirm_start_generating_yellow_button")
async def confirm_start_generating_yellow_button():
    await civitai_page.get_by_role("button", name="I Confirm, Start Generating").click()

@app.get("/open_settings_pre_menu")
async def open_settings_pre_menu():
    await civitai_page.get_by_role("button").filter(has_text="EA125").click()

@app.get("/open_settings_menu")
async def open_settings_menu():
    await civitai_page.get_by_label("EA125").get_by_role("link").filter(has_text=re.compile(r"^$")).click()

@app.get("/enable_mature_content")
async def enable_mature_content():
    await civitai_page.locator("div:nth-child(2) > .mantine-uetonu > .mantine-17s5p12 > .mantine-155cra4").first.click()
    await civitai_page.locator("div:nth-child(2) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-69c9zd").first.click()
    await civitai_page.locator("div:nth-child(2) > div:nth-child(2) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-69c9zd").click()
    await civitai_page.locator(".mantine-Paper-root > div:nth-child(3) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-69c9zd").click()
    await civitai_page.locator("div:nth-child(4) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-69c9zd").first.click()
    await civitai_page.locator("div:nth-child(5) > .mantine-Switch-root > .mantine-uetonu > .mantine-17s5p12 > .mantine-155cra4").click()

@app.get("/enter_generation_perspective")
async def enter_generation_perspective():
    await civitai_page.locator("div:nth-child(3) > button").first.click()

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

@app.get("/close")
async def close():
    await civitai_page.close()

@app.get("/codegen")
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
    uvicorn.run("civitai_extractor:app", host="127.0.0.1", port=8000, reload=True)
