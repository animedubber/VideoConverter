import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def get_file_extension(file_name):
    """Get file extension from filename"""
    return os.path.splitext(file_name)[1].lower()

def get_mime_type(file_path):
    """Get MIME type based on file extension"""
    ext = get_file_extension(file_path)
    
    mime_types = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.mov': 'video/quicktime',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
    }
    
    return mime_types.get(ext, 'application/octet-stream')

def get_clean_filename(filename):
    """Sanitize filename"""
    # Remove path information if present
    filename = os.path.basename(filename)
    
    # Replace potentially problematic characters
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        filename = filename.replace(char, '_')
        
    return filename

def check_file_exists(file_path):
    """Check if file exists and has content"""
    if not os.path.exists(file_path):
        return False
    
    if os.path.getsize(file_path) == 0:
        return False
    
    return True