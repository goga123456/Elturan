import asyncio
from datetime import datetime, timedelta
import json
import psycopg2
from aiogram import types, executor, Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from markups.inline_markups import priority_kb, edit_kb, inc_category_kb, cause_kb
from markups.reply_markups_start_and_back import *
from states import ProfileStatesGroup
import os
import asyncpg
from aiogram.utils.executor import start_webhook
import logging
from db import Database
from apscheduler.jobstores.base import JobLookupError
import uuid
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

DATABASE_URL = os.environ.get('DATABASE_URL')  # Use environment variable for security


async def save_task_to_db(id, task_type, run_date, args):
    conn = await asyncpg.connect(DATABASE_URL, ssl='require')
    try:
        args_json = json.dumps(args)
        async with conn.transaction():  # Автоматический commit или rollback
            await conn.execute(
                "INSERT INTO scheduled_tasks (id, task_type, run_date, args) VALUES ($1, $2, $3, $4)",
                id, task_type, run_date, args_json
            )
    except asyncpg.PostgresError as e:
        print("Error saving task to database:", e)
    finally:
        await conn.close()
    return id
  
async def print_all_jobs():
    jobs = scheduler.get_jobs()
    print("Запланированные задачи:")
    for job in jobs:
        print(f"ID: {job.id}, Имя функции: {job.func.__name__}, Следующий запуск: {job.next_run_time}")    
      
async def delete_task(task_id):
    conn = await asyncpg.connect(DATABASE_URL, ssl='require')
    try:
        async with conn.transaction():
            await conn.execute("DELETE FROM scheduled_tasks WHERE args->>0 = $1", task_id)
    finally:
        await conn.close()

async def delete_task_from_schedule(task_id):
    conn = await asyncpg.connect(DATABASE_URL, ssl='require')
    try:
        result = await conn.fetchrow("SELECT id FROM scheduled_tasks WHERE args->>0 = $1", task_id)
        if result:
            job_id = str(result['id']).replace("-", "")
            print(f"Trying to delete job with ID: {job_id}")
            if scheduler.get_job(str(job_id)):
                scheduler.remove_job(job_id)
                print(f"Job {job_id} removed successfully")
            else:
                print(f"No job with ID {job_id} was found in the scheduler")
    except asyncpg.PostgresError as e:
        print(f"Error deleting task {task_id} from schedule:", e)
        await conn.execute('ROLLBACK')
        raise
    finally:
        await conn.close()

async def restore_tasks_from_db():
    conn = await asyncpg.connect(os.environ.get('DATABASE_URL'), ssl='require')
    try:
        tasks = await conn.fetch("SELECT * FROM scheduled_tasks")
        job = None
        for task in tasks:
            task_id, task_type, run_date, args_json = task[0], task[1], task[2], task[3]
            args = json.loads(args_json)  # Предполагаем, что args - это JSON-строка
            try:
                if task_type == 'prosrochen' and isinstance(args, list) and len(args) == 4:
                    job = scheduler.add_job(prosrochen, "date", run_date=run_date, args=args, max_instances=1)
                    scheduled_tasks[task_id] = job
            except Exception as e:
                print(f"Error restoring task {task_id}: {e}")
    except asyncpg.PostgresError as e:
        print(f"Error restoring task: {e}")
    finally:
        await conn.close()


async def prosrochen(number, priority, category, desc):
    await baza.update_status(status="Просрочен SLA", inc_number=number)
    await bot.send_message(CHANNEL_ID, f"{category}\n"
                                       f"‼️ПРОСРОЧЕН SLA Инц. №{number}\n"
                                       f"{desc}\n"
                                       f"Приоритет: {priority}\n\n")
    await delete_task(number)

async def incidents() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    incidents_list = await baza.incidents()

    # Итерируем по списку инцидентов, создавая новый ряд каждые два элемента
    for i in range(0, len(incidents_list), 2):
        # Создаем кнопки для текущего ряда
        buttons = [InlineKeyboardButton(f'{incident[0]}', callback_data=f'{incident[0]}') for incident in incidents_list[i:i+2]]
        
        # Добавляем ряд в разметку
        markup.row(*buttons)

    return markup



