import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.bot.handlers.booking_handlers import router
from app.common.models import async_main

bot = Bot(token="8057743274:AAH-6HPJAj0ZAWIaMezg5mdIMzF3AUGwyHk")
dp = Dispatcher()


async def main():
    await async_main()
    dp.include_router(router)
    await dp.start_polling(bot)
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except:
        print("Exit")