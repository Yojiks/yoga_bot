from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from collections import defaultdict
from app.common.models import Slot
import calendar

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Свободные слоты', callback_data='free_slots')],
    [InlineKeyboardButton(text='Мои брони', callback_data='my_bookings'), 
     InlineKeyboardButton(text='Контакты', callback_data='contacts')]
])

# Словарь для перевода дней недели на русский
WEEKDAYS_RU = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье',
}


def chunked(lst, n):
    """Разделить список на подсписки по n элементов"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
        

async def inline_slots(slots: list[Slot]) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    grouped = defaultdict(list)

    for slot in slots:
        weekday_en = calendar.day_name[slot.date.weekday()]
        grouped[weekday_en].append(slot)

    # Порядок дней недели
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day_en in weekday_order:
        if day_en not in grouped:
            continue

        # Заголовок дня недели
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📅 {WEEKDAYS_RU[day_en]}",
                callback_data="none"
            )
        ])

        # Кнопки слотов по 2 в ряд
        day_slots = grouped[day_en]
        row_buttons = [
            InlineKeyboardButton(
                text=slot.date.strftime("%H:%M"),
                callback_data=f"slot_{slot.id}"
            )
            for slot in day_slots
        ]

        for row in chunked(row_buttons, 2):
            markup.inline_keyboard.append(row)

    # Кнопка «Назад»
    markup.inline_keyboard.append([
        InlineKeyboardButton(text="◀ Назад", callback_data="go_back")
    ])

    return markup


def my_bookings_keyboard(bookings: list) -> InlineKeyboardMarkup:
    keyboard = []
    
    
    for booking in bookings:
        dt_str = booking.slot.date.strftime('%d.%m %H:%M')
        
        if not booking.is_paid:
            buttons_row = [
                InlineKeyboardButton(
                    text=f"✅ Оплатить {dt_str}",
                    callback_data=f"pay_{booking.id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ Отменить {dt_str}",
                    callback_data=f"cancel_{booking.id}"
                )
            ]
            keyboard.append(buttons_row)
        
    keyboard.append([
        InlineKeyboardButton(text="◀ Назад", callback_data="go_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def go_back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ На главную", callback_data="go_back")]
    ])
    