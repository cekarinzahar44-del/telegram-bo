import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# Настройка логирования
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN! Добавьте его в переменные окружения.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Данные магазина ---
products = {
    "gaming_pc": {"title": "Игровой ПК \"Gamer Pro\"", "description": "Топовый компьютер.", "price": 1500000},
    "laptop": {"title": "Ноутбук \"WorkMaster X\"", "description": "Мощный и легкий ноутбук.", "price": 800000},
}

def get_main_keyboard():
    """Главное меню с кнопками"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💻 Задать вопрос"))
    kb.add(KeyboardButton("🛍️ Каталог"), KeyboardButton("📞 Связаться"))
    return kb

@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}! Я — бот магазина.",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda msg: msg.text == "💻 Задать вопрос")
async def ask_question(message: Message):
    await message.answer("Напиши свой вопрос (например, про ноутбук или ПК).")
    dp.current_state(user=message.from_user.id).set_state("waiting_question")

@dp.message_handler(state="waiting_question")
async def handle_question(message: Message):
    text = message.text.lower()
    await message.answer("🤔 Думаю...")
    await asyncio.sleep(1)

    if "ноутбук" in text:
        reply = f"Рекомендую **{products['laptop']['title']}**. Он отлично подходит."
    elif "пк" in text or "компьютер" in text:
        reply = f"Рекомендую **{products['gaming_pc']['title']}**. Идеален для игр."
    else:
        reply = "Посмотрите каталог или свяжитесь с менеджером."

    # Кнопка для возврата в каталог
    ikb = InlineKeyboardMarkup().add(InlineKeyboardButton("🛒 Каталог", callback_data="catalog"))
    await message.answer(reply, reply_markup=ikb)
    await dp.current_state(user=message.from_user.id).reset_state()

@dp.message_handler(lambda msg: msg.text == "🛍️ Каталог")
async def show_catalog(message: Message):
    ikb = InlineKeyboardMarkup(row_width=1)
    for prod_id, prod_info in products.items():
        ikb.add(InlineKeyboardButton(prod_info['title'], callback_data=f"prod_{prod_id}"))
    await message.answer("Наши товары:", reply_markup=ikb)

@dp.callback_query_handler(lambda c: c.data.startswith("prod_"))
async def show_product(callback: CallbackQuery):
    prod_id = callback.data.split("_")[1]
    product = products[prod_id]
    text = f"*{product['title']}*\n{product['description']}\nЦена: {product['price']//100} ₽"
    ikb = InlineKeyboardMarkup().add(InlineKeyboardButton("◀ Назад", callback_data="catalog"))
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=ikb)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def back_to_catalog(callback: CallbackQuery):
    await callback.message.delete()
    await show_catalog(callback.message)

@dp.message_handler(lambda msg: msg.text == "📞 Связаться")
async def contact(message: Message):
    await message.answer("Скоро свяжемся! А пока посмотрите каталог.")

@dp.message_handler()
async def other(message: Message):
    await message.answer("Воспользуйтесь кнопками меню.", reply_markup=get_main_keyboard())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
