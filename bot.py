import os
import logging
import uuid
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
)
import motor.motor_asyncio
from media_processor import MediaProcessor
from utils import get_file_extension, get_clean_filename

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token and MongoDB connection
BOT_TOKEN = "7681307753:AAHX0aBHWbfTQRobha6klUl6mNVFcnW2qYI"
MONGO_URI = "mongodb+srv://raj:krishna@cluster0.eq8xrjs.mongodb.net/"
DATABASE_NAME = "telegram_bot_db"

# Initialize media processor
media_processor = MediaProcessor()

# MongoDB client and collections
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]
users_collection = db.users

# Constants
START_GIF_URL = (
    "https://media.giphy.com/media/4pk6ba2LUEMi4/giphy.gif"
    "?cid=ecf05e47japbznlmj88js7bhzc2z6yjqjnbedc5dyw7mlz96&ep=v1_gifs_search&rid=giphy.gif&ct=g"
)

WELCOME_TEXT = """
👋 Welcome to the Video & Audio Merger Bot!

✶ You can customise /settings (Rename File, Upload Mode).

Send me a Video, Audio, or Document to get started.
⚠️ Note: Telegram limits file size to 20MB. For larger files (up to 2GB),
please use our web interface: https://yourboturl.replit.app

Use /help to see all commands.
"""

HELP_TEXT = """
📋 Available commands:

/start - Start the bot and see welcome animation
/settings - Customize your preferences
/help - Show this help message
/cancel - Cancel the current operation

📤 How to use:
1. Send a video file (max 20MB due to Telegram limits)
   For larger files (up to 2GB), use our web interface:
   https://yourboturl.replit.app
2. Send an audio file to merge with the video
3. The bot will process and return the merged file

⚙️ Settings:
- Rename File: Enable to be prompted for a custom filename
- Upload Mode: Choose between 'default' (high quality) or 'fast' (compressed)
"""

# User states
AWAITING_VIDEO, AWAITING_AUDIO, AWAITING_FILENAME, PROCESSING, IDLE = range(5)

# Context data keys
VIDEO_PATH = "video_path"
AUDIO_PATH = "audio_path"
OUTPUT_PATH = "output_path"
STATE = "state"

# Keyboards
def get_settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Rename File", callback_data="settings_rename")],
        [InlineKeyboardButton("Upload Mode", callback_data="settings_upload_mode")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="back_main")],
    ])

# Get user settings or create default
async def get_user_settings(user_id: int):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        default_settings = {
            "user_id": user_id,
            "rename_file": False,
            "upload_mode": "default",
        }
        await users_collection.insert_one(default_settings)
        return default_settings
    return user

# Update specific user setting
async def update_user_settings(user_id: int, field: str, value):
    await users_collection.update_one(
        {"user_id": user_id}, 
        {"$set": {field: value}}
    )

