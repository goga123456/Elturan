from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def create_incident_kb() -> ReplyKeyboardMarkup:
    k_incident = ReplyKeyboardMarkup(resize_keyboard=True)
    b1 = KeyboardButton('Создать Инцидент')
    b2 = KeyboardButton('Закрыть Инцидент')
    b3 = KeyboardButton('Редактировать Инцидент')
    b4 = KeyboardButton('/start')
    k_incident.add(b1, b2).add(b3).add(b4)
    return k_incident



def get_start_and_back_kb() -> ReplyKeyboardMarkup:
    kmain = ReplyKeyboardMarkup(resize_keyboard=True)
    b1 = KeyboardButton('🔙')
    b2 = KeyboardButton('/start')
    kmain.add(b1, b2)
    return kmain


def get_start_kb() -> ReplyKeyboardMarkup:
    kmain2 = ReplyKeyboardMarkup(resize_keyboard=True)
    b1 = KeyboardButton('/start')
    kmain2.add(b1)
    return kmain2
