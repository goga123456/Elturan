import asyncpg
import os

class Database:
    def __init__(self):
        self.db_url = os.environ['DATABASE_URL']

    async def connect(self):
        return await asyncpg.connect(dsn=self.db_url)


    async def is_inc_number_unique(self, inc_number):
        conn = await self.connect()
        try:
            # Проверяем, существует ли запись с таким inc_number
            result = await conn.fetchrow('SELECT * FROM incidents WHERE inc_number = $1', inc_number)
            return result is None  # Возвращаем True, если такой номер не найден (уникален)
        finally:
            await conn.close()
    

    async def insert(self, inc_number, inc_category, desc, priority, status):
        conn = await self.connect()
        try:
            # Преобразование priority в целое число
            priority_int = int(priority)

            await conn.execute(
                'INSERT INTO incidents (inc_number, inc_category, "desc", priority, status) VALUES ($1, $2, $3, $4, $5);',
                inc_number, inc_category, desc, priority_int, status)
        finally:
            await conn.close()

    async def insert_deleted(self, inc_number, inc_category, desc, priority, status):
        conn = await self.connect()
        try:
            # Преобразование priority в целое число
            priority_int = int(priority)

            await conn.execute(
                'INSERT INTO closed_incidents (inc_number, inc_category, "desc", priority, status) VALUES ($1, $2, $3, $4, $5);',
                inc_number, inc_category, desc, priority_int, status)
        finally:
            await conn.close()   

    async def incidents(self):
        conn = await self.connect()
        try:
            result = await conn.fetch('SELECT inc_number FROM incidents')
            return result
        finally:
            await conn.close()

    async def closed_incidents(self):
        conn = await self.connect()
        try:
            result = await conn.fetch('SELECT inc_number FROM closed_incidents')
            return result
        finally:
            await conn.close()

    async def select_incident(self, inc_number):
        conn = await self.connect()
        try:
            result = await conn.fetchrow('SELECT * FROM incidents WHERE inc_number = $1', inc_number)
            return result
        finally:
            await conn.close()

    async def select_closed_incident(self, inc_number):
        conn = await self.connect()
        try:
            result = await conn.fetchrow('SELECT * FROM closed_incidents WHERE inc_number = $1', inc_number)
            return result
        finally:
            await conn.close()
    

    async def select_priority(self, inc_number):
        conn = await self.connect()
        try:
            result = await conn.fetchrow('SELECT priority FROM incidents WHERE inc_number = $1', inc_number)
            return result
        finally:
            await conn.close()

    async def delete_incident(self, inc_number):
        conn = await self.connect()
        try:
            await conn.execute('DELETE FROM incidents WHERE inc_number = $1', inc_number)
        finally:
            await conn.close()

    async def delete_incident_from_deleted(self, inc_number):
        conn = await self.connect()
        try:
            await conn.execute('DELETE FROM closed_incidents WHERE inc_number = $1', inc_number)
        finally:
            await conn.close()
    
    async def update_status(self, status, inc_number):
        conn = await self.connect()
        try:
            await conn.execute("UPDATE incidents SET status = $1 WHERE inc_number = $2", status, inc_number)
        finally:
            await conn.close()

    async def update_priority(self, priority, inc_number):
        conn = await self.connect()
        try:
            await conn.execute("UPDATE incidents SET priority = $1 WHERE inc_number = $2", priority, inc_number)
        finally:
            await conn.close()

    async def update_description(self, desc, inc_number):
        conn = await self.connect()
        try:
            await conn.execute("UPDATE incidents SET 'desc' = $1 WHERE inc_number = $2", desc, inc_number)
        finally:
            await conn.close()

