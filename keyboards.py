from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Settings menu keyboard
def get_settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Rename File", callback_data="settings_rename")],
        [InlineKeyboardButton("Upload Mode", callback_data="settings_upload_mode")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="back_main")],
    ])

# Confirmation keyboard
def get_confirmation_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Yes", callback_data="confirm_yes"),
            InlineKeyboardButton("No", callback_data="confirm_no")
        ],
    ])

# Cancel operation keyboard
def get_cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Cancel", callback_data="cancel_operation")],
    ])
