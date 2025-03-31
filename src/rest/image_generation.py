from fastapi import APIRouter, Depends

from src.provider import get_image_generator
from src.service import ImageGenerator

image_generation_router = APIRouter()

@image_generation_router.post("/generate_till_no_buzz")
async def generate_till_no_buzz(image_generator: ImageGenerator = Depends(get_image_generator)):
    await image_generator.generate_till_no_buzz()
