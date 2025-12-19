import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from bezoekersparkeren.config import Config
from bezoekersparkeren.license_plate_recognition import recognize_plate

async def main():
    # Load config
    try:
        config = Config.load()
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # Check API key
    if not config.openrouter.api_key:
        print("Error: PARKEER_OPENROUTER_API_KEY not set in .env or config.yaml")
        print("Please set it to run this test.")
        return

    # Check for test image
    image_path = Path("test_car.jpg")
    if not image_path.exists():
        print(f"Error: {image_path} not found.")
        print("Please place a 'test_car.jpg' in this directory to test.")
        return

    print(f"Testing License Plate Recognition on {image_path}...")
    print(f"Using model: {config.openrouter.model}")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    result = await recognize_plate(image_bytes, config)
    
    if result:
        print(f"\nSUCCESS! Recognized plate: {result}")
    else:
        print("\nFAILED. Could not recognize plate (or returned NONE).")

if __name__ == "__main__":
    asyncio.run(main())
