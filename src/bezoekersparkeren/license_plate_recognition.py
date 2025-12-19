import base64
import re
import logging
import httpx
from typing import Optional

from bezoekersparkeren.config import Config

logger = logging.getLogger(__name__)

async def recognize_plate(image_bytes: bytes, config: Config) -> Optional[str]:
    """
    Recognize license plate from image bytes using OpenRouter Vision API.
    
    Args:
        image_bytes: Raw bytes of the image
        config: Application configuration
        
    Returns:
        Recognized license plate string (normalized) or None if failed/invalid
    """
    if not config.openrouter.api_key:
        logger.error("No OpenRouter API key configured")
        return None

    # Encode image to base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {config.openrouter.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/DanielTromp/bezoekersparkeren",
        "X-Title": "Bezoekersparkeren Almere Bot"
    }

    payload = {
        "model": config.openrouter.model,
        "messages": [
            {
                "role": "system",
                "content": "You are a License Plate Recognition system. Analyze the image. Return ONLY the license plate string. Remove all spaces and dashes. Convert to UPPERCASE. If no plate is clearly visible, return strictly the string 'NONE'. Do not add markdown formatting, do not add explanations. Example output: 'AB123CD'."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            if not data.get("choices"):
                logger.error("No choices in OpenRouter response")
                return None
                
            content = data["choices"][0]["message"]["content"].strip()
            
            # Basic validation
            if content == "NONE":
                return None
                
            # Remove any Markdown code blocks if the model hallucinates them (despite prompt)
            content = content.replace("```", "").strip()
            
            # Validate format (Dutch plates are roughly 6 chars alnum, but let's be slightly flexible 6-8)
            # Remove any dashes/spaces just in case model forgot
            clean_plate = re.sub(r'[^A-Z0-9]', '', content.upper())
            
            if not (6 <= len(clean_plate) <= 8):
                logger.warning(f"Invalid plate length recognized: {clean_plate} (original: {content})")
                return None
                
            return clean_plate

    except Exception as e:
        logger.exception(f"Error calling OpenRouter API: {e}")
        return None
