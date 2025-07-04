from typing import Dict, Any, Optional

class NLUProcessor:
    """Natural Language Understanding processor for handling user intents."""
    
    def __init__(self, gigachat_credentials: Optional[str] = None):
        self.gigachat_credentials = gigachat_credentials
        # Initialize GigaChat client if credentials are provided
        self.gigachat_client = None
        if gigachat_credentials:
            self._initialize_gigachat()
    
    def _initialize_gigachat(self):
        """Initialize GigaChat client with provided credentials."""
        try:
            # Import here to avoid dependency if not using GigaChat
            from gigachat import GigaChat
            self.gigachat_client = GigaChat(credentials=self.gigachat_credentials, verify_ssl_certs=False)
        except ImportError:
            pass
    
    async def process(self, text: str, user_id: int) -> Dict[str, Any]:
        """Process user text and extract intent and entities."""
        if self.gigachat_client:
            return await self._process_with_gigachat(text, user_id)
        return self._process_with_regex(text)
    
    async def _process_with_gigachat(self, text: str, user_id: int) -> Dict[str, Any]:
        """Process text using GigaChat API."""
        try:
            # This is a simplified example - adjust according to your needs
            response = await self.gigachat_client.achat(
                messages=[{
                    "role": "user",
                    "content": f"User (ID: {user_id}) said: {text}\n"
                               "Extract intent and entities in JSON format."
                }]
            )
            # Parse response and return structured data
            return self._parse_gigachat_response(response.choices[0].message.content)
        except Exception as e:
            # Fallback to regex if API call fails
            return self._process_with_regex(text)
    
    def _process_with_regex(self, text: str) -> Dict[str, Any]:
        """Fallback processing using regex patterns."""
        # Basic intent detection as fallback
        text_lower = text.lower()
        if any(word in text_lower for word in ["add", "new", "create"]):
            return {"intent": "add_subscription", "confidence": 0.7}
        elif any(word in text_lower for word in ["list", "show", "my"]):
            return {"intent": "list_subscriptions", "confidence": 0.7}
        elif any(word in text_lower for word in ["delete", "remove", "cancel"]):
            return {"intent": "delete_subscription", "confidence": 0.7}
        return {"intent": "unknown", "confidence": 0.0}
    
    def _parse_gigachat_response(self, response_text: str) -> Dict[str, Any]:
        """Parse GigaChat response into a structured format."""
        # This is a simplified parser - adjust based on your GigaChat response format
        try:
            import json
            return json.loads(response_text)
        except (json.JSONDecodeError, AttributeError):
            return {"intent": "unknown", "confidence": 0.0}
