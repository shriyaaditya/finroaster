import re
import copy
import logging
from typing import List, Dict, Any, Union
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy loading for SpaCy en_core_web_sm model
_nlp = None

def get_nlp_model():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            try:
                _nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded SpaCy en_core_web_sm model successfully.")
            except OSError:
                logger.warning("en_core_web_sm model not found. Downloading...")
                from spacy.cli import download
                download("en_core_web_sm")
                _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.error(f"Failed to load SpaCy model: {e}")
            _nlp = None
    return _nlp

class DataSanitizer:
    """
    Enterprise InfoSec Zero-Knowledge Data Sanitizer.
    Masks PII, location data (GPE/LOC), personal names (PERSON), and long account numbers
    prior to sending payload context to external LLM providers.
    """
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        if not text or not isinstance(text, str):
            return text

        sanitized = text

        # 1. SpaCy NER Masking for GPE (Geopolitical Entity), LOC (Location), and PERSON
        nlp = get_nlp_model()
        if nlp:
            try:
                doc = nlp(sanitized)
                # Process entities in reverse order to preserve string character indices during replacement
                entities = sorted(doc.ents, key=lambda e: e.start_char, reverse=True)
                for ent in entities:
                    if ent.label_ in ("GPE", "LOC"):
                        sanitized = sanitized[:ent.start_char] + "[LOCATION_MASKED]" + sanitized[ent.end_char:]
                    elif ent.label_ == "PERSON":
                        sanitized = sanitized[:ent.start_char] + "[USER_MASKED]" + sanitized[ent.end_char:]
            except Exception as e:
                logger.error(f"Error during SpaCy NER masking: {e}")

        # 2. Mask account numbers / sequence of digits > 4 (including attached digits like ACC1234567)
        sanitized = re.sub(r'(?:\d[^\d\s]*){5,}', '[ACCOUNT_MASKED]', sanitized)
        sanitized = re.sub(r'\b\d{5,}\b', '[ACCOUNT_MASKED]', sanitized)

        return sanitized

    @classmethod
    def sanitize_transactions(cls, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """
        Returns a deep copy of the input transactions with sensitive text fields masked.
        Original data structures remain completely untouched.
        """
        if isinstance(data, pd.DataFrame):
            df_copy = data.copy(deep=True)
            for col in ["category", "name", "description", "vendor"]:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col].astype(str).apply(cls.sanitize_text)
            return df_copy

        elif isinstance(data, list):
            list_copy = copy.deepcopy(data)
            for item in list_copy:
                if isinstance(item, dict):
                    for key in ["category", "name", "description", "vendor"]:
                        if key in item and item[key]:
                            item[key] = cls.sanitize_text(str(item[key]))
            return list_copy

        return copy.deepcopy(data)

def sanitize_transactions(data: Union[List[Dict[str, Any]], pd.DataFrame]) -> Union[List[Dict[str, Any]], pd.DataFrame]:
    """Helper functional wrapper around DataSanitizer."""
    return DataSanitizer.sanitize_transactions(data)