# Command handlers
def start(update, context):
    """Handle the /start command"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Initialize user state
    context.user_data[STATE] = AWAITING_VIDEO
    
    # Send welcome message
    context.bot.send_animation(chat_id=chat_id, animation=START_GIF_URL)
    context.bot.send_message(chat_id=chat_id, text=WELCOME_TEXT)
    context.bot.send_message(chat_id=chat_id, text="Please send a video file to begin.")

def settings(update, context):
    """Handle the /settings command"""
    chat_id = update.effective_chat.id
    
    # Get current settings from user_data or use defaults
    rename_file = context.user_data.get("rename_file", False)
    upload_mode = context.user_data.get("upload_mode", "default")
    
    text = (
        f"⚙️ Settings Menu\n\n"
        f"Rename File: {'Enabled' if rename_file else 'Disabled'}\n"
        f"Upload Mode: {upload_mode}\n\n"
        "Choose an option:"
    )
    context.bot.send_message(
        chat_id=chat_id, 
        text=text, 
        reply_markup=get_settings_keyboard()
    )

def help_command(update, context):
    """Handle the /help command"""
    update.message.reply_text(HELP_TEXT)
    
    # Set state to awaiting video
    context.user_data[STATE] = AWAITING_VIDEO
    update.message.reply_text("Please send a video file to begin.")

def cancel_command(update, context):
    """Handle the /cancel command"""
    # Reset any ongoing operations
    for key in [VIDEO_PATH, AUDIO_PATH, OUTPUT_PATH]:
        if key in context.user_data:
            # Clean up any files if they exist
            if context.user_data[key] and os.path.exists(context.user_data[key]):
                try:
                    os.remove(context.user_data[key])
                except Exception as e:
                    logger.error(f"Error removing file {context.user_data[key]}: {e}")
            # Remove from user_data
            del context.user_data[key]
    
    # Reset state
    context.user_data[STATE] = IDLE
    
    update.message.reply_text("Operation cancelled. Send /start to begin again.")

# Callback query handler
def callback_handler(update, context):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "settings_rename":
        # For this version, we'll toggle a simple setting in user context
        current_value = context.user_data.get("rename_file", False)
        context.user_data["rename_file"] = not current_value
        
        query.edit_message_text(
            text=f"Rename File setting is now: {'Enabled' if context.user_data['rename_file'] else 'Disabled'}",
            reply_markup=get_settings_keyboard(),
        )
    elif data == "settings_upload_mode":
        # For this version, we'll toggle between "fast" and "default"
        current_mode = context.user_data.get("upload_mode", "default")
        new_mode = "fast" if current_mode == "default" else "default"
        context.user_data["upload_mode"] = new_mode
        
        query.edit_message_text(
            text=f"Upload Mode is now: {new_mode}",
            reply_markup=get_settings_keyboard(),
        )
    elif data == "back_main":
        query.edit_message_text(text=WELCOME_TEXT)
        
        # Set state to awaiting video
        context.user_data[STATE] = AWAITING_VIDEO
        context.bot.send_message(
            chat_id=query.message.chat_id, 
            text="Please send a video file to begin."
        )

# Handler for video files
def handle_video(update, context):
    """Handle receiving video files"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if we're expecting a video
    current_state = context.user_data.get(STATE, IDLE)
    if current_state != AWAITING_VIDEO:
        context.bot.send_message(
            chat_id=chat_id,
            text=f"I'm not expecting a video file right now. Current state: {current_state}. Send /cancel to reset."
        )
        return
    
    # Get the file
    video = update.message.video
    if not video:
        context.bot.send_message(
            chat_id=chat_id,
            text="This doesn't appear to be a valid video file. Please send a proper video."
        )
        return
    
    # Check file size (2GB limit)
    if not media_processor.check_file_size(video.file_size):
        context.bot.send_message(
            chat_id=chat_id,
            text="File exceeds size limit of 2GB"
        )
        return
    
    # Get file
    try:
        video_file = update.message.video.get_file()
    except BadRequest as e:
        if "File is too big" in str(e):
            context.bot.send_message(
                chat_id=chat_id,
                text="This file exceeds Telegram's size limits. Please use a smaller file (max 20MB) or send it as a direct file upload."
            )
            return
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Error getting file: {str(e)}"
            )
            return
    
    # Generate temp path
    file_ext = ".mp4"  # Default extension for videos
    video_path = media_processor.generate_temp_path(user_id, "video", file_ext[1:] if file_ext.startswith('.') else file_ext)
    
    # Download file
    status_message = context.bot.send_message(
        chat_id=chat_id,
        text="Downloading video file..."
    )
    
    download_success = media_processor.download_file(video_file, video_path)
    if not download_success:
        status_message.edit_text("Failed to download video file")
        return
    
    # Validate video file
    if not media_processor.is_valid_video(video_path):
        status_message.edit_text("This doesn't appear to be a valid video file")
        media_processor.clean_temp_files([video_path])
        return
    
    # Store video path
    context.user_data[VIDEO_PATH] = video_path
    
    # Update state
    context.user_data[STATE] = AWAITING_AUDIO
    
    status_message.edit_text("Video received! Now please send an audio file to merge with the video.")

