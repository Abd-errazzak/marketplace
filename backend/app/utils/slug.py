"""
Slug generation utilities
"""

import re
from unidecode import unidecode


def generate_slug(text: str) -> str:
    """Generate a URL-friendly slug from text"""
    # Convert to lowercase and remove accents
    text = unidecode(text.lower())
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text

