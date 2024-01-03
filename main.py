import asyncio
from datetime import datetime, timedelta

from aiogram import types, executor, Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import TOKEN_API
from markups.inline_markups import priority_kb, edit_kb, inc_category_kb
from markups.reply_markups_start_and_back import *
from states import ProfileStatesGroup
import os
import asyncpg
from aiogram.utils.executor import start_webhook
import logging


from db import Database
CHANNEL_ID = -1002018175768

scheduled_tasks = {}


storage = MemoryStorage()
TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot,
                storage=storage)

HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')

# webhook settings
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# webserver settings
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = os.getenv('PORT', default=8000)

baza = Database()
scheduler = AsyncIOScheduler()


async def delete_msg(message_id):
    await bot.delete_message(chat_id=CHANNEL_ID, message_id=message_id)


async def prosrochen(number, priority, category, desc):
    await baza.update_status(status="Просрочен SLA", inc_number=number)
    await bot.send_message(CHANNEL_ID, f"Просрочен SLA\n"
                                       f"Номер инцидента: {number}\n"
                                       f"Приоритет: {priority}\n"
                                       f"Категория: {category}\n"
                                       f"Описание: {desc}\n")
async def incidents() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    incidents_list = await baza.incidents()
    for i in incidents_list:
        markup.add(InlineKeyboardButton(f'{i[0]}', callback_data=f'{i[0]}'))
    return markup

async def closed_incidents() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    incidents_list = await baza.closed_incidents()
    for i in incidents_list:
        markup.add(InlineKeyboardButton(f'{i[0]}', callback_data=f'{i[0]}'))
    return markup

@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await bot.send_message(chat_id=message.from_user.id,
                           text="Здравствуйте , это бот для создания инцидентов",
                           reply_markup=create_incident_kb())
    await ProfileStatesGroup.main_menu.set()


@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.main_menu)
async def cmd_start(message: types.Message, state: FSMContext) -> InlineKeyboardMarkup:
    if message.text == "Создать Инцидент":
        await bot.send_message(chat_id=message.from_user.id,
                               text="Номер инцидента:",
                               reply_markup=get_start_kb())
        await ProfileStatesGroup.number_of_incident.set()
    if message.text == "Закрыть Инцидент":
        await bot.send_message(chat_id=message.from_user.id,
                               text="Выберите номер инцидента:",
                               reply_markup=await incidents())
        await ProfileStatesGroup.close_incident.set()
    if message.text == "Редактировать Инцидент":
        await bot.send_message(chat_id=message.from_user.id,
                               text="Выберите номер инцидента:",
                               reply_markup=await incidents())
        await ProfileStatesGroup.edit_incident.set()
    if message.text == "Восстановить Инцидент":
        await bot.send_message(chat_id=message.from_user.id,
                               text="Выберите номер инцидента:",
                               reply_markup=await closed_incidents())
        await ProfileStatesGroup.recovery_incident.set()  



@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.number_of_incident)
async def load_it_info(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['number'] = message.text
        if len(data['number'])>60:
            await bot.send_message(chat_id=message.from_user.id,
                                   text="Слишком большое количество символов")
        elif not await baza.is_inc_number_unique(data['number']):
            await bot.send_message(chat_id=message.from_user.id,
                                   text="Инцидент с таким номером уже существует, введите номер инцидента заново")
        else:
            await bot.send_message(chat_id=message.from_user.id,
                                   text="Категория инцидента:",
                                   reply_markup=inc_category_kb())
            await ProfileStatesGroup.category_of_incident.set()



@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.description)
async def load_it_info(message: types.Message, state: FSMContext) -> None:
    if message.text == "🔙":
        await bot.send_message(chat_id=message.chat.id,
                               text="Категория инцидента:", reply_markup=inc_category_kb())
        await ProfileStatesGroup.category_of_incident.set()
    else:
        async with state.proxy() as data:
            data['desc'] = message.text
        if len(data['desc'])>2000:
            await bot.send_message(chat_id=message.from_user.id,
                                   text="Слишком большое количество символов")  
        else:  
            await bot.send_message(chat_id=message.from_user.id,
                          text="Приоритет:",
                          reply_markup=priority_kb())
            await ProfileStatesGroup.priority.set()