# Handler for audio files
def handle_audio(update, context):
    """Handle receiving audio files"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if we're expecting an audio
    current_state = context.user_data.get(STATE, IDLE)
    if current_state != AWAITING_AUDIO:
        context.bot.send_message(
            chat_id=chat_id,
            text=f"I'm not expecting an audio file right now. Current state: {current_state}. Send /cancel to reset."
        )
        return
    
    # Get the file
    audio = update.message.audio or update.message.voice
    if not audio:
        context.bot.send_message(
            chat_id=chat_id,
            text="This doesn't appear to be a valid audio file. Please send a proper audio."
        )
        return
    
    # Check file size (2GB limit)
    if not media_processor.check_file_size(audio.file_size):
        context.bot.send_message(
            chat_id=chat_id,
            text="File exceeds size limit of 2GB"
        )
        return
    
    # Get file
    try:
        audio_file = audio.get_file()
    except BadRequest as e:
        if "File is too big" in str(e):
            context.bot.send_message(
                chat_id=chat_id,
                text="This file exceeds Telegram's size limits. Please use a smaller file (max 20MB) or send it as a direct file upload."
            )
            return
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Error getting file: {str(e)}"
            )
            return
    
    # Generate temp path
    if hasattr(audio, 'mime_type') and audio.mime_type:
        ext = "." + audio.mime_type.split("/")[-1]
    else:
        ext = ".mp3"  # Default extension
    
    audio_path = media_processor.generate_temp_path(user_id, "audio", ext[1:] if ext.startswith('.') else ext)
    
    # Download file
    status_message = context.bot.send_message(
        chat_id=chat_id,
        text="Downloading audio file..."
    )
    
    download_success = media_processor.download_file(audio_file, audio_path)
    if not download_success:
        status_message.edit_text("Failed to download audio file")
        return
    
    # Validate audio file
    if not media_processor.is_valid_audio(audio_path):
        status_message.edit_text("This doesn't appear to be a valid audio file")
        media_processor.clean_temp_files([audio_path])
        return
    
    # Store audio path
    context.user_data[AUDIO_PATH] = audio_path
    
    # Check if rename is enabled
    rename_file = context.user_data.get("rename_file", False)
    
    if rename_file:
        # Ask for filename
        context.user_data[STATE] = AWAITING_FILENAME
        status_message.edit_text("Audio received! Please send a name for the output file (without extension)")
    else:
        # Process immediately
        process_files(update, context, status_message)

# Handler for text messages (used for filename input)
def handle_text(update, context):
    """Handle text messages for filename input"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if we're expecting a filename
    current_state = context.user_data.get(STATE, IDLE)
    if current_state != AWAITING_FILENAME:
        return
    
    # Get the custom filename
    custom_filename = get_clean_filename(update.message.text)
    
    # Process with custom filename
    status_message = context.bot.send_message(
        chat_id=chat_id,
        text="Processing files with your custom filename..."
    )
    
    process_files(update, context, status_message, custom_filename)

# Handler for document files
def handle_document(update, context):
    """Handle document files (detect if video or audio)"""
    # Check mime type or file extension to determine if it's video or audio
    document = update.message.document
    if not document:
        return
    
    # Check file extension
    file_name = document.file_name if document.file_name else "unknown"
    file_ext = get_file_extension(file_name).lower()
    
    # Video extensions
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm']
    # Audio extensions
    audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
    
    current_state = context.user_data.get(STATE, IDLE)
    
    if current_state == AWAITING_VIDEO and file_ext in video_extensions:
        # Handle as video
        handle_document_as_video(update, context)
    elif current_state == AWAITING_AUDIO and file_ext in audio_extensions:
        # Handle as audio
        handle_document_as_audio(update, context)
    elif current_state == AWAITING_VIDEO:
        update.message.reply_text("This doesn't appear to be a valid video file. Please send a proper video.")
    elif current_state == AWAITING_AUDIO:
        update.message.reply_text("This doesn't appear to be a valid audio file. Please send a proper audio.")

