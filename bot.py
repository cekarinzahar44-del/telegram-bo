import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN! Добавьте его в переменные окружения.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Определяем состояния
class QuestionState(StatesGroup):
    waiting = State()

# --- Данные магазина ---
products = {
    "gaming_pc": {"title": "Игровой ПК \"Gamer Pro\"", "description": "Топовый компьютер для игр и работы.", "price": 1500000},
    "laptop": {"title": "Ноутбук \"WorkMaster X\"", "description": "Мощный и легкий ноутбук для любых задач.", "price": 800000},
}

# --- Клавиатуры ---
def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💻 Задать вопрос"))
    kb.add(KeyboardButton("🛍️ Каталог"), KeyboardButton("📞 Связаться"))
    return kb

def get_back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 В главное меню"))
    return kb

# --- Обработчики ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}! Я — бот магазина электроники.\n"
        f"Выбери действие в меню:",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda msg: msg.text == "🏠 В главное меню")
async def back_to_main(message: Message):
    await cmd_start(message)

@dp.message_handler(lambda msg: msg.text == "💻 Задать вопрос")
async def ask_question(message: Message):
    await message.answer(
        "Напиши свой вопрос (например, про ноутбук или ПК).\n"
        "Или нажми кнопку ниже, чтобы вернуться.",
        reply_markup=get_back_keyboard()
    )
    # Правильный асинхронный вызов
    await QuestionState.waiting.set()

@dp.message_handler(state=QuestionState.waiting)
async def handle_question(message: Message):
    text = message.text.lower()
    await message.answer("🤔 Думаю...")
    await asyncio.sleep(1)

    if "ноутбук" in text:
        reply = f"✅ Рекомендую **{products['laptop']['title']}**. Он отлично подходит для работы и учебы."
    elif "пк" in text or "компьютер" in text or "игр" in text:
        reply = f"✅ Рекомендую **{products['gaming_pc']['title']}**. Идеален для игр и тяжёлых задач."
    else:
        reply = "❓ Я не совсем понял вопрос. Посмотрите каталог или свяжитесь с менеджером."

    ikb = InlineKeyboardMarkup().add(InlineKeyboardButton("🛒 Перейти в каталог", callback_data="catalog"))
    await message.answer(reply, reply_markup=ikb)
    await QuestionState.waiting.reset_state()

@dp.message_handler(lambda msg: msg.text == "🛍️ Каталог")
async def show_catalog(message: Message):
    ikb = InlineKeyboardMarkup(row_width=1)
    for prod_id, prod_info in products.items():
        ikb.add(InlineKeyboardButton(prod_info['title'], callback_data=f"prod_{prod_id}"))
    await message.answer(
        "📋 Наши товары:\nВыберите интересующий:",
        reply_markup=ikb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("prod_"))
async def show_product(callback: CallbackQuery):
    prod_id = callback.data.split("_")[1]
    product = products[prod_id]
    text = f"*{product['title']}*\n\n{product['description']}\n\n💰 Цена: *{product['price'] // 100} ₽*"
    ikb = InlineKeyboardMarkup(row_width=2)
    ikb.add(
        InlineKeyboardButton("◀ Назад в каталог", callback_data="catalog"),
        InlineKeyboardButton("📞 Связаться", callback_data="contact")
    )
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=ikb)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def back_to_catalog(callback: CallbackQuery):
    await callback.message.delete()
    await show_catalog(callback.message)

@dp.message_handler(lambda msg: msg.text == "📞 Связаться")
async def contact(message: Message):
    await message.answer(
        "📱 Свяжитесь с нами:\n"
        "Телефон: +7 (999) 123-45-67\n"
        "Email: shop@example.com\n\n"
        "Или нажмите кнопку ниже, чтобы вернуться в меню.",
        reply_markup=get_back_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "contact")
async def contact_callback(callback: CallbackQuery):
    await callback.message.answer(
        "📱 Контакты:\n+7 (999) 123-45-67\nshop@example.com",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()

@dp.message_handler()
async def other(message: Message):
    await message.answer(
        "⚠️ Я не понимаю эту команду.\nВоспользуйтесь кнопками меню.",
        reply_markup=get_main_keyboard()
    )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