async def closed_incidents(page=0) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    incidents_list = await baza.closed_incidents()

    # Определяем максимальное количество кнопок на одной странице
    buttons_per_page = 30

    # Определяем количество кнопок на одной строке
    buttons_per_row = 3

    # Определяем индексы начала и конца текущей страницы
    start_index = page * buttons_per_page
    end_index = min((page + 1) * buttons_per_page, len(incidents_list))

    # Создаем кнопки для текущей страницы
    buttons = [InlineKeyboardButton(f'{incident[0]}', callback_data=f'{incident[0]}') for incident in incidents_list[start_index:end_index]]

    # Делим кнопки на ряды по buttons_per_row кнопок в каждом
    rows = [buttons[i:i+buttons_per_row] for i in range(0, len(buttons), buttons_per_row)]

    # Добавляем ряды в разметку
    for row in rows:
        markup.row(*row)

    # Добавляем кнопки "Вперед" и "Назад", если это возможно
    if page > 0:
        markup.row(InlineKeyboardButton("Назад", callback_data=f"closed_page_{page-1}"))
    if end_index < len(incidents_list):
        markup.row(InlineKeyboardButton("Вперед", callback_data=f"closed_page_{page+1}"))

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
                               text="Выберите инцидент ,который хотите закрыть",
                               reply_markup=get_start_kb())
        await bot.send_message(chat_id=message.from_user.id,
                               text="Список инцидентов",
                               reply_markup=await incidents())
        await ProfileStatesGroup.close_incident.set()
    if message.text == "Редактировать Инцидент":
        await bot.send_message(chat_id=message.from_user.id,
                               text="Выберите инцидент ,который хотите редактировать",
                               reply_markup=get_start_kb())
        await bot.send_message(chat_id=message.from_user.id,
                               text="Список инцидентов:",
                               reply_markup=await incidents())
        await ProfileStatesGroup.edit_incident.set()
    if message.text == "Восстановить Инцидент":
        await bot.send_message(chat_id=message.from_user.id,
                               text="Выберите инцидент ,который хотите восстановить",
                               reply_markup=get_start_kb())
        await bot.send_message(chat_id=message.from_user.id,
                               text="Список инцидентов:",
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

@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.category_hand)
async def load_it_info(message: types.Message, state: FSMContext) -> None:
    if message.text == "🔙":
        await bot.send_message(chat_id=message.chat.id,
                               text="Категория инцидента:", reply_markup=inc_category_kb())
        await ProfileStatesGroup.category_of_incident.set()
    else:
        async with state.proxy() as data:
            data['category'] = f"#{message.text}"
        if len(data['category'])>100:
            await bot.send_message(chat_id=message.from_user.id,
                                   text="Слишком большое количество символов")  
        else:  
            await bot.send_message(chat_id=message.from_user.id,
                          text="Описание:", reply_markup=get_start_kb())
            await ProfileStatesGroup.description.set()



