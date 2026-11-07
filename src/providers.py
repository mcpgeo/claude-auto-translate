"""Translation provider implementations for claude-auto-translate."""

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """Base class for translation providers."""
    
    def __init__(self, api_key: str, config: Dict[str, Any], timeout: float):
        self.api_key = api_key
        self.config = config
        self.timeout = timeout
    
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source to target language."""
        pass
    
    def _make_request(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST"
    ) -> Dict[str, Any]:
        """Make an HTTP request and return JSON response."""
        headers = headers or {}
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        # Create SSL context (required for HTTPS)
        ctx = ssl.create_default_context()
        
        response = urllib.request.urlopen(req, timeout=self.timeout, context=ctx)
        response_data = response.read().decode("utf-8")
        return json.loads(response_data)


class AnthropicProvider(TranslationProvider):
    """Anthropic Claude API for translation."""
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        model = self.config.get("model", "claude-3-haiku-20240307")
        
        prompt = self._build_prompt(text, source_lang, target_lang)
        
        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        response = self._make_request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        
        return self._extract_translation(response)
    
    def _build_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        return (
            f"Translate the following text from {source_lang} to {target_lang}. "
            f"Output ONLY the translation, nothing else. No explanations, no quotes, "
            f"no additional text. Preserve any placeholders like __PRESERVE_*__ exactly as they appear.\n\n"
            f"{text}"
        )
    
    def _extract_translation(self, response: Dict[str, Any]) -> str:
        content = response.get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "").strip()
        return ""


class OpenAIProvider(TranslationProvider):
    """OpenAI API for translation."""
    
    API_URL = "https://api.openai.com/v1/chat/completions"
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        model = self.config.get("model", "gpt-4o-mini")
        
        prompt = self._build_prompt(text, source_lang, target_lang)
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a translator. Translate from {source_lang} to {target_lang}. "
                        f"Output ONLY the translation. No explanations, no quotes. "
                        f"Preserve any placeholders like __PRESERVE_*__ exactly."
                    )
                },
                {"role": "user", "content": text}
            ],
            "temperature": 0.1
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = self._make_request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        
        return self._extract_translation(response)
    
    def _build_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        return text
    
    def _extract_translation(self, response: Dict[str, Any]) -> str:
        choices = response.get("choices", [])
        if choices and len(choices) > 0:
            message = choices[0].get("message", {})
            return message.get("content", "").strip()
        return ""


class GeminiProvider(TranslationProvider):
    """Google Gemini API for translation."""
    
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        model = self.config.get("model", "gemini-1.5-flash")
        
        prompt = self._build_prompt(text, source_lang, target_lang)
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }
        
        url = f"{self.API_URL_TEMPLATE.format(model=model)}?key={self.api_key}"
        
        headers = {"Content-Type": "application/json"}
        
        response = self._make_request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        
        return self._extract_translation(response)
    
    def _build_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        return (
            f"Translate the following text from {source_lang} to {target_lang}. "
            f"Output ONLY the translation, nothing else. No explanations, no quotes. "
            f"Preserve any placeholders like __PRESERVE_*__ exactly as they appear.\n\n"
            f"{text}"
        )
    
    def _extract_translation(self, response: Dict[str, Any]) -> str:
        candidates = response.get("candidates", [])
        if candidates and len(candidates) > 0:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts and len(parts) > 0:
                return parts[0].get("text", "").strip()
        return ""


class DeepLProvider(TranslationProvider):
    """DeepL API for translation."""
    
    API_URL_FREE = "https://api-free.deepl.com/v2/translate"
    API_URL_PRO = "https://api.deepl.com/v2/translate"
    
    # DeepL language codes mapping (common cases)
    LANG_CODES = {
        "english": "EN",
        "georgian": "KA",  # Note: DeepL may not support all languages
        "german": "DE",
        "french": "FR",
        "spanish": "ES",
        "italian": "IT",
        "portuguese": "PT",
        "russian": "RU",
        "japanese": "JA",
        "chinese": "ZH",
        "korean": "KO",
        "polish": "PL",
        "dutch": "NL",
        "ukrainian": "UK",
    }
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        # Determine API URL based on key format
        api_url = self.API_URL_FREE if ":fx" in self.api_key else self.API_URL_PRO
        
        target_code = self._get_lang_code(target_lang)
        source_code = self._get_lang_code(source_lang)
        
        payload = {
            "text": [text],
            "target_lang": target_code,
        }
        
        # DeepL allows omitting source_lang for auto-detection
        if source_code:
            payload["source_lang"] = source_code
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"DeepL-Auth-Key {self.api_key}"
        }
        
        response = self._make_request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        
        return self._extract_translation(response)
    
    def _get_lang_code(self, lang: str) -> Optional[str]:
        return self.LANG_CODES.get(lang.lower())
    
    def _extract_translation(self, response: Dict[str, Any]) -> str:
        translations = response.get("translations", [])
        if translations and len(translations) > 0:
            return translations[0].get("text", "").strip()
        return ""


class GoogleCloudProvider(TranslationProvider):
    """Google Cloud Translation API."""
    
    API_URL = "https://translation.googleapis.com/language/translate/v2"
    
    # Google Cloud language codes
    LANG_CODES = {
        "english": "en",
        "georgian": "ka",
        "german": "de",
        "french": "fr",
        "spanish": "es",
        "italian": "it",
        "portuguese": "pt",
        "russian": "ru",
        "japanese": "ja",
        "chinese": "zh",
        "korean": "ko",
        "polish": "pl",
        "dutch": "nl",
        "ukrainian": "uk",
        "arabic": "ar",
        "hindi": "hi",
    }
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        target_code = self._get_lang_code(target_lang) or "en"
        source_code = self._get_lang_code(source_lang)
        
        payload = {
            "q": text,
            "target": target_code,
            "format": "text",
            "key": self.api_key
        }
        
        if source_code:
            payload["source"] = source_code
        
        headers = {"Content-Type": "application/json"}
        
        response = self._make_request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        
        return self._extract_translation(response)
    
    def _get_lang_code(self, lang: str) -> Optional[str]:
        return self.LANG_CODES.get(lang.lower())
    
    def _extract_translation(self, response: Dict[str, Any]) -> str:
        data = response.get("data", {})
        translations = data.get("translations", [])
        if translations and len(translations) > 0:
            return translations[0].get("translatedText", "").strip()
        return ""


PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "deepl": DeepLProvider,
    "google_cloud": GoogleCloudProvider,
}


def get_provider(
    provider_name: str,
    api_key: str,
    config: Dict[str, Any],
    timeout: float
) -> Optional[TranslationProvider]:
    """Get a translation provider instance."""
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        return None
    return provider_class(api_key, config, timeout)
