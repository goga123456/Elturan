import asyncpg
import os
import ssl
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler()

class Database:
    def __init__(self):
        self.db_url = os.environ['DATABASE_URL']
        self.pool = None

    async def init_pool(self):
        self.pool = await asyncpg.create_pool(self.db_url, ssl='require')

    async def connect(self):
        if self.pool is None:
            await self.init_pool()  # Ensure the pool is initialized
        return self.pool

    async def is_inc_number_unique(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:  # Используем соединение из пула
            result = await conn.fetchrow('SELECT * FROM incidents WHERE inc_number = $1', inc_number)
            return result is None

    async def insert(self, inc_number, inc_category, desc, priority, status, created_at, cause):
        pool = await self.connect()
        async with pool.acquire() as conn:
            priority_int = int(priority)
            await conn.execute(
                'INSERT INTO incidents (inc_number, inc_category, "desc", priority, created_at, cause) VALUES ($1, $2, $3, $4, $5, $6);',
                inc_number, inc_category, desc, priority_int, created_at, cause)

    async def insert_deleted(self, inc_number, inc_category, desc, priority, status, created_at, cause):
        pool = await self.connect()
        async with pool.acquire() as conn:
            priority_int = int(priority)
            await conn.execute(
                'INSERT INTO closed_incidents (inc_number, inc_category, "desc", priority, status, created_at, cause) VALUES ($1, $2, $3, $4, $5, $6, $7);',
                inc_number, inc_category, desc, priority_int, status, created_at, cause)

    async def incidents(self):
        pool = await self.connect()
        async with pool.acquire() as conn:
            result = await conn.fetch('SELECT inc_number FROM incidents')
            return result

    async def closed_incidents(self):
        pool = await self.connect()
        async with pool.acquire() as conn:
            result = await conn.fetch('SELECT inc_number FROM closed_incidents')
            return result

    async def select_incident(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            result = await conn.fetchrow('SELECT * FROM incidents WHERE inc_number = $1', inc_number)
            return result

    async def select_closed_incident(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            result = await conn.fetchrow('SELECT * FROM closed_incidents WHERE inc_number = $1', inc_number)
            return result

    async def select_priority(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            result = await conn.fetchrow('SELECT priority FROM incidents WHERE inc_number = $1', inc_number)
            return result[0]

    async def select_created_date(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            result = await conn.fetchrow('SELECT created_at FROM incidents WHERE inc_number = $1', inc_number)
            return result[0]

    async def delete_incident(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM incidents WHERE inc_number = $1', inc_number)

    async def delete_incident_from_deleted(self, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM closed_incidents WHERE inc_number = $1', inc_number)

    async def update_status(self, status, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE incidents SET status = $1 WHERE inc_number = $2", status, inc_number)

    async def update_priority(self, priority, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE incidents SET priority = $1 WHERE inc_number = $2", priority, inc_number)

    async def update_description(self, desc, inc_number):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute('UPDATE incidents SET "desc" = $1 WHERE inc_number = $2', desc, inc_number)

    async def save_task_to_db(self, id, task_type, run_date, args):
        pool = await self.connect()
        async with pool.acquire() as conn:
            try:
                args_json = json.dumps(args)
                await conn.execute("INSERT INTO scheduled_tasks (id, task_type, run_date, args) VALUES ($1, $2, $3, $4)",
                                   id, task_type, run_date, args_json)
                return id
            except Exception as e:
                print("Error saving task to database:", e)
                raise

    async def delete_task(self, task_id):
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM scheduled_tasks WHERE args->>0 = $1", (task_id,))     

    async def delete_task_from_schedule(self, task_id):
        pool = await self.connect()
        async with pool.acquire() as conn:
            # Удаление лишней запятой и скобок вокруг task_id
            result = await conn.execute("SELECT id FROM scheduled_tasks WHERE args->>0 = $1", (task_id,))
            if result:
                job_id = str(result['id']).replace("-", "")
                print(f"Trying to delete job with ID: {job_id}")
                # Убедитесь, что переменная scheduler правильно определена и доступна
                if scheduler.get_job(str(job_id)):
                    scheduler.remove_job(job_id)
                    print(f"Job {job_id} removed successfully")
                else:
                    print(f"No job with ID {job_id} was found in the scheduler")
                    print(f"Type of task_id: {type(task_id)}, Value of task_id: {task_id}")
            else:
                print(f"No task with args {task_id} found in database")

