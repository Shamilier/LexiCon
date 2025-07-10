import aiosqlite

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ru_word TEXT,
            foreign_word TEXT,
            lang_code TEXT,
            source_set TEXT,
            status TEXT
        );
        """)
        await db.commit()

async def create_user_if_not_exists(user_id: int):
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        exists = await cursor.fetchone()
        if not exists:
            await db.execute("INSERT INTO users (user_id, language) VALUES (?, NULL)", (user_id,))
            await db.commit()

async def save_user_language(user_id: int, lang: str):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("REPLACE INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
        await db.commit()

async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def save_word(
    user_id: int,
    ru_word: str,
    foreign_word: str,
    lang_code: str,
    source_set: str = None,
    status: str = "learning"
):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            INSERT INTO words (user_id, ru_word, foreign_word, lang_code, source_set, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, ru_word, foreign_word, lang_code, source_set, status))
        await db.commit()

async def get_user_words_test(user_id: int):
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("""
            SELECT ru_word, foreign_word, lang_code
            FROM words
            WHERE user_id = ?
              AND status IN ('learning', 'need_check')
            ORDER BY id DESC
        """, (user_id,))
        return await cursor.fetchall()
    
async def get_user_words_learn(user_id: int):
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("""
            SELECT ru_word, foreign_word, lang_code
            FROM words
            WHERE user_id = ?
              AND status IN ('learning', 'learning')
            ORDER BY id DESC
        """, (user_id,))
        return await cursor.fetchall()
    
async def get_random_words(exclude_word: str, lang_code: str, limit: int = 3):
    import aiosqlite

    async with aiosqlite.connect("bot.db") as db:
        if lang_code == 'ru':
            query = "SELECT ru_word FROM words WHERE ru_word != ? ORDER BY RANDOM() LIMIT ?"
        else:
            query = "SELECT foreign_word FROM words WHERE foreign_word != ?  ORDER BY RANDOM() LIMIT ?"

        if lang_code == 'ru':
            cursor = await db.execute(query, (exclude_word, limit))
        else:
            cursor = await db.execute(query, (exclude_word, limit))

        rows = await cursor.fetchall()
        return [r[0] for r in rows]
    
async def delete_word_from_db(user_id: int, ru: str, foreign: str):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "DELETE FROM words WHERE user_id = ? AND ru_word = ? AND foreign_word = ?",
            (user_id, ru, foreign)
        )
        await db.commit()


async def mark_word_as_known(user_id: int, ru_word: str, foreign_word: str):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            UPDATE words
            SET status = 'need_check'
            WHERE user_id = ? AND ru_word = ? AND foreign_word = ?
        """, (user_id, ru_word, foreign_word))
        await db.commit()


async def get_user_words_for_set(user_id: int, source_set: str):
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("""
            SELECT ru_word, foreign_word FROM words
            WHERE user_id = ? AND source_set = ?
        """, (user_id, source_set))
        return await cursor.fetchall()
    
async def count_user_progress_for_set(user_id: int, source_set: str):
    import aiosqlite
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("""
            SELECT COUNT(*) FROM words
            WHERE user_id = ? AND source_set = ?
              AND status IN ('known', 'learning')
        """, (user_id, source_set))
        row = await cursor.fetchone()
        return row[0] if row else 0