@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.change_desc)
async def load_it_info(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['desc'] = message.text
        date = await baza.select_incident(data['choose'])
        if len(data['desc'])>2000:
            await bot.send_message(chat_id=message.from_user.id,
                                   text="Слишком большое количество символов")  
        else:
            if date[7] is not None:
                await bot.send_message(CHANNEL_ID, f"{date[2]}\n"
                                               f"🆕ОТКРЫТ Инц. №{date[1]}\n"
                                               f"{data['desc']}\n"
                                               f"Приоритет: {date[4]}\n"
                                               f"{date[7]}\n\n"
                                               f"@{message.from_user.username}")
            else:
                await bot.send_message(CHANNEL_ID, f"{date[2]}\n"
                                               f"🆕ОТКРЫТ Инц. №{date[1]}\n"
                                               f"{data['desc']}\n"
                                               f"Приоритет: {date[4]}\n\n"
                                               f"@{message.from_user.username}")
            
            await baza.update_description(data['desc'], date[1])
            await bot.send_message(chat_id=message.from_user.id,
                           text="Описание изменено")
            await state.finish()

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
        if dates and dates[7] is not None:
            await bot.send_message(CHANNEL_ID, f"{dates[2]}\n"
                                           f"🆕ОТКРЫТ Инц. №{dates[1]}\n"
                                           f"{dates[3]}\n"
                                           f"Приоритет: {dates[4]}\n"
                                           f"{dates[7]}\n\n"
                                           f"@{callback_query.from_user.username}")
        else:
            await bot.send_message(CHANNEL_ID, f"{dates[2]}\n"
                                           f"🆕ОТКРЫТ Инц. №{dates[1]}\n"
                                           f"{dates[3]}\n"
                                           f"Приоритет: {dates[4]}\n\n"
                                           f"@{callback_query.from_user.username}")
        
        await baza.insert(dates[1], dates[2], dates[3], dates[4], 'Открыт', datetime.now(), dates[7])
        await baza.delete_incident_from_deleted(data['choose'])
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=f"Инцидент с номером {data['choose']} открыт заново",
                               reply_markup=create_incident_kb())
        run_time1 = datetime.now() + timedelta(hours=4)
        run_time2 = datetime.now() + timedelta(hours=12)
        run_time3 = datetime.now() + timedelta(hours=24)
        run_time4 = datetime.now() + timedelta(hours=72)
        run_time5 = datetime.now() + timedelta(hours=168)
        if dates[4] == 1:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time1,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time1, [dates[1], dates[4], dates[2], dates[3]])
        if dates[4] == 2:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time2,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time2, [dates[1], dates[4], dates[2], dates[3]])
            
        if dates[4] == 3:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time3,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time3, [dates[1], dates[4], dates[2], dates[3]])
            
        if dates[4] == 4:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time4,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time4, [dates[1], dates[4], dates[2], dates[3]])
            
        if dates[4] == 5:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time5,
                              args=[dates[1], dates[4], dates[2], dates[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time5, [dates[1], dates[4], dates[2], dates[3]])
            
    await ProfileStatesGroup.main_menu.set()

@dp.callback_query_handler(state=ProfileStatesGroup.close_incident)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['choose'] = callback_query.data
        date = await baza.select_incident(data['choose'])
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=f"{date[3]}")
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=f"Напишите как решили данный инцидент",
                               reply_markup=get_start_kb())
        await ProfileStatesGroup.solve.set()
       

