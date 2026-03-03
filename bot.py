import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN! Добавьте его в переменные окружения.")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Данные магазина ---
products = {
    "gaming_pc": {"title": "Игровой ПК \"Gamer Pro\"", "description": "Топовый компьютер для игр и работы.", "price": 1500000},
    "laptop": {"title": "Ноутбук \"WorkMaster X\"", "description": "Мощный и легкий ноутбук для любых задач.", "price": 800000},
}

# --- Клавиатуры ---
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="💻 Задать вопрос ИИ-консультанту")],
        [KeyboardButton(text="🛍️ Каталог товаров")],
        [KeyboardButton(text="📞 Связаться с человеком")]
    ])
    return keyboard

# --- Состояния для ИИ-консультанта ---
class AIState(StatesGroup):
    waiting_for_question = State()

# --- Команда /start ---
@dp.message(commands=['start'])
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}! Я — умный бот магазина электроники.\n"
        f"Выбери действие в меню ниже:",
        reply_markup=get_main_keyboard()
    )

# --- Блок ИИ-консультанта (симуляция) ---
@dp.message(lambda message: message.text == "💻 Задать вопрос ИИ-консультанту")
async def ai_consultant_start(message: Message, state: FSMContext):
    await message.answer(
        "Отлично! Задай мне свой вопрос. Например:\n"
        "• Какой ноутбук подойдет для видеомонтажа?\n"
        "• Что лучше для игр: RTX 4060 или RTX 4070?"
    )
    await state.set_state(AIState.waiting_for_question)

@dp.message(AIState.waiting_for_question)
async def ai_consultant_answer(message: Message, state: FSMContext):
    user_question = message.text
    await message.answer("🤖 ИИ-консультант думает над твоим вопросом...")
    await asyncio.sleep(2)

    if "ноутбук" in user_question.lower() or "видеомонтаж" in user_question.lower():
        answer = f"Рекомендую **{products['laptop']['title']}**. Он отлично справляется с ресурсоемкими задачами."
    elif "игр" in user_question.lower() or "пк" in user_question.lower():
        answer = f"Рекомендую **{products['gaming_pc']['title']}**. Максимальная производительность в играх."
    else:
        answer = "Чтобы дать точный ответ, нужно больше информации. Посмотрите каталог или свяжитесь с менеджером."

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛒 Каталог", callback_data="catalog"))
    builder.row(InlineKeyboardButton(text="✅ Ещё вопрос", callback_data="ask_ai_again"))
    await message.answer(answer, reply_markup=builder.as_markup())
    await state.clear()

@dp.callback_query(lambda c: c.data == "ask_ai_again")
async def ask_ai_again(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await ai_consultant_start(callback.message, state)

# --- Блок каталога ---
@dp.message(lambda message: message.text == "🛍️ Каталог товаров")
async def show_catalog(message: Message):
    builder = InlineKeyboardBuilder()
    for prod_id, prod_info in products.items():
        builder.row(InlineKeyboardButton(text=prod_info['title'], callback_data=f"product_{prod_id}"))
    await message.answer("Наши товары:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = callback.data.split("_")[1]
    product = products[product_id]
    text = f"*{product['title']}*\n\n{product['description']}\n\nЦена: *{product['price'] // 100} ₽*"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад к каталогу", callback_data="catalog"))
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "catalog")
async def back_to_catalog(callback: CallbackQuery):
    await callback.message.delete()
    await show_catalog(callback.message)

# --- Блок связи с человеком ---
@dp.message(lambda message: message.text == "📞 Связаться с человеком")
async def contact_human(message: Message):
    await message.answer("Скоро с вами свяжется наш специалист.")

# --- Обработка всего остального ---
@dp.message()
async def other_messages(message: Message):
    await message.answer("Пожалуйста, воспользуйтесь кнопками меню.")

# --- Запуск бота ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())