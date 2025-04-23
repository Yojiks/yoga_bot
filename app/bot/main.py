import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.bot.handlers.booking_handlers import router
from app.bot.handlers.admin_handlers import router_admin
from app.common.models import async_main
from app.bot.config import BOT_TOKEN

import os

bot = Bot(token=BOT_TOKEN)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher() 


async def main():
    await async_main()
    dp.include_router(router)
    dp.include_router(router_admin)
    await dp.start_polling(bot)
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except:
        print("Exit")