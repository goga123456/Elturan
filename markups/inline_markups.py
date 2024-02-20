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
    b3 = InlineKeyboardButton('Изменить описание', callback_data='change_desc')
    b4 = InlineKeyboardButton('Назад', callback_data='back')
    kpriority.add(b1,b2).add(b3)
    return kpriority

def inc_category_kb() -> InlineKeyboardMarkup:
    category = InlineKeyboardMarkup(resize_keyboard=True)
    b1 = InlineKeyboardButton('Качество_связи_и_интернета', callback_data='#Качество_связи_и_интернета')
    b2 = InlineKeyboardButton('app_Beeline_Uzbekistan', callback_data='#app_Beeline_Uzbekistan')
    b3 = InlineKeyboardButton('Внутренне_ПО', callback_data='#Внутренне_ПО')
    b4 = InlineKeyboardButton('База_знаний', callback_data='#База_знаний')
    b5 = InlineKeyboardButton('Интерфейсы_CPA', callback_data='#Интерфейсы_CPA')
    b6 = InlineKeyboardButton('Beepul', callback_data='#Beepul')
    b7 = InlineKeyboardButton('Beeline_TV', callback_data='#Beeline_TV')
    b8 = InlineKeyboardButton('Beeline_Music', callback_data='#Beeline_Music')
    b9 = InlineKeyboardButton('Дозвон_в_КЦ', callback_data='#Дозвон_в_КЦ')
    b10 = InlineKeyboardButton('Акции', callback_data='#Акции')
    b11 = InlineKeyboardButton('CVM_активности', callback_data='#CVM_активности')
    b12 = InlineKeyboardButton('USSD_запросы', callback_data='#USSD_запросы')
    b13 = InlineKeyboardButton('SMS', callback_data='#SMS')
    b14 = InlineKeyboardButton('Корпоративный_сайт', callback_data='#Корпоративный_сайт')
    b15 = InlineKeyboardButton('Balance', callback_data='#Balance')
    b16 = InlineKeyboardButton('Яндекс Плюс', callback_data='#Яндекс_Плюс')
    b17 = InlineKeyboardButton('Телеграмм', callback_data='#Телеграмм')
    b18 = InlineKeyboardButton('Beeline Visa ', callback_data='#Beeline_Visa ')
    b19 = InlineKeyboardButton('OQ mobile', callback_data='#OQ_mobile')
    b20 = InlineKeyboardButton('Написать вручную', callback_data='hand')
    b21 = InlineKeyboardButton('Назад', callback_data='back')
    category.add(b1).add(b2).add(b3, b4).add(b5, b6).add(b7, b8).add(b9, b10).add(b11, b12).add(b12, b13).add(b14, b15).add(b16, b17).add(b18, b19).add(b20).add(b21)
    return category
