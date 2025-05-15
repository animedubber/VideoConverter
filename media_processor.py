import os
import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Create temp directory if it doesn't exist
TEMP_DIRECTORY = "temp_files"
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
Path(TEMP_DIRECTORY).mkdir(parents=True, exist_ok=True)

class MediaProcessor:
    # Store the max file size as a class variable
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    
    @staticmethod
    def download_file(file, file_path):
        """Download a file from Telegram"""
        try:
            file.download(file_path)
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False

    @staticmethod
    def merge_video_audio(video_path, audio_path, output_path, fast_mode=False):
        """Merge video and audio files using FFmpeg"""
        try:
            # Set FFmpeg command options based on upload mode
            if fast_mode:
                # Fast mode: Use lower quality settings
                cmd = [
                    "ffmpeg", "-i", video_path, "-i", audio_path, 
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-c:a", "aac", "-b:a", "128k", 
                    "-map", "0:v", "-map", "1:a", 
                    "-shortest", output_path, "-y"
                ]
            else:
                # Default mode: Maintain quality
                cmd = [
                    "ffmpeg", "-i", video_path, "-i", audio_path, 
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v", "-map", "1:a", 
                    "-shortest", output_path, "-y"
                ]

            # Execute FFmpeg command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False, stderr.decode()
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error merging files: {e}")
            return False, str(e)

    @staticmethod
    def is_valid_video(file_path):
        """Check if the file is a valid video"""
        try:
            # Using FFprobe to check file validity
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", 
                file_path
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            
            return stdout.decode().strip() == "video"
        except Exception as e:
            logger.error(f"Error validating video: {e}")
            return False

    @staticmethod
    def is_valid_audio(file_path):
        """Check if the file is a valid audio"""
        try:
            # Using FFprobe to check file validity
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", 
                file_path
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            
            return stdout.decode().strip() == "audio"
        except Exception as e:
            logger.error(f"Error validating audio: {e}")
            return False

    @staticmethod
    def clean_temp_files(file_paths):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing temporary file {file_path}: {e}")

    @staticmethod
    def generate_temp_path(user_id, file_type, ext):
        """Generate a unique temporary file path"""
        import uuid
        filename = f"{user_id}_{uuid.uuid4().hex}.{ext}"
        return os.path.join(TEMP_DIRECTORY, filename)

    @classmethod
    def check_file_size(cls, file_size):
        """Check if file size is within limits"""
        return file_size <= cls.MAX_FILE_SIZE