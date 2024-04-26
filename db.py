import asyncpg
import os
import ssl
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduled_tasks = {}
scheduler = AsyncIOScheduler()

class Database:
    def __init__(self):
        self.db_url = os.environ['DATABASE_URL']
        

    async def connect(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return await asyncpg.connect(dsn=self.db_url, ssl=ssl_context)

    async def is_inc_number_unique(self, inc_number):
        async with await self.connect() as conn:
            result = await conn.fetchrow('SELECT * FROM incidents WHERE inc_number = $1', inc_number)
            return result is None

    async def insert(self, inc_number, inc_category, desc, priority, status, created_at, cause):
        async with await self.connect() as conn:
            priority_int = int(priority)
            await conn.execute(
                'INSERT INTO incidents (inc_number, inc_category, "desc", priority, created_at, cause) VALUES ($1, $2, $3, $4, $5, $6);',
                inc_number, inc_category, desc, priority_int, created_at, cause)

    async def insert_deleted(self, inc_number, inc_category, desc, priority, status, created_at, cause):
        async with await self.connect() as conn:
            priority_int = int(priority)
            await conn.execute(
                'INSERT INTO closed_incidents (inc_number, inc_category, "desc", priority, status, created_at, cause) VALUES ($1, $2, $3, $4, $5, $6, $7);',
                inc_number, inc_category, desc, priority_int, status, created_at, cause)

    async def incidents(self):
        async with await self.connect() as conn:
            result = await conn.fetch('SELECT inc_number FROM incidents')
            return result

    async def closed_incidents(self):
        async with await self.connect() as conn:
            result = await conn.fetch('SELECT inc_number FROM closed_incidents')
            return result

    async def select_incident(self, inc_number):
        async with await self.connect() as conn:
            result = await conn.fetchrow('SELECT * FROM incidents WHERE inc_number = $1', inc_number)
            return result

    async def select_closed_incident(self, inc_number):
        async with await self.connect() as conn:
            result = await conn.fetchrow('SELECT * FROM closed_incidents WHERE inc_number = $1', inc_number)
            return result

    async def select_priority(self, inc_number):
        async with await self.connect() as conn:
            result = await conn.fetchrow('SELECT priority FROM incidents WHERE inc_number = $1', inc_number)
            return result[0]

    async def select_created_date(self, inc_number):
        async with await self.connect() as conn:
            result = await conn.fetchrow('SELECT created_at FROM incidents WHERE inc_number = $1', inc_number)
            return result[0]

    async def delete_incident(self, inc_number):
        async with await self.connect() as conn:
            await conn.execute('DELETE FROM incidents WHERE inc_number = $1', inc_number)

    async def delete_incident_from_deleted(self, inc_number):
        async with await self.connect() as conn:
            await conn.execute('DELETE FROM closed_incidents WHERE inc_number = $1', inc_number)

    async def update_status(self, status, inc_number):
        async with await self.connect() as conn:
            await conn.execute("UPDATE incidents SET status = $1 WHERE inc_number = $2", status, inc_number)

    async def update_priority(self, priority, inc_number):
        async with await self.connect() as conn:
            await conn.execute("UPDATE incidents SET priority = $1 WHERE inc_number = $2", priority, inc_number)

    async def update_description(self, desc, inc_number):
        async with await self.connect() as conn:
            await conn.execute('UPDATE incidents SET "desc" = $1 WHERE inc_number = $2', desc, inc_number)

    async def save_task_to_db(self, id, task_type, run_date, args):
        async with await self.connect() as conn:
            try:
                args_json = json.dumps(args)
                await conn.execute("INSERT INTO scheduled_tasks (id, task_type, run_date, args) VALUES ($1, $2, $3, $4)",
                                   id, task_type, run_date, args_json)
                return id
            except Exception as e:
                print("Error saving task to database:", e)
                raise

    async def delete_task(self, task_id):
        async with await self.connect() as conn:
            await conn.execute("DELETE FROM scheduled_tasks WHERE args->>0 = $1", (task_id,))

    async def restore_tasks_from_db(self):
        conn = await self.connect()
        try:
            records = await conn.fetch("SELECT * FROM scheduled_tasks")
        
            for task in records:
                task_id, task_type, run_date, args = task['id'], task['task_type'], task['run_date'], task['args']
                try:
                    if task_type == 'prosrochen':
                        job = scheduler.add_job(prosrochen, "date", run_date=run_date, args=args, max_instances=1)
                        scheduled_tasks[task_id] = job
                except Exception as e:
                    print(f"Error restoring task {task_id}: {e}")
        finally:
            await conn.close()            

    async def delete_task_from_schedule(self, task_id):
        async with await self.connect() as conn:
            result = await conn.fetchrow("SELECT id FROM scheduled_tasks WHERE args->>0 = $1", (task_id,))
            if result:
                job_id = result['id'].replace("-", "")
                print(f"Trying to delete job with ID: {job_id}")
                if scheduler.get_job(str(job_id)):
                    scheduler.remove_job(job_id)
                    print(f"Job {job_id} removed successfully")
                else:
                    print(f"No job with ID {job_id} was found in the scheduler")
            else:
                print(f"No task with args {task_id} found in database")

