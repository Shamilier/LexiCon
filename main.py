from aiogram import Bot, Dispatcher
import asyncio
from config import BOT_TOKEN
from handlers import start, messages, my_words, test, learn, sets

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

from database import init_db

async def main():
    await init_db()
    dp.include_routers(start.router, my_words.router, test.router,  learn.router,  sets.router, messages.router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


    