@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.solve)
async def load_it_info(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['solve'] = message.text
        date = await baza.select_incident(data['choose'])
        await bot.send_message(CHANNEL_ID, f"{date[2]}\n"
                                           f"✅ЗАКРЫТ Инц. №{date[1]}\n"
                                           f"{date[3]}\n"
                                           f"Приоритет: {date[4]}\n"
                                           f"{data['solve']}\n\n"
                                           f"@{message.from_user.username}")
        date = await baza.select_incident(data['choose'])
        await baza.insert_deleted(date[1], date[2], date[3], date[4], 'Закрыт', date[6], date[7])      
        await print_all_jobs()
        await delete_task_from_schedule(date[1])
        await delete_task(date[1]) 
        await bot.send_message(chat_id=message.chat.id,
                               text=f"Инцидент с номером {data['choose']} закрыт")
        await baza.delete_incident(data['choose'])
        await state.finish()

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
            if date[7] is not None:
                await bot.send_message(CHANNEL_ID, f"{date[2]}\n"
                                                   f"‼️ ПРОСРОЧЕН SLA Инц. №{date[1]}\n"
                                                   f"{date[3]}\n"
                                                   f"Приоритет: {date[4]}\n"
                                                   f"{date[7]}\n\n"
                                                   f"@{callback_query.from_user.username}")
            else:
                await bot.send_message(CHANNEL_ID, f"{date[2]}\n"
                                                   f"‼️ ПРОСРОЧЕН SLA Инц. №{date[1]}\n"
                                                   f"{date[3]}\n"
                                                   f"Приоритет: {date[4]}\n\n"
                                                   f"@{callback_query.from_user.username}")
            await ProfileStatesGroup.main_menu.set()
            await delete_task_from_schedule(date[1])
            await delete_task(date[1])
    if callback_query.data == "change_desc":
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.from_user.id, text="Описание:",
                               reply_markup=get_start_kb())
        await ProfileStatesGroup.change_desc.set()
            
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
        await bot.send_message(callback_query.message.chat.id, text=f"Приоритет был изменён на {data['priority']}")      
        ex_priority = await baza.select_priority(data['choose'])
        date = await baza.select_incident(data['choose'])
        if date[7] is not None:
            await bot.send_message(CHANNEL_ID, text=f"{date[2]}\n"
                                                    f"🆕ОТКРЫТ Инц. №{date[1]}\n"
                                                    f"{date[3]}\n"
                                                    f"Приоритет изменён на {date[4]}\n"
                                                    f"{date[7]}\n\n"
                                                    f"@{callback_query.from_user.username}")
        else:
            await bot.send_message(CHANNEL_ID, text=f"{date[2]}\n"
                                                    f"🆕ОТКРЫТ Инц. №{date[1]}\n"
                                                    f"{date[3]}\n"
                                                    f"Приоритет изменён на {date[4]}\n\n"
                                                    f"@{callback_query.from_user.username}")  
          
        await delete_task_from_schedule(date[1])
        await delete_task(date[1])
              
        created_at = await baza.select_created_date(date[1])   
        difference = datetime.now() - created_at    

        if int(data['priority']) <= int(ex_priority):
            run_time1 = datetime.now() + timedelta(hours=4)
            run_time2 = datetime.now() + timedelta(hours=12)
            run_time3 = datetime.now() + timedelta(hours=24)
            run_time4 = datetime.now() + timedelta(hours=72)
            run_time5 = datetime.now() + timedelta(hours=168)
        elif int(data['priority']) > int(ex_priority):
            run_time1 = datetime.now() + timedelta(hours=4) - difference
            run_time2 = datetime.now() + timedelta(hours=12) - difference
            run_time3 = datetime.now() + timedelta(hours=24) - difference
            run_time4 = datetime.now() + timedelta(hours=72) - difference
            run_time5 = datetime.now() + timedelta(hours=168) - difference
            
            
        if date[4] == 1:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time1,
                              args=[date[1], date[4], date[2], date[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time1, [date[1], date[4], date[2], date[3]])
        if date[4] == 2:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time2,
                              args=[date[1], date[4], date[2], date[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time2, [date[1], date[4], date[2], date[3]])
        if date[4] == 3:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time3,
                              args=[date[1], date[4], date[2], date[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time3, [date[1], date[4], date[2], date[3]])
        if date[4] == 4:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time4,
                              args=[date[1], date[4], date[2], date[3]],
                              max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time4, [date[1], date[4], date[2], date[3]])
        if date[4] == 5:
            job=scheduler.add_job(prosrochen, "date", run_date=run_time5,
                              args=[date[1], date[4], date[2], date[3]],
                              max_instances=1) 
            await save_task_to_db(job.id, 'prosrochen', run_time5, [date[1], date[4], date[2], date[3]])
        #await callback_query.message.delete()  
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
        await callback_query.message.delete()  
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text=callback_query.data)
        await bot.send_message(callback_query.message.chat.id, 
                                               "Если вы знаете причину ,можете добавить её",
                               reply_markup=cause_kb())
        await ProfileStatesGroup.cause.set()
    if callback_query.data == 'Back':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Описание:")
            await ProfileStatesGroup.description.set()


@dp.callback_query_handler(state=ProfileStatesGroup.cause)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == 'add_cause':
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.message.chat.id,
                               text="Причина:")
        await ProfileStatesGroup.cause_yes.set()
    if callback_query.data == 'No':
        async with state.proxy() as data:
            await baza.insert(data['number'], data['category'], data['desc'], data['priority'], 'Открыто',
                              datetime.now(), None)
            await bot.send_message(CHANNEL_ID, f"{data['category']}\n"
                                               f"🆕ОТКРЫТ Инц. №{data['number']}\n"
                                               f"{data['desc']}\n"
                                               f"Приоритет: {data['priority']}\n\n"
                                               f"@{callback_query.from_user.username}")
            run_time1 = datetime.now() + timedelta(hours=4)
            run_time2 = datetime.now() + timedelta(hours=12)
            run_time3 = datetime.now() + timedelta(hours=24)
            run_time4 = datetime.now() + timedelta(hours=72)
            run_time5 = datetime.now() + timedelta(hours=168)

            # task_uuid = str(uuid.uuid4())
            if data['priority'] == '1':
                job = scheduler.add_job(prosrochen, "date", run_date=run_time1,
                                        args=[data['number'], data['priority'], data['category'], data['desc']],
                                        max_instances=1)
                await print_all_jobs()
                await save_task_to_db(job.id, 'prosrochen', run_time1,
                                [data['number'], data['priority'], data['category'], data['desc']])
            if data['priority'] == '2':
                job = scheduler.add_job(prosrochen, "date", run_date=run_time2,
                                        args=[data['number'], data['priority'], data['category'], data['desc']],
                                        max_instances=1)
                await print_all_jobs()
                await save_task_to_db(job.id, 'prosrochen', run_time2,
                                [data['number'], data['priority'], data['category'], data['desc']])
            if data['priority'] == '3':
                job = scheduler.add_job(prosrochen, "date", run_date=run_time3,
                                        args=[data['number'], data['priority'], data['category'], data['desc']],
                                        max_instances=1)
                await print_all_jobs()
                await save_task_to_db(job.id, 'prosrochen', run_time3,
                                [data['number'], data['priority'], data['category'], data['desc']])
            if data['priority'] == '4':
                job = scheduler.add_job(prosrochen, "date", run_date=run_time4,
                                        args=[data['number'], data['priority'], data['category'], data['desc']],
                                        max_instances=1)
                await save_task_to_db(job.id, 'prosrochen', run_time4,
                                [data['number'], data['priority'], data['category'], data['desc']])
            if data['priority'] == '5':
                job = scheduler.add_job(prosrochen, "date", run_date=run_time5,
                                        args=[data['number'], data['priority'], data['category'], data['desc']],
                                        max_instances=1)
                await save_task_to_db(job.id, 'prosrochen', run_time5,
                                [data['number'], data['priority'], data['category'], data['desc']])
        await callback_query.message.delete()
        await bot.send_message(callback_query.message.chat.id,
                               text=f"{data['category']}\n"
                               f"🆕ОТКРЫТ Инц. №{data['number']}\n"
                               f"{data['desc']}\n"
                               f"Приоритет: {data['priority']}\n",
                               reply_markup=create_incident_kb())
        await ProfileStatesGroup.main_menu.set()
    if callback_query.data == 'Back':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Приоритет:",
                                   reply_markup=priority_kb())
            await ProfileStatesGroup.priority.set()

