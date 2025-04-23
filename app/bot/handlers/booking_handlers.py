from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.common.requests import get_user_by_tg_id
from app.common.models import User, Slot, Booking, async_session
from app.bot.middlewares import TestMiddleware

import app.bot.handlers.keyboards as kb
import app.common.requests as rq
from app.bot.handlers.keyboards import go_back_markup
from app.common.requests import BookingResult

router = Router()

router.message.outer_middleware(TestMiddleware())

class Reg(StatesGroup):
    name = State()
    email = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    user = await get_user_by_tg_id(tg_id)
    
    if user:
        await message.answer(f"Вы уже зарегистрированы.\nEmail: {user.email}", reply_markup=kb.main)
    else:
        await message.answer("Привет! Введи, пожалуйста, корпоративный email:")
        await state.set_state(Reg.email)
    
    
@router.message(Reg.email)
async def process_email(message: Message, state: FSMContext):
    email = message.text
    
    await rq.set_user(tg_id=message.from_user.id, email=email)

    await message.answer(f"Спасибо, регистрация завершена.\nEmail: {email}")
    await state.clear()
    
    
@router.callback_query(F.data == 'free_slots')
async def show_slots(callback: CallbackQuery):
    await callback.answer('Вы выбрали свободные слоты')
    
    async with async_session() as session:
        result = await session.execute(select(Slot).order_by(Slot.date))
        slots = result.scalars().all()
        
    print(f"[DEBUG] Найдено слотов: {len(slots)}")
    for s in slots:
        print(f"[DEBUG] Слот: {s.id}, date={s.date}, type={type(s.date)}")
        
    if not slots:
        await callback.message.edit_text("Нет доступных слотов")
        return
        
    markup = await kb.inline_slots(slots)
    await callback.message.edit_text("Свободные слоты:", reply_markup=markup)
    

@router.callback_query(F.data == 'contacts')
async def contacts(callback: CallbackQuery):
    await callback.answer('Вы выбрали контакты')
    
    await callback.message.edit_text(
        "Связаться с нами: +79885556644",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Назад",   callback_data="go_back")]
        ])
    )

ADMINS = [793734889]

@router.callback_query(F.data.startswith("confirm_payment_"))
async def notify_admin(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[2])
    bot = callback.bot  # берём Bot из callback

    # 1) Внутри сессии подгружаем и booking, и slot
    async with async_session() as session:
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.slot))    # <-- eager load slot
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        # Подгружаем User
        user = await session.get(User, booking.user_id)

        # Сразу достаём всё, что нужно
        slot = booking.slot
        dt     = slot.date.strftime("%d.%m %H:%M")
        amount = slot.price_per_person
        code   = booking.confirmation_code

    # 2) Составляем сообщение
    msg = (
        f"💳 *Подтверждение оплаты*\n\n"
        f"📧 Email: `{user.email}`\n"
        f"📅 Слот: *{dt}*\n"
        f"💰 Сумма: *{amount} ₽*\n"
        f"🔑 Код: `{code}`\n\n"
        f"Booking ID: {booking.id}"
    )

    # 3) Раздаём админам
    for admin_id in ADMINS:
        await bot.send_message(
            chat_id=admin_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить",
                        callback_data=f"admin_confirm_{booking_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data="my_bookings"
                    )
                ]
            ])
        )

    # 4) Сообщаем пользователю, что заявка ушла
    await callback.message.edit_text(
        "Заявка на оплату отправлена. Ожидайте подтверждения.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ На главную",   callback_data="go_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery):
    
    user_tg_id = callback.from_user.id
    slot_id = int(callback.data.split("_")[1])

    result, message = await rq.book_slot(user_tg_id, slot_id)
    
    if result == BookingResult.SUCCESS:
        await callback.message.edit_text(message)
    else: 
        await callback.message.edit_text(message, reply_markup=go_back_markup())
    
    await callback.answer()
    
    
@router.callback_query(F.data.startswith("slot_"))
async def confirm_slot(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[1])

    WEEKDAYS_RU = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье',
}
    
    async with async_session() as session:
        slot = await session.get(Slot, slot_id)

    if not slot:
        await callback.answer("Слот не найден", show_alert=True)
        return

    day_ru = WEEKDAYS_RU[slot.date.strftime("%A")]
    time_text = f"{day_ru} {slot.date.strftime('%d.%m %H:%M')}"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{slot_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_booking")
        ]
    ])

    await callback.message.edit_text(
        f"Вы уверены, что хотите записаться на {time_text}?",
        reply_markup=markup
    )
    await callback.answer()


@router.callback_query(F.data == 'my_bookings')
async def my_bookings(callback: CallbackQuery):
    user_id = callback.from_user.id
    bookings = await rq.get_user_bookings(user_id)
    
    if not bookings:
        await callback.message.edit_text("У вас нет активных бронирований.")
        await callback.answer()
        return
    
    WEEKDAYS_RU = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье',
    }

    text = "Ваши бронирования:\n"
    for i,b in enumerate(bookings, 1):
        day = WEEKDAYS_RU[b.slot.date.strftime("%A")]
        dt = b.slot.date.strftime("%d.%m %H.%M")
        status = "Оплачено" if b.is_paid else "Не оплачено"
        text += f"{i}. {day} {dt} - {status}\n"
        
    await callback.message.edit_text(text, reply_markup=kb.my_bookings_keyboard(bookings))
    await callback.answer()
    
    
@router.callback_query(F.data.startswith("cancel_"))
async def cancel_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    success = await rq.delete_booking(booking_id, user_id)
    
    if success:
        await callback.answer("Бронирование отменено.")
    else:
        await callback.answer("Нельзя отменить эту бронь. ", show_alert=True)
        
    await my_bookings(callback)
    
    
@router.callback_query(F.data.startswith("pay_"))
async def handle_payment(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    success, code, booking = await rq.prepare_payment(booking_id, user_id)
    
    if not success:
        await callback.answer(code, show_alert=True)
        return
    
    cost = booking.slot.price_per_person
    dt = booking.slot.date.strftime("%d.%m %H:%M")
    
    #смс клиенту
    await callback.message.edit_text(
        f"💳 Оплата за слот {dt}\n"
        f"Сумма: {cost} ₽\n\n"
        f"👉 Реквизиты: `1234 5678 9012 3456`\n"
        f"‼️ В назначении укажите: `{code}`\n\n"
        f"После перевода нажмите кнопку ниже.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"confirm_payment_{booking_id}")],
            [InlineKeyboardButton(text="◀ Назад",   callback_data="my_bookings")]
        ])
    )
    await callback.answer()
        
        
@router.callback_query(F.data == 'go_back')
async def go_back(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню", reply_markup=kb.main)
    await callback.answer()

