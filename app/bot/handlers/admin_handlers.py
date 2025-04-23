from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy import select

from app.common.requests import get_user_by_tg_id
from app.common.models import User, Slot, Booking, async_session
from app.bot.middlewares import TestMiddleware

import app.bot.handlers.keyboards as kb
import app.common.requests as rq

router_admin = Router()

@router_admin.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split("_")[2])
    
    
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.answer("Ошибка", show_alert=True)
            return
        
        await rq.mark_payment_confirmed(booking_id)
        
        user = await session.get(User, booking.user_id)
        await bot.send_message(
            chat_id = user.tg_id,
            text = "✅ Ваша оплата подтверждена. До встречи на йоге!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ На главную",   callback_data="go_back")]
            ])
        )
        
        await callback.message.edit_text("Оплата подтверждена ✅")
        await callback.answer()