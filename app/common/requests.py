from app.common.models import async_session
from app.common.models import User, Slot, Booking, Payment
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import uuid4
from datetime import datetime
from enum import Enum

import random



class BookingResult(Enum):
    SUCCESS = "success"
    ALREADY_BOOKED = "already_booked"
    SLOT_NOT_FOUND = "slot_not_found"
    USER_NOT_FOUND = "user_not_found"



async def set_user(tg_id: int, email: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        
        if not user:
            session.add(User(tg_id=tg_id, email=email))
            await session.commit()


async def get_user_by_tg_id(tg_id: int) -> User | None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user


async def book_slot(tg_id: int, slot_id: int) -> tuple[BookingResult, str]:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            return BookingResult.USER_NOT_FOUND, "Ошибка: пользователь не найден"

        slot = await session.get(Slot, slot_id)
        if not slot:
            return BookingResult.SLOT_NOT_FOUND, "Ошибка: слот не найден"

        # Проверка: не записан ли уже
        existing = await session.scalar(
            select(Booking).where(
                Booking.user_id == user.id,
                Booking.slot_id == slot.id
            )
        )
        if existing:
            return BookingResult.ALREADY_BOOKED, "Вы уже записаны на этот слот"

        # Считаем количество бронирований
        result = await session.execute(
            select(func.count()).select_from(Booking).where(Booking.slot_id == slot_id)
        )
        count = result.scalar_one()

        date_str = slot.date.strftime('%d.%m %H:%M')
        new_price = 1000 // (count + 1)
        slot.price_per_person = new_price

        booking = Booking(
            user_id=user.id,
            slot_id=slot.id,
            is_paid=False,
            confirmation_code=str(uuid4())[:8]
        )
        session.add(booking)
        await session.commit()

        return BookingResult.SUCCESS, f"Вы успешно записаны на занятие ✅\nДата: {date_str}"
    
    
async def get_user_bookings(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            return []

        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.slot))
            .join(Slot)
            .where(Booking.user_id == user.id)
            .order_by(Slot.date)
        )
        bookings = result.scalars().all()
        return bookings
    

async def delete_booking(booking_id: int, tg_id: int) -> bool:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id==tg_id))
        if not user:
            return False
        
        booking = await session.get(Booking, booking_id)
        if not booking or booking.user_id != user.id:
            return False
        
        if booking.is_paid:
            return False
        
        await session.delete(booking)
        await session.commit()
        return True
    

async def delete_past_bookings():
    async with async_session() as session:
        result = await session.execute(
            select(Booking).join(Slot).where(Slot.date < datetime.now())
        )
        old_bookings = result.scalars().all()
        
        for b in old_bookings:
            await session.delete(b)
            
        await session.commit()
        

def generate_payment_code() -> str:
    return f"YOGA-{random.randint(1000, 9999)}"


async def prepare_payment(booking_id: int, tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        result = await session.execute(
            select(Booking).options(selectinload(Booking.slot))
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()

        if not user or not booking or booking.user_id != user.id or booking.is_paid:
            return False, "Ошибка", None

        # Генерируем код оплаты только если его нет
        if not booking.confirmation_code:
            booking.confirmation_code = generate_payment_code()
            await session.commit()

        return True, booking.confirmation_code, booking
    

async def mark_payment_confirmed(booking_id: int):
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        if booking:
            booking.is_paid = True
            await session.commit()
        
        