@dp.callback_query_handler(state=ProfileStatesGroup.recovery_incident)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['choose'] = callback_query.data
        dates = await baza.select_closed_incident(data['choose'])
        await bot.send_message(CHANNEL_ID, f"Инцидент открыт заново\n"
                                           f"Номер инцидента: {dates[1]}\n"
                                           f"Приоритет: {dates[4]}\n"
                                           f"Категория: {dates[2]}\n"
                                           f"Описание: {dates[3]}\n")
        await baza.insert(dates[1], dates[2], dates[3], dates[4], 'Открыт')
        await baza.delete_incident_from_deleted(data['choose'])
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=f"Инцидент с номером {data['choose']} открыт заново",
                               reply_markup=create_incident_kb())

        run_time = datetime.now() + timedelta(seconds=5)
        run_time1 = datetime.now() + timedelta(seconds=10)
        run_time2 = datetime.now() + timedelta(seconds=20)
        run_time3 = datetime.now() + timedelta(seconds=30)
        run_time4 = datetime.now() + timedelta(seconds=40)
        run_time5 = datetime.now() + timedelta(seconds=50)
        if date[4] == 1:
            msg = await bot.send_message(CHANNEL_ID, "@IsmoilovOybek")
            message_id = msg.message_id
            scheduler.add_job(delete_msg, "date", run_date=run_time,
                              args=[message_id],
                              max_instances=1)
            job=scheduler.add_job(prosrochen, "date", run_date=run_time1,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            scheduled_tasks[data['number']] = job
        if date[4] == '2':
            msg = await bot.send_message(CHANNEL_ID, "@Elturan")
            message_id = msg.message_id
            scheduler.add_job(delete_msg, "date", run_date=run_time,
                              args=[message_id],
                              max_instances=1)
            job=scheduler.add_job(prosrochen, "date", run_date=run_time2,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            scheduled_tasks[data['number']] = job
        if date[4] == '3':
            msg = await bot.send_message(CHANNEL_ID, "@Elturan")
            message_id = msg.message_id
            scheduler.add_job(delete_msg, "date", run_date=run_time,
                              args=[message_id],
                              max_instances=1)
            job=scheduler.add_job(prosrochen, "date", run_date=run_time3,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            scheduled_tasks[data['number']] = job
        if date[4] == '4':
            job=scheduler.add_job(prosrochen, "date", run_date=run_time4,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            scheduled_tasks[data['number']] = job
        if date[4] == '5':
            job=scheduler.add_job(prosrochen, "date", run_date=run_time5,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            scheduled_tasks[data['number']] = job

    await ProfileStatesGroup.main_menu.set()

@dp.callback_query_handler(state=ProfileStatesGroup.close_incident)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['choose'] = callback_query.data
        date = await baza.select_incident(data['choose'])
        await bot.send_message(CHANNEL_ID, f"Инцидент закрыт\n"
                                           f"Номер инцидента: {date[1]}\n"
                                           f"Приоритет: {date[4]}\n"
                                           f"Категория: {date[2]}\n"
                                           f"Описание: {date[3]}\n")
        await baza.insert_deleted(date[1], date[2], date[3], date[4], 'Закрыт')
        await baza.delete_incident(data['choose'])
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=f"Инцидент с номером {data['choose']} закрыт",
                               reply_markup=create_incident_kb())
        if date[1] in scheduled_tasks:
            scheduled_tasks[date[1]].remove()
            del scheduled_tasks[date[1]]
        await ProfileStatesGroup.main_menu.set()


@dp.callback_query_handler(state=ProfileStatesGroup.edit_incident)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['choose'] = callback_query.data
    await callback_query.message.delete()
    await bot.send_message(chat_id=callback_query.from_user.id, text="Выберите действие", reply_markup=edit_kb())
    await ProfileStatesGroup.edit_incident_kb.set()


@dp.callback_query_handler(state=ProfileStatesGroup.edit_incident_kb)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "change priority":
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.from_user.id, text="Выберите приоритет",
                               reply_markup=priority_kb())
        await ProfileStatesGroup.change_priority.set()

    if callback_query.data == "prosrochen":
        async with state.proxy() as data:
            await baza.update_status('Просрочен SLA', data['choose'])
            await bot.send_message(chat_id=callback_query.from_user.id,
                                   text=f"Статус инцидента номер {data['choose']} изменён на 'Просрочен SLA'")
            date = await baza.select_incident(data['choose'])
            await callback_query.message.delete()
            await bot.send_message(CHANNEL_ID, f"Просрочен SLA\n"
                                               f"Номер инцидента: {date[1]}\n"
                                               f"Приоритет: {date[4]}\n"
                                               f"Категория: {date[2]}\n"
                                               f"Описание: {date[3]}\n")
            await ProfileStatesGroup.main_menu.set()
    if callback_query.data == "back":
        await bot.send_message(chat_id=callback_query.from_user.id, text="🔙", reply_markup=create_incident_kb())
        await callback_query.message.delete()
        await ProfileStatesGroup.main_menu.set()


@dp.callback_query_handler(state=ProfileStatesGroup.change_priority)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    if (
            callback_query.data == '1' or callback_query.data == '2' or callback_query.data == '3' or callback_query.data == '4' or callback_query.data == '5'):
        async with state.proxy() as data:
            data['priority'] = callback_query.data
        await baza.update_priority(int(data['priority']), data['choose'])
        date = await baza.select_incident(data['choose'])
        await bot.send_message(callback_query.message.chat.id, text=f"Приоритет был изменён на {data['priority']}")
        await callback_query.message.delete()
        await bot.send_message(CHANNEL_ID, text=f"{date[5]}\n"
                                                f"Номер инцидента: {date[1]}\n"
                                                f"Приоритет изменён на {date[4]}\n"
                                                f"Категория: {date[2]}\n"
                                                f"Описание: {date[3]}\n")
        await ProfileStatesGroup.main_menu.set()
    if callback_query.data == 'Back':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Выберите действие",
                                   reply_markup=edit_kb())
            await ProfileStatesGroup.edit_incident_kb.set()


@dp.callback_query_handler(state=ProfileStatesGroup.priority)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    if (
            callback_query.data == '1' or callback_query.data == '2' or callback_query.data == '3' or
            callback_query.data == '4' or callback_query.data == '5'):
        async with state.proxy() as data:
            data['priority'] = callback_query.data
            await baza.insert(data['number'], data['category'], data['desc'], data['priority'], 'Открыто')
            await bot.send_message(CHANNEL_ID, f"Инцидент открыт\n"
                                               f"Номер инцидента: {data['number']}\n"
                                               f"Приоритет: {data['priority']}\n"
                                               f"Категория: {data['category']}\n"
                                               f"Описание: {data['desc']}\n")
            run_time = datetime.now() + timedelta(seconds=5)
            run_time1 = datetime.now() + timedelta(seconds=10)
            run_time2 = datetime.now() + timedelta(seconds=20)
            run_time3 = datetime.now() + timedelta(seconds=30)
            run_time4 = datetime.now() + timedelta(seconds=40)
            run_time5 = datetime.now() + timedelta(seconds=50)
            if data['priority'] == '1':
                msg = await bot.send_message(CHANNEL_ID, "@IsmoilovOybek")
                message_id = msg.message_id
                scheduler.add_job(delete_msg, "date", run_date=run_time,
                                  args=[message_id],
                                  max_instances=1)
                job=scheduler.add_job(prosrochen, "date", run_date=run_time1,
                                  args=[data['number'], data['priority'], data['category'], data['desc']],
                                  max_instances=1)
                scheduled_tasks[data['number']] = job
            if data['priority'] == '2':
                msg = await bot.send_message(CHANNEL_ID, "@Elturan")
                message_id = msg.message_id
                scheduler.add_job(delete_msg, "date", run_date=run_time,
                                  args=[message_id],
                                  max_instances=1)
                job=scheduler.add_job(prosrochen, "date", run_date=run_time2,
                                  args=[data['number'], data['priority'], data['category'], data['desc']],
                                  max_instances=1)
                scheduled_tasks[data['number']] = job
            if data['priority'] == '3':
                msg = await bot.send_message(CHANNEL_ID, "@Elturan")
                message_id = msg.message_id
                scheduler.add_job(delete_msg, "date", run_date=run_time,
                                  args=[message_id],
                                  max_instances=1)
                job=scheduler.add_job(prosrochen, "date", run_date=run_time3,
                                  args=[data['number'], data['priority'], data['category'], data['desc']],
                                  max_instances=1)
                scheduled_tasks[data['number']] = job
            if data['priority'] == '4':
                job=scheduler.add_job(prosrochen, "date", run_date=run_time4,
                                  args=[data['number'], data['priority'], data['category'], data['desc']],
                                  max_instances=1)
                scheduled_tasks[data['number']] = job
            if data['priority'] == '5':
                job=scheduler.add_job(prosrochen, "date", run_date=run_time5,
                                  args=[data['number'], data['priority'], data['category'], data['desc']],
                                  max_instances=1)
                scheduled_tasks[data['number']] = job

        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=callback_query.data, reply_markup=create_incident_kb())

        await ProfileStatesGroup.main_menu.set()
    if callback_query.data == 'Back':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Описание:")
            await ProfileStatesGroup.description.set()


@dp.callback_query_handler(state=ProfileStatesGroup.category_of_incident)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == '#Интернет' or callback_query.data == '#Качество_связи' or callback_query.data == '#Внутренне_ПО' or callback_query.data == '#Услуги' or callback_query.data == '#Digital_Услуги' or callback_query.data == '#Beeline_Uzbekistan' or callback_query.data == '#Beepul' or callback_query.data == '#Оплата' or callback_query.data == '#Beeline_TV':
        async with state.proxy() as data:
            data['category'] = callback_query.data
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.from_user.id, text=data['category'])
        await bot.send_message(chat_id=callback_query.from_user.id,
                               text="Описание:", reply_markup=get_start_and_back_kb())
        await ProfileStatesGroup.description.set()
    if callback_query.data == 'back':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Номер инцидента:")
            await ProfileStatesGroup.number_of_incident.set()


async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, max_connections=100)
    scheduler.start()

async def on_shutdown(dispatcher):
    await bot.delete_webhook()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
