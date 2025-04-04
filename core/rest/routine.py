import asyncio

from fastapi import APIRouter, Depends, Form, File, UploadFile

from core.constant import main
from core.config import GENERATION_DEFAULT_DIR
from core.model.injection_extraction_state import InjectionExtractionState
from core.provider import get_image_generator, get_browser_manager, get_civitai_page_preparator, get_prompt_injector, \
    get_prompt_builder, get_xml_parser, get_image_extractor, get_popup_remover, get_state_manager
from core.service import ImageGenerator, BrowserManager, CivitaiPagePreparator, PromptInjector, PromptBuilder, XmlParser, \
    ImageExtractor, PopupRemover, StateManager

routine_router = APIRouter()

@routine_router.post("/inject_generate_extract", tags=[main])
async def inject_generate_extract(
        session_url: str = Form(...),
        file: UploadFile = File(...),
        inject_seed: bool = False,
        close_browser_when_finished: bool = True,
        state_manager: StateManager = Depends(get_state_manager),
        browser_manager: BrowserManager = Depends(get_browser_manager),
        civitai_page_preparator: CivitaiPagePreparator = Depends(get_civitai_page_preparator),
        popup_remover: PopupRemover = Depends(get_popup_remover),
        prompt_injector: PromptInjector = Depends(get_prompt_injector),
        prompt_builder: PromptBuilder = Depends(get_prompt_builder),
        xml_parser: XmlParser = Depends(get_xml_parser),
        image_generator: ImageGenerator = Depends(get_image_generator),
        image_extractor: ImageExtractor = Depends(get_image_extractor)
    ):
    ask_first_session_preparation: bool = True
    await browser_manager.open_browser(session_url)
    async def interact():
        await civitai_page_preparator.prepare_civitai_page(ask_first_session_preparation)
        state_manager.injection_extraction_state = InjectionExtractionState.PAGE_PREPARED
        await prompt_injector.inject(prompt_builder.build_from_xml(await xml_parser.parse_xml(file)), inject_seed)
        state_manager.injection_extraction_state = InjectionExtractionState.PROMPT_INJECTED
        await image_generator.generate_all_possible()
        state_manager.injection_extraction_state = InjectionExtractionState.IMAGES_GENERATED
        await image_extractor.save_images_from_page(GENERATION_DEFAULT_DIR + "/" + str(file.filename).split('.xml')[0])
        state_manager.injection_extraction_state = InjectionExtractionState.IMAGES_EXTRACTED
        if close_browser_when_finished:
            await browser_manager.shutdown_if_possible()
    await asyncio.gather(
        popup_remover.remove_popups(ask_first_session_preparation),
        interact()
    )
