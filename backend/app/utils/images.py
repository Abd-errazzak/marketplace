"""
Image handling utilities
"""

import os
import io
import uuid
from fastapi import UploadFile
from PIL import Image
from app.core.config import settings


async def save_uploaded_image(file: UploadFile, folder: str = "products") -> str:
    """Save uploaded image and return the file path"""
    # Generate unique filename
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        raise ValueError("Invalid image format")
    
    filename = f"{uuid.uuid4()}.{file_extension}"
    
    # Create directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, folder)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, filename)
    
    # Read and process image
    contents = await file.read()
    
    # Open image with PIL
    image = Image.open(io.BytesIO(contents))
    
    # Resize if too large (max 1920x1080)
    max_size = (1920, 1080)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save processed image
    image.save(file_path, optimize=True, quality=85)
    
    return f"/uploads/{folder}/{filename}"


def delete_image(image_path: str) -> bool:
    """Delete image file"""
    try:
        if image_path.startswith('/uploads/'):
            file_path = os.path.join(settings.UPLOAD_DIR, image_path[9:])  # Remove '/uploads/' prefix
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
    except Exception:
        pass
    return False


def get_image_url(image_path: str) -> str:
    """Get full URL for image"""
    if image_path.startswith('http'):
        return image_path
    
    return f"{settings.BASE_URL}{image_path}"
