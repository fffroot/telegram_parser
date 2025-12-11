from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton




def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Парссинг", callback_data="btn1"),
            InlineKeyboardButton(text="Помощь", callback_data="btn2"),
        ]
    ])