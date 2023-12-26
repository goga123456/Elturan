from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def priority_kb() -> InlineKeyboardMarkup:
    kpriority = InlineKeyboardMarkup(resize_keyboard=True)
    b1 = InlineKeyboardButton('1', callback_data='1')
    b2 = InlineKeyboardButton('2', callback_data='2')
    b3 = InlineKeyboardButton('3', callback_data='3')
    b4 = InlineKeyboardButton('4', callback_data='4')
    b5 = InlineKeyboardButton('5', callback_data='5')
    b6 = InlineKeyboardButton('Назад', callback_data='Back')
    kpriority.add(b1).add(b2).add(b3).add(b4).add(b5).add(b6)
    return kpriority

def edit_kb() -> InlineKeyboardMarkup:
    kpriority = InlineKeyboardMarkup(resize_keyboard=True)
    b1 = InlineKeyboardButton('Изменить приоритет', callback_data='change priority')
    b2 = InlineKeyboardButton('Просрочен SLA', callback_data='prosrochen')
    b3 = InlineKeyboardButton('Назад', callback_data='back')
    kpriority.add(b1,b2).add(b3)
    return kpriority

def inc_category_kb() -> InlineKeyboardMarkup:
    category = InlineKeyboardMarkup(resize_keyboard=True)
    b1 = InlineKeyboardButton('Интернет', callback_data='#Интернет')
    b2 = InlineKeyboardButton('Качество_связи', callback_data='#Качество_связи')
    b3 = InlineKeyboardButton('Внутренне_ПО', callback_data='#Внутренне_ПО')
    b4 = InlineKeyboardButton('Услуги', callback_data='#Услуги')
    b5 = InlineKeyboardButton('Digital_Услуги', callback_data='#Digital_Услуги')
    b6 = InlineKeyboardButton('Beeline_Uzbekistan', callback_data='#Beeline_Uzbekistan')
    b7 = InlineKeyboardButton('Beepul', callback_data='#Beepul')
    b8 = InlineKeyboardButton('Оплата', callback_data='#Оплата')
    b9 = InlineKeyboardButton('Beeline_TV', callback_data='#Beeline_TV')
    b10 = InlineKeyboardButton('Назад', callback_data='back')
    category.add(b1,b2,b3).add(b4,b5).add(b6,b7,b8).add(b9).add(b10)
    return category
