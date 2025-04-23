from app.common.models import async_session
from app.common.models import User, Slot, Booking, Payment
from sqlalchemy import select
from sqlalchemy.orm import selectinload


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


async def book_slot(tg_id: int, slot_id: int) -> tuple[bool, str]:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            return False, "Ошибка: пользователь не найден"

        slot = await session.get(Slot, slot_id)
        if not slot:
            return False, "Ошибка: слот не найден"

        # Проверка: не записан ли уже
        existing = await session.scalar(
            select(Booking).where(
                Booking.user_id == user.id,
                Booking.slot_id == slot.id
            )
        )
        if existing:
            return False, "Вы уже записаны на этот слот"

        # Добавляем бронирование
        booking = Booking(user_id=user.id, slot_id=slot.id)
        session.add(booking)
        await session.commit()

        return True, "Вы успешно записаны на занятие ✅"
    

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