@dp.message_handler(content_types=[*types.ContentTypes.TEXT], state=ProfileStatesGroup.cause_yes)
async def load_it_info(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['cause'] = message.text

        await baza.insert(data['number'], data['category'], data['desc'], data['priority'], 'Открыто',
                          datetime.now(), data['cause'])
        await bot.send_message(CHANNEL_ID, f"{data['category']}\n"
                                           f"🆕ОТКРЫТ Инц. №{data['number']}\n"
                                           f"{data['desc']}\n"
                                           f"Приоритет: {data['priority']}\n"
                                           f"{data['cause']}\n\n"
                                           f"@{message.from_user.username}")
        run_time1 = datetime.now() + timedelta(hours=4)
        run_time2 = datetime.now() + timedelta(hours=12)
        run_time3 = datetime.now() + timedelta(hours=24)
        run_time4 = datetime.now() + timedelta(hours=72)
        run_time5 = datetime.now() + timedelta(hours=168)

        # task_uuid = str(uuid.uuid4())
        if data['priority'] == '1':
            job = scheduler.add_job(prosrochen, "date", run_date=run_time1,
                                    args=[data['number'], data['priority'], data['category'], data['desc']],
                                    max_instances=1)
            await print_all_jobs()
            await save_task_to_db(job.id, 'prosrochen', run_time1,
                            [data['number'], data['priority'], data['category'], data['desc']])
        if data['priority'] == '2':
            job = scheduler.add_job(prosrochen, "date", run_date=run_time2,
                                    args=[data['number'], data['priority'], data['category'], data['desc']],
                                    max_instances=1)
            await print_all_jobs()
            await save_task_to_db(job.id, 'prosrochen', run_time2,
                            [data['number'], data['priority'], data['category'], data['desc']])
        if data['priority'] == '3':
            job = scheduler.add_job(prosrochen, "date", run_date=run_time3,
                                    args=[data['number'], data['priority'], data['category'], data['desc']],
                                    max_instances=1)
            await print_all_jobs()
            await save_task_to_db(job.id, 'prosrochen', run_time3,
                            [data['number'], data['priority'], data['category'], data['desc']])
        if data['priority'] == '4':
            job = scheduler.add_job(prosrochen, "date", run_date=run_time4,
                                    args=[data['number'], data['priority'], data['category'], data['desc']],
                                    max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time4,
                            [data['number'], data['priority'], data['category'], data['desc']])
        if data['priority'] == '5':
            job = scheduler.add_job(prosrochen, "date", run_date=run_time5,
                                    args=[data['number'], data['priority'], data['category'], data['desc']],
                                    max_instances=1)
            await save_task_to_db(job.id, 'prosrochen', run_time5,
                            [data['number'], data['priority'], data['category'], data['desc']])
        await bot.send_message(chat_id=message.chat.id,
                               text=f"Инцидент открыт",
                               reply_markup=create_incident_kb())
        await ProfileStatesGroup.main_menu.set()

@dp.callback_query_handler(state=ProfileStatesGroup.category_of_incident)
async def edu_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == '#Качество_связи_и_интернета' or callback_query.data == '#app_Beeline_Uzbekistan' or callback_query.data == '#Внутренне_ПО' or callback_query.data == '#База_знаний' or callback_query.data == '#Интерфейсы_CPA' or callback_query.data == '#Beepul' or callback_query.data == '#Beeline_TV' or callback_query.data == '#Beeline_Music' or callback_query.data == '#Дозвон_в_КЦ' or callback_query.data == '#Акции' or callback_query.data == '#CVM_активности' or callback_query.data == '#USSD_запросы' or callback_query.data == '#SMS' or callback_query.data == '#Корпоративный_сайт' or callback_query.data == '#Balance' or callback_query.data == '#Яндекс_Плюс' or callback_query.data == '#Телеграмм' or callback_query.data == '#Beeline_Visa' or callback_query.data == '#OQ_mobile':
        async with state.proxy() as data:
            data['category'] = callback_query.data
        await callback_query.message.delete()
        await bot.send_message(chat_id=callback_query.from_user.id, text=data['category'])
        await bot.send_message(chat_id=callback_query.from_user.id,
                               text="Описание:", reply_markup=get_start_kb())
        await ProfileStatesGroup.description.set()
    if callback_query.data == 'hand':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Напишите категорию")
            await ProfileStatesGroup.category_hand.set()  
    if callback_query.data == 'back':
        async with state.proxy() as data:
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Номер инцидента:")
            await ProfileStatesGroup.number_of_incident.set()

async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, max_connections=100)
    scheduler.start()
    await restore_tasks_from_db()

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

