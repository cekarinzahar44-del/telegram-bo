import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

class QuestionState(StatesGroup):
    waiting = State()

products = {
    "gaming_pc": {"title": "Игровой ПК \"Gamer Pro\"", "description": "Топовый компьютер для игр.", "price": 1500000},
    "laptop": {"title": "Ноутбук \"WorkMaster X\"", "description": "Мощный и легкий.", "price": 800000},
}

def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💻 Задать вопрос"))
    kb.add(KeyboardButton("🛍️ Каталог"), KeyboardButton("📞 Связаться"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 В главное меню"))
    return kb

@dp.message_handler(commands=['start'])
async def start(message: Message):
    await message.answer(f"👋 Привет, {message.from_user.first_name}!", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "🏠 В главное меню")
async def back(message: Message):
    await start(message)

@dp.message_handler(lambda msg: msg.text == "💻 Задать вопрос")
async def ask(message: Message):
    await message.answer("Напиши вопрос:", reply_markup=back_keyboard())
    await QuestionState.waiting.set()  # ← правильно!

@dp.message_handler(state=QuestionState.waiting)
async def answer_question(message: Message):
    text = message.text.lower()
    await message.answer("🤔 Думаю...")
    await asyncio.sleep(1)
    if "ноутбук" in text:
        reply = f"✅ {products['laptop']['title']}"
    elif "пк" in text or "игр" in text:
        reply = f"✅ {products['gaming_pc']['title']}"
    else:
        reply = "❓ Не понял, посмотрите каталог."
    ikb = InlineKeyboardMarkup().add(InlineKeyboardButton("🛒 Каталог", callback_data="catalog"))
    await message.answer(reply, reply_markup=ikb)
    await QuestionState.waiting.reset_state()

@dp.message_handler(lambda msg: msg.text == "🛍️ Каталог")
async def catalog(message: Message):
    ikb = InlineKeyboardMarkup(row_width=1)
    for pid, prod in products.items():
        ikb.add(InlineKeyboardButton(prod['title'], callback_data=f"prod_{pid}"))
    await message.answer("📋 Наши товары:", reply_markup=ikb)

@dp.callback_query_handler(lambda c: c.data.startswith("prod_"))
async def show(callback: CallbackQuery):
    pid = callback.data.split("_")[1]
    prod = products[pid]
    text = f"*{prod['title']}*\n{prod['description']}\n💰 {prod['price']//100} ₽"
    ikb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("◀ Назад", callback_data="catalog"),
        InlineKeyboardButton("📞 Связаться", callback_data="contact")
    )
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=ikb)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def back_catalog(callback: CallbackQuery):
    await callback.message.delete()
    await catalog(callback.message)

@dp.message_handler(lambda msg: msg.text == "📞 Связаться")
async def contact(message: Message):
    await message.answer("📱 +7 (999) 123-45-67\nshop@example.com", reply_markup=back_keyboard())

@dp.callback_query_handler(lambda c: c.data == "contact")
async def contact_cb(callback: CallbackQuery):
    await callback.message.answer("📱 +7 (999) 123-45-67\nshop@example.com", reply_markup=back_keyboard())
    await callback.answer()

@dp.message_handler()
async def other(message: Message):
    await message.answer("Используйте кнопки.", reply_markup=main_keyboard())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
