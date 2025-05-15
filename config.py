import os

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7681307753:AAHX0aBHWbfTQRobha6klUl6mNVFcnW2qYI")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://raj:krishna@cluster0.eq8xrjs.mongodb.net/")
DATABASE_NAME = "telegram_bot_db"
USERS_COLLECTION = "users"
TASKS_COLLECTION = "tasks"

# Media Settings
TEMP_DIRECTORY = "temp_files"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Bot Messages
START_GIF_URL = (
    "https://media.giphy.com/media/4pk6ba2LUEMi4/giphy.gif"
    "?cid=ecf05e47japbznlmj88js7bhzc2z6yjqjnbedc5dyw7mlz96&ep=v1_gifs_search&rid=giphy.gif&ct=g"
)

WELCOME_TEXT = """
👋 Welcome to the Video & Audio Merger Bot!

✶ You can customise /settings (Rename File, Upload Mode).

Send me a Video, Audio, or Document to get started.

Use /help to see all commands.
"""

HELP_TEXT = """
📋 Available commands:

/start - Start the bot and see welcome animation
/settings - Customize your preferences
/help - Show this help message
/cancel - Cancel the current operation

📤 How to use:
1. Send a video file
2. Send an audio file to merge with the video
3. The bot will process and return the merged file

⚙️ Settings:
- Rename File: Enable to be prompted for a custom filename
- Upload Mode: Choose between 'default' (high quality) or 'fast' (compressed)
"""

PROCESSING_TEXT = "⏳ Processing your files, please wait..."
SEND_VIDEO_TEXT = "📤 Please send a video file"
SEND_AUDIO_TEXT = "🎵 Please send an audio file to merge with the video"
RENAME_PROMPT = "✏️ Please send a name for the output file (without extension)"
ERROR_TEXT = "❌ An error occurred: {}"
SIZE_LIMIT_TEXT = "⚠️ File exceeds size limit of 50MB"
SUCCESS_TEXT = "✅ Video and audio merged successfully!"
WRONG_FILE_TYPE = "❌ This is not a valid {}. Please send a proper {} file."