def handle_document_as_video(update, context):
    """Process document as video"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    document = update.message.document
    
    # Check file size (2GB limit)
    if not media_processor.check_file_size(document.file_size):
        context.bot.send_message(
            chat_id=chat_id,
            text="File exceeds size limit of 2GB"
        )
        return
    
    # Get file
    try:
        file = document.get_file()
    except BadRequest as e:
        if "File is too big" in str(e):
            context.bot.send_message(
                chat_id=chat_id,
                text="This file exceeds Telegram's size limits. Please use a smaller file (max 20MB) or send it as a direct file upload."
            )
            return
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Error getting file: {str(e)}"
            )
            return
    
    # Generate temp path with correct extension
    if document.file_name:
        file_ext = get_file_extension(document.file_name)
    else:
        file_ext = ".mp4"  # Default
    
    file_path = media_processor.generate_temp_path(user_id, "video", file_ext[1:] if file_ext.startswith('.') else file_ext)
    
    # Download file
    status_message = context.bot.send_message(
        chat_id=chat_id,
        text="Downloading video file..."
    )
    
    download_success = media_processor.download_file(file, file_path)
    if not download_success:
        status_message.edit_text("Failed to download video file")
        return
    
    # Validate video file
    if not media_processor.is_valid_video(file_path):
        status_message.edit_text("This doesn't appear to be a valid video file")
        media_processor.clean_temp_files([file_path])
        return
    
    # Store video path
    context.user_data[VIDEO_PATH] = file_path
    
    # Update state
    context.user_data[STATE] = AWAITING_AUDIO
    
    status_message.edit_text("Video received! Now please send an audio file to merge with the video.")

def handle_document_as_audio(update, context):
    """Process document as audio"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    document = update.message.document
    
    # Check file size (2GB limit)
    if not media_processor.check_file_size(document.file_size):
        context.bot.send_message(
            chat_id=chat_id,
            text="File exceeds size limit of 2GB"
        )
        return
    
    # Get file
    try:
        file = document.get_file()
    except BadRequest as e:
        if "File is too big" in str(e):
            context.bot.send_message(
                chat_id=chat_id,
                text="This file exceeds Telegram's size limits. Please use a smaller file (max 20MB) or send it as a direct file upload."
            )
            return
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Error getting file: {str(e)}"
            )
            return
    
    # Generate temp path
    if document.file_name:
        file_ext = get_file_extension(document.file_name)
    else:
        file_ext = ".mp3"  # Default
    
    file_path = media_processor.generate_temp_path(user_id, "audio", file_ext[1:] if file_ext.startswith('.') else file_ext)
    
    # Download file
    status_message = context.bot.send_message(
        chat_id=chat_id,
        text="Downloading audio file..."
    )
    
    download_success = media_processor.download_file(file, file_path)
    if not download_success:
        status_message.edit_text("Failed to download audio file")
        return
    
    # Validate audio file
    if not media_processor.is_valid_audio(file_path):
        status_message.edit_text("This doesn't appear to be a valid audio file")
        media_processor.clean_temp_files([file_path])
        return
    
    # Store audio path
    context.user_data[AUDIO_PATH] = file_path
    
    # Check if rename is enabled
    rename_file = context.user_data.get("rename_file", False)
    
    if rename_file:
        # Ask for filename
        context.user_data[STATE] = AWAITING_FILENAME
        status_message.edit_text("Audio received! Please send a name for the output file (without extension)")
    else:
        # Process immediately
        process_files(update, context, status_message)

def process_files(update, context, status_message, custom_filename=None):
    """Process video and audio files to merge them"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Set state to processing
    context.user_data[STATE] = PROCESSING
    
    # Get file paths
    video_path = context.user_data.get(VIDEO_PATH)
    audio_path = context.user_data.get(AUDIO_PATH)
    
    if not video_path or not audio_path:
        status_message.edit_text("Missing video or audio file. Please /start again.")
        return
    
    # Get upload mode setting
    fast_mode = context.user_data.get("upload_mode", "default") == "fast"
    
    # Generate output filename
    if custom_filename:
        output_filename = f"{custom_filename}.mp4"
    else:
        output_filename = f"merged_{user_id}_{int(time.time())}.mp4"
    
    output_path = os.path.join('temp_files', output_filename)
    context.user_data[OUTPUT_PATH] = output_path
    
    # Send processing message
    status_message.edit_text("⏳ Processing your files, please wait...")
    
    # Process files
    success, error_message = media_processor.merge_video_audio(
        video_path, audio_path, output_path, fast_mode
    )
    
    if not success:
        status_message.edit_text(f"❌ An error occurred: {error_message or 'Failed to merge files'}")
        
        # Clean up
        media_processor.clean_temp_files([video_path, audio_path])
        return
    
    # Send the merged file
    try:
        status_message.edit_text("✅ Video and audio merged successfully!")
        
        # Send as video
        context.bot.send_video(
            chat_id=chat_id,
            video=open(output_path, 'rb'),
            caption=f"Merged file: {output_filename}",
            supports_streaming=True,
            filename=output_filename
        )
        
        # Reset state
        context.user_data[STATE] = IDLE
        
        # Clean up temp files
        media_processor.clean_temp_files([video_path, audio_path, output_path])
        
        # Guide for next action
        context.bot.send_message(
            chat_id=chat_id,
            text="Send /start to process another file"
        )
        
    except Exception as e:
        logger.error(f"Error sending merged file: {e}")
        context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Failed to send merged file: {str(e)}"
        )
        
        # Clean up
        media_processor.clean_temp_files([video_path, audio_path, output_path])

def main():
    """Initialize and run the bot"""
    # Create the updater
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Add command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("settings", settings))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("cancel", cancel_command))
    dispatcher.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add message handlers for handling media and text
    dispatcher.add_handler(MessageHandler(Filters.video, handle_video))
    dispatcher.add_handler(MessageHandler(Filters.audio | Filters.voice, handle_audio))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    # Start the Bot
    print("Bot started...")
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main()