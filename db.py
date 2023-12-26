import aiosqlite3
import asyncpg
import os


class Database:
    #def __init__(self, db_file):
    #    self.db_file = db_file

    def __init__(self):
        self.db_url = os.environ['DATABASE_URL']

    async def insert(self, inc_number, inc_category, desc, priority, status):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                'INSERT INTO incidents (inc_number, inc_category, desc, priority, status) VALUES (?, ?, ?, ?, ?);',
                (inc_number, inc_category, desc, priority, status))
            await conn.commit()

    async def incidents(self):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            result = await cursor.execute('SELECT inc_number FROM incidents')
            return result.fetchall()

    async def select_incident(self, inc_number):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            result = await cursor.execute('SELECT * FROM incidents WHERE inc_number = ?', (inc_number,))
            return result.fetchone()

    async def select_priority(self, inc_number):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            result = await cursor.execute('SELECT priority FROM incidents WHERE inc_number = ?', (inc_number,))
            return result.fetchone()

    async def delete_incident(self, inc_number):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            await cursor.execute('DELETE FROM incidents WHERE inc_number = ?', (inc_number,))
            await conn.commit()

    async def update_status(self, status, inc_number):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            await cursor.execute("UPDATE incidents SET status = ? WHERE inc_number = ?", (status, inc_number))
            await conn.commit()

    async def update_priority(self, priority, inc_number):
        async with aiosqlite3.connect(self.db_file) as conn:
            cursor = await conn.cursor()
            await cursor.execute("UPDATE incidents SET priority = ? WHERE inc_number = ?", (priority, inc_number))
            await conn.commit()



