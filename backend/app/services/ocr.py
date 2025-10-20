"""
OCR service for extracting text from receipt images
Supports Tesseract and EasyOCR
"""
import logging
import io
from typing import Optional, Dict, Any
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure tesseract
if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class OCRService:
    def __init__(self):
        self.engine = settings.OCR_ENGINE
        self.easyocr_reader = None
    
    def _is_pdf(self, image_data: bytes) -> bool:
        """Check if data is a PDF file"""
        return image_data[:4] == b'%PDF'
    
    def _pdf_to_images(self, pdf_data: bytes) -> list:
        """Convert PDF to list of PIL Images"""
        try:
            # Set poppler path if configured
            poppler_path = settings.POPPLER_PATH if settings.POPPLER_PATH else None
            images = convert_from_bytes(pdf_data, dpi=300, poppler_path=poppler_path)
            logger.info(f"Converted PDF to {len(images)} image(s)")
            return images
        except Exception as e:
            logger.error(f"PDF conversion error: {e}")
            raise ValueError(f"Failed to convert PDF: {e}")
    
    def _initialize_easyocr(self):
        """Lazy initialization of EasyOCR"""
        if self.easyocr_reader is None:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized")
    
    def preprocess_image(self, image_data: bytes) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy
        - Convert to grayscale
        - Denoise
        - Deskew
        - Increase contrast
        """
        # Handle PDF files
        if self._is_pdf(image_data):
            pil_images = self._pdf_to_images(image_data)
            # Use first page
            pil_image = pil_images[0]
            # Convert PIL to cv2
            img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        else:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Deskew
        coords = np.column_stack(np.where(denoised > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # Rotate image
            (h, w) = denoised.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                denoised, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
        else:
            rotated = denoised
        
        # Increase contrast using adaptive histogram equalization
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(rotated)
        
        # Threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_text_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text using Tesseract OCR"""
        try:
            # Get detailed data with confidence scores
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config='--oem 3 --psm 6'
            )
            
            # Extract text with confidence
            text_blocks = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Filter out low confidence
                    text_blocks.append(data['text'][i])
                    confidences.append(int(data['conf'][i]))
            
            full_text = ' '.join(text_blocks)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "engine": "tesseract"
            }
        except Exception as e:
            logger.error(f"Tesseract OCR error: {e}")
            raise
    
    def extract_text_easyocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text using EasyOCR"""
        try:
            self._initialize_easyocr()
            
            results = self.easyocr_reader.readtext(image)
            
            text_blocks = []
            confidences = []
            
            for (bbox, text, conf) in results:
                text_blocks.append(text)
                confidences.append(conf * 100)  # Convert to percentage
            
            full_text = ' '.join(text_blocks)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "engine": "easyocr"
            }
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            raise
    
    def extract_text(self, image_data: bytes) -> Dict[str, Any]:
        """
        Main method to extract text from image
        Returns OCR text and confidence score
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_data)
            
            # Extract text based on engine
            if self.engine == "tesseract":
                result = self.extract_text_tesseract(processed_image)
            elif self.engine == "easyocr":
                result = self.extract_text_easyocr(processed_image)
            else:
                raise ValueError(f"Unsupported OCR engine: {self.engine}")
            
            logger.info(f"OCR completed with {result['engine']}, confidence: {result['confidence']:.2f}%")
            return result
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            raise


# Global OCR service instance
ocr_service = OCRService()
