import logging
import sqlite3
import asyncio
import random
from aiogram import Bot, Dispatcher, executor, types

# 🔑 Вставь сюда токен от BotFather
API_TOKEN = "YOUR_TOKEN_HERE"

# 🔧 Логирование
logging.basicConfig(level=logging.INFO)

# 📂 База данных
conn = sqlite3.connect("gamebot.db")
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 1000000,
    factories TEXT DEFAULT '',
    hidden INTEGER DEFAULT 0,
    ref_id INTEGER DEFAULT NULL
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS promo (
    code TEXT PRIMARY KEY,
    amount INTEGER,
    activations INTEGER
)""")
conn.commit()

# 🤖 Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 👑 Админ ID
ADMIN_ID = 7167501974  # замени на свой айди

# 📌 Хелперы
def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()
    
    # 📌 Регистрация
@dp.message_handler(commands=["ss"])
async def register(message: types.Message):
    if not get_user(message.from_user.id):
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (message.from_user.id,))
        conn.commit()
        await message.answer("✅ Вы зарегистрированы!\n💰 Ваш баланс: 1,000,000")
    else:
        await message.answer("Вы уже зарегистрированы!")

# 📌 Профиль
@dp.message_handler(commands=["meb", "я"])
async def profile(message: types.Message):
    user = get_user(message.from_user.id)
    if user:
        await message.answer(
            f"👤 Ваш профиль\n\n💰 Баланс: {user[1]:,}\n🏭 Заводы: {user[2] or 'нет'}"
        )
    else:
        await message.answer("Сначала зарегистрируйтесь: /ss")

# 📌 Бонус
@dp.message_handler(commands=["бонус", "bonus"])
async def bonus(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала зарегистрируйтесь: /ss")
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (100000, message.from_user.id))
    conn.commit()
    await message.answer("🎁 Вы получили бонус: 100,000")

# 📌 Промокоды
@dp.message_handler(commands=["new_promo"])
async def new_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, code, amount, act = message.text.split()
        cur.execute("INSERT INTO promo VALUES (?, ?, ?)", (code, int(amount), int(act)))
        conn.commit()
        await message.answer(f"✅ Промокод {code} создан на {amount}₽ ({act} активаций)")
    except:
        await message.answer("Формат: /new_promo название сумма активации")

@dp.message_handler(commands=["pr"])
async def activate_promo(message: types.Message):
    try:
        _, code = message.text.split()
    except:
        return await message.answer("Использование: /pr код")
    cur.execute("SELECT * FROM promo WHERE code = ?", (code,))
    promo = cur.fetchone()
    if not promo:
        return await message.answer("❌ Промокод не найден")
    if promo[2] <= 0:
        return await message.answer("❌ Промокод закончился")
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (promo[1], message.from_user.id))
    cur.execute("UPDATE promo SET activations = activations - 1 WHERE code = ?", (code,))
    conn.commit()
    await message.answer(f"✅ Промокод активирован! Получено {promo[1]}")

# 📌 Перевод
@dp.message_handler(commands=["перевести"])
async def transfer(message: types.Message):
    try:
        _, amount, uid = message.text.split()
        amount, uid = int(amount), int(uid)
    except:
        return await message.answer("Формат: /перевести сумма айди")
    user = get_user(message.from_user.id)
    if user[1] < amount:
        return await message.answer("Недостаточно средств")
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, message.from_user.id))
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    await message.answer(f"✅ Перевод {amount} игроку {uid} выполнен")
    
    # 📌 Заводы
factories_list = {
    "small": 1_000_000,
    "medium": 10_000_000,
    "big": 100_000_000
}

@dp.message_handler(commands=["buy_factory"])
async def buy_factory(message: types.Message):
    try:
        _, name = message.text.split()
    except:
        return await message.answer("Использование: /buy_factory small|medium|big")
    if name not in factories_list:
        return await message.answer("Такого завода нет")
    price = factories_list[name]
    user = get_user(message.from_user.id)
    if user[1] < price:
        return await message.answer("Недостаточно денег для покупки")
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, message.from_user.id))
    new_factories = (user[2] + "," + name) if user[2] else name
    cur.execute("UPDATE users SET factories = ? WHERE user_id = ?", (new_factories, message.from_user.id))
    conn.commit()
    await message.answer(f"🏭 Завод {name} куплен за {price:,}")

# 📌 Начисление прибыли от заводов (2%/час)
async def factory_income():
    while True:
        await asyncio.sleep(3600)
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        for u in users:
            if not u[2]:
                continue
            factories = u[2].split(",")
            income = 0
            for f in factories:
                if f in factories_list:
                    income += int(factories_list[f] * 0.02)
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (income, u[0]))
        conn.commit()

# 📌 Админ: выдать/забрать деньги
@dp.message_handler(commands=["admin_money"])
async def admin_money(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, uid, amount = message.text.split()
        uid, amount = int(uid), int(amount)
    except:
        return await message.answer("Использование: /admin_money user_id сумма(+/-)")
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    await message.answer(f"✅ Баланс пользователя {uid} изменён на {amount}")

# 📌 Топ игроков
@dp.message_handler(commands=["топ", "top"])
async def top_players(message: types.Message):
    cur.execute("SELECT user_id, balance FROM users WHERE hidden=0 ORDER BY balance DESC LIMIT 10")
    top = cur.fetchall()
    text = "🏆 ТОП игроков:\n\n"
    for idx, (user_id, balance) in enumerate(top, start=1):
        text += f"{idx}. Пользователь {user_id} — {balance:,}₽\n"
    await message.answer(text)
    
    # 📌 Рулетка
@dp.message_handler(commands=["рул"])
async def roulette(message: types.Message):
    try:
        _, bet, choice = message.text.split()
        bet = int(bet)
    except:
        return await message.answer("Использование: /рул ставка чет|нечет|красное|черное|число")
    user = get_user(message.from_user.id)
    if user[1] < bet:
        return await message.answer("Недостаточно средств для ставки")

    number = random.randint(0, 36)
    color = "красное" if number % 2 == 0 else "черное"
    parity = "чет" if number % 2 == 0 else "нечет"
    win = False
    coef = 2

    if choice.isdigit() and int(choice) == number:
        win, coef = True, 35
    elif choice in [color, parity]:
        win = True

    if win:
        prize = bet * coef
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (prize, message.from_user.id))
        conn.commit()
        await message.answer(f"🎰 Выпало: {number} ({color}, {parity})\n✅ Победа! Выигрыш: {prize:,}\n💰 Баланс: {user[1] + prize - bet:,}")
    else:
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        conn.commit()
        await message.answer(f"🎰 Выпало: {number} ({color}, {parity})\n❌ Проигрыш: {bet:,}\n💰 Баланс: {user[1] - bet:,}")

# 📌 Мини-игра
@dp.message_handler(commands=["мини"])
async def mini(message: types.Message):
    try:
        _, bet = message.text.split()
        bet = int(bet)
    except:
        return await message.answer("Использование: /мини ставка")
    user = get_user(message.from_user.id)
    if user[1] < bet:
        return await message.answer("Недостаточно средств")
    if random.random() > 0.5:
        prize = bet * 2
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (prize, message.from_user.id))
        conn.commit()
        await message.answer(f"🎲 Победа! Выигрыш: {prize:,}\n💰 Баланс: {user[1] + prize - bet:,}")
    else:
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        conn.commit()
        await message.answer(f"🎲 Проигрыш: {bet:,}\n💰 Баланс: {user[1] - bet:,}")

# 📌 Башня
@dp.message_handler(commands=["башня"])
async def tower(message: types.Message):
    try:
        _, bet, floors = message.text.split()
        bet, floors = int(bet), int(floors)
    except:
        return await message.answer("Использование: /башня ставка этажи")
    user = get_user(message.from_user.id)
    if user[1] < bet:
        return await message.answer("Недостаточно средств")
    coef = 1 + (floors * 0.2)
    if random.random() > 0.5:
        prize = int(bet * coef)
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (prize, message.from_user.id))
        conn.commit()
        await message.answer(f"🏰 Победа! Этажей: {floors}, Выигрыш: {prize:,}\n💰 Баланс: {user[1] + prize - bet:,}")
    else:
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        conn.commit()
        await message.answer(f"🏰 Башня рухнула!\n❌ Проигрыш: {bet:,}\n💰 Баланс: {user[1] - bet:,}")

# 📌 Краш
@dp.message_handler(commands=["краш"])
async def crash(message: types.Message):
    try:
        _, bet, coef = message.text.split()
        bet, coef = int(bet), float(coef)
    except:
        return await message.answer("Использование: /краш ставка коэф")
    user = get_user(message.from_user.id)
    if user[1] < bet:
        return await message.answer("Недостаточно средств")
    crash_coef = round(random.uniform(1, 5), 2)
    if crash_coef >= coef:
        prize = int(bet * coef)
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (prize, message.from_user.id))
        conn.commit()
        await message.answer(f"💥 Краш достиг {crash_coef}x\n✅ Победа! Выигрыш: {prize:,}\n💰 Баланс: {user[1] + prize - bet:,}")
    else:
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id))
        conn.commit()
        await message.answer(f"💥 Краш остановился на {crash_coef}x\n❌ Проигрыш: {bet:,}\n💰 Баланс: {user[1] - bet:,}")
        
        # 📌 Стартер
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(factory_income())
    executor.start_polling(dp, skip_updates=True)
    
    
    
