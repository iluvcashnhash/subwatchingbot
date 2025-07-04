from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Literal, TypedDict, Union

import aiohttp
from pydantic import BaseModel, Field, field_validator

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Type definitions
IntentType = Literal["add", "delete", "update", "list", "total"]

class SubscriptionIntent(BaseModel):
    """Structured intent data extracted from user messages."""
    intent: IntentType
    service: str | None = None
    amount: float | None = None
    currency: str | None = None
    period_days: int | None = Field(None, gt=0)
    next_payment: str | None = None  # ISO 8601 date string

    @field_validator('currency')
    @classmethod
    def normalize_currency(cls, v: str | None) -> str | None:
        """Convert currency to uppercase if provided."""
        return v.upper() if v else v

    @field_validator('next_payment')
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        """Validate date format if provided."""
        if v:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
                return v
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid date format: {v}")
                raise ValueError("Date must be in ISO 8601 format") from e
        return v

class NLUService:
    """Service for natural language understanding using GigaChat API."""
    
    GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: aiohttp.ClientSession | None = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    @lru_cache(maxsize=50)
    async def interpret_message(self, msg: str) -> dict[str, Any]:
        """
        Interpret user message and extract structured data.
        
        Args:
            msg: User message to interpret
            
        Returns:
            dict: Parsed intent and entities
            
        Example:
            {
                "intent": "add",
                "service": "Netflix",
                "amount": 12.99,
                "currency": "EUR",
                "period_days": 30,
                "next_payment": "2025-08-01"
            }
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")
        
        system_prompt = """
        You are a helpful assistant that extracts structured data from user messages about subscriptions.
        Respond with ONLY a valid JSON object matching this schema:
        {
            "intent": "add|delete|update|list|total",
            "service": "...",
            "amount": 12.99,
            "currency": "USD",
            "period_days": 30,
            "next_payment": "2025-08-01"
        }
        
        Rules:
        1. Only include fields you can extract from the message
        2. For dates, use ISO 8601 format (YYYY-MM-DD)
        3. For amounts, extract the numeric value only
        4. For intents, use one of: add, delete, update, list, total
        5. If uncertain about a field, omit it
        6. Respond with ONLY the JSON object, no other text
        """
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        payload = {
            "model": "GigaChat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg}
            ],
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": 400,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with self.session.post(
                self.GIGACHAT_API_URL,
                headers=headers,
                json=payload,
                timeout=10.0
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Extract JSON from the response
                try:
                    content = result['choices'][0]['message']['content']
                    parsed = json.loads(content)
                    
                    # Validate against our model
                    validated = SubscriptionIntent.model_validate(parsed)
                    return validated.model_dump(exclude_none=True)
                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.error(f"Failed to parse GigaChat response: {e}")
                    return {"intent": "unknown", "error": "Failed to parse response"}
                    
        except aiohttp.ClientError as e:
            logger.error(f"GigaChat API request failed: {e}")
            return {"intent": "unknown", "error": "Service unavailable"}

# Global instance to be initialized with API key
nlu_service: NLUService | None = None

async def get_nlu_service() -> NLUService:
    """Get or create the global NLU service instance."""
    global nlu_service
    if nlu_service is None:
        if not settings.GIGACHAT_SECRET_KEY:
            raise ValueError("GIGACHAT_SECRET_KEY is not configured")
        nlu_service = NLUService(settings.GIGACHAT_SECRET_KEY)
    return nlu_service
