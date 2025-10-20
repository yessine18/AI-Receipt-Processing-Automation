"""
Gemini AI service for structured data extraction from receipts
"""
import logging
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)


class GeminiService:
    def __init__(self):
        self.model_name = settings.GEMINI_MODEL
        self.model = genai.GenerativeModel(self.model_name)
    
    def _create_extraction_prompt(self, ocr_text: str) -> str:
        """Create prompt for structured data extraction"""
        prompt = f"""
You are an expert at extracting structured data from receipt OCR text in ANY language (English, French, Arabic, etc.).

Given the following OCR text from a receipt, extract the following information in JSON format:

{{
  "vendor": "name of the vendor/merchant",
  "date": "receipt date in YYYY-MM-DD format",
  "total_amount": numeric value (convert comma decimals to dots, e.g., 70,000 -> 70.00),
  "currency": "3-letter ISO currency code (e.g., USD, EUR, TND for Tunisian Dinar)",
  "tax_amount": numeric value or null,
  "subtotal_amount": numeric value or null,
  "payment_method": "cash, credit, debit, mobile, recharge, etc.",
  "category": "food, travel, office supplies, mobile recharge, utilities, etc.",
  "line_items": [
    {{
      "description": "item description",
      "quantity": numeric value,
      "unit_price": numeric value,
      "total_price": numeric value
    }}
  ],
  "transaction_id": "any reference or transaction number",
  "location": "store location or address",
  "confidence_scores": {{
    "vendor": 0-100,
    "date": 0-100,
    "total_amount": 0-100,
    "overall": 0-100
  }}
}}

IMPORTANT Rules:
1. Return ONLY valid JSON, no additional text
2. Use null for missing/uncertain values
3. Ensure all numeric values are numbers, not strings
4. Convert comma decimals to dots (70,000 -> 70.00 or 70000.00 depending on context)
5. For dates in DD/MM/YYYY format, convert to YYYY-MM-DD
6. Detect currency from context (TND for Tunisia, EUR for Europe, USD for US, etc.)
7. Handle multi-language receipts (French, Arabic, English, etc.)
8. For recharge/utility receipts, set category appropriately
9. Extract ALL visible numbers including transaction IDs
10. If the amount looks like 70,000 and seems to be a whole number, treat it as 70000.00

OCR Text:
{ocr_text}

JSON Output:
"""
        return prompt
    
    def _create_vision_prompt(self) -> str:
        """Create prompt for vision-based extraction"""
        prompt = """
Analyze this receipt image and extract the following information in JSON format.
Handle receipts in ANY language (English, French, Arabic, etc.):

{
  "vendor": "name of the vendor/merchant",
  "date": "receipt date in YYYY-MM-DD format (convert DD/MM/YYYY if needed)",
  "total_amount": numeric value (convert comma decimals: 70,000 -> 70.00 or 70000.00),
  "currency": "3-letter ISO currency code (TND, EUR, USD, etc.)",
  "tax_amount": numeric value or null,
  "subtotal_amount": numeric value or null,
  "payment_method": "payment type (cash, card, mobile, recharge, etc.)",
  "category": "expense category (food, travel, mobile recharge, utilities, etc.)",
  "line_items": [
    {
      "description": "item description",
      "quantity": numeric value,
      "unit_price": numeric value,
      "total_price": numeric value
    }
  ],
  "transaction_id": "any reference or transaction number visible",
  "location": "store location or address",
  "confidence_scores": {
    "vendor": 0-100,
    "date": 0-100,
    "total_amount": 0-100,
    "overall": 0-100
  }
}

CRITICAL: 
- Look carefully at ALL numbers on the receipt
- For amounts with comma (70,000), determine if it's decimal (70.00) or thousands (70000.00)
- Extract transaction IDs, reference numbers
- Detect currency from country context
- Return ONLY valid JSON with no additional text
"""
        return prompt
    
    def extract_from_text(self, ocr_text: str) -> Dict[str, Any]:
        """
        Extract structured data from OCR text using Gemini
        """
        try:
            prompt = self._create_extraction_prompt(ocr_text)
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for consistent output
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            
            # Parse JSON response
            result_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result_text = result_text.strip()
            
            # Parse JSON
            data = json.loads(result_text)
            
            logger.info(f"Gemini extraction successful, vendor: {data.get('vendor')}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text: {result_text}")
            raise ValueError("Invalid JSON response from Gemini")
        except Exception as e:
            logger.error(f"Gemini extraction error: {e}")
            raise
    
    def extract_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extract structured data directly from image using Gemini Vision
        """
        try:
            import PIL.Image
            import io
            
            # Convert bytes to PIL Image
            image = PIL.Image.open(io.BytesIO(image_data))
            
            prompt = self._create_vision_prompt()
            
            response = self.model.generate_content(
                [prompt, image],
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            
            # Parse JSON response
            result_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result_text = result_text.strip()
            
            # Parse JSON
            data = json.loads(result_text)
            
            logger.info(f"Gemini vision extraction successful, vendor: {data.get('vendor')}")
            return data
        except Exception as e:
            logger.error(f"Gemini vision extraction error: {e}")
            raise
    
    def extract_hybrid(self, image_data: bytes, ocr_text: str) -> Dict[str, Any]:
        """
        Hybrid approach: Use both OCR text and image for best results
        Fallback to OCR if vision fails
        """
        try:
            # Try vision-based extraction first
            return self.extract_from_image(image_data)
        except Exception as e:
            logger.warning(f"Vision extraction failed, falling back to OCR: {e}")
            # Fallback to OCR-based extraction
            return self.extract_from_text(ocr_text)


# Global Gemini service instance
gemini_service = GeminiService()
