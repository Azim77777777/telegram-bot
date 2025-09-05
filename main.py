from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import random, json, time, os

TOKEN = "ВАШ_ТОКЕН_БОТА"
ADMIN_ID = 123456789  # замените на свой Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Загрузка пользователей
if os.path.exists("users.json"):
    with open("users.json", "r") as f:
        users = json.load(f)
else:
    users = {}

# Загрузка промокодов
if os.path.exists("promos.json"):
    with open("promos.json", "r") as f:
        promos = json.load(f)
else:
    promos = {}

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f)

def save_promos():
    with open("promos.json", "w") as f:
        json.dump(promos, f)

# ======== Start ========
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in users:
        users[user_id] = {"balance": 1000, "last_hour": 0}
        save_users()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Сапёр", "Краш", "Башня", "Рулетка", "Промо", "Баланс", "Часовой бонус"]
    keyboard.add(*buttons)
    await message.reply("Привет! Выбери игру или команду:", reply_markup=keyboard)

# ======== Баланс ========
@dp.message_handler(lambda message: message.text.lower() == "баланс")
async def balance(message: types.Message):
    user_id = str(message.from_user.id)
    bal = users.get(user_id, {"balance":0})["balance"]
    await message.reply(f"💰 Ваш баланс: {bal} mCoin")

# ======== Часовой бонус ========
@dp.message_handler(lambda message: message.text.lower() == "часовой бонус")
async def hour_bonus(message: types.Message):
    user_id = str(message.from_user.id)
    now = time.time()
    last = users[user_id].get("last_hour", 0)
    if now - last >= 3600:
        bonus = random.randint(100, 200)
        users[user_id]["balance"] += bonus
        users[user_id]["last_hour"] = now
        save_users()
        await message.reply(f"⏰ Вы получили {bonus} mCoin в качестве часового бонуса!")
    else:
        await message.reply("⏳ Бонус можно брать раз в час!")

# ======== Промокод ========
@dp.message_handler(lambda message: message.text.lower() == "промо")
async def promo(message: types.Message):
    await message.reply("Введите ваш промокод:")
    @dp.message_handler()
    async def apply_promo(msg: types.Message):
        code = msg.text.strip().upper()
        user_id = str(msg.from_user.id)
        if code in promos:
            users[user_id]["balance"] += promos[code]
            save_users()
            await msg.reply(f"🎉 Промокод применён! Получено {promos[code]} mCoin.")
            del promos[code]
            save_promos()
        else:
            await msg.reply("❌ Промокод не найден или уже использован.")

# ======== Сапёр (Мини) ========
@dp.message_handler(lambda message: message.text.lower() == "сапёр")
async def saper(message: types.Message):
    user_id = str(message.from_user.id)
    bet = 100
    if users[user_id]["balance"] < bet:
        await message.reply("❌ Недостаточно средств!")
        return
    users[user_id]["balance"] -= bet
    total_cells = 5
    mines_count = 2
    mine_positions = random.sample(range(1, total_cells+1), mines_count)
    safe_cell = random.choice([i for i in range(1, total_cells+1) if i not in mine_positions])
    users[user_id]["balance"] += bet*2  # простой пример
    save_users()
    await message.reply(f"✅ Вы открыли безопасную клетку! Вы выиграли {bet*2} mCoin.")

# ======== Краш ========
@dp.message_handler(lambda message: message.text.lower() == "краш")
async def crash(message: types.Message):
    user_id = str(message.from_user.id)
    bet = 100
    if users[user_id]["balance"] < bet:
        await message.reply("❌ Недостаточно средств!")
        return
    users[user_id]["balance"] -= bet
    multiplier = round(random.uniform(1.1, 5.0), 2)
    win = int(bet * multiplier)
    users[user_id]["balance"] += win
    save_users()
    await message.reply(f"📈 Краш завершен! Множитель: {multiplier}x\nВы выиграли {win} mCoin!")

# ======== Рулетка ========
@dp.message_handler(lambda message: message.text.lower() == "рулетка")
async def roulette(message: types.Message):
    user_id = str(message.from_user.id)
    bet = 100
    if users[user_id]["balance"] < bet:
        await message.reply("❌ Недостаточно средств!")
        return
    users[user_id]["balance"] -= bet
    color = random.choice(["Красный", "Чёрный"])
    users[user_id]["balance"] += bet*2
    save_users()
    await message.reply(f"🎰 Выпало {color}! Вы выиграли {bet*2} mCoin!")

# ======== Башня ========
@dp.message_handler(lambda message: message.text.lower() == "башня")
async def tower(message: types.Message):
    user_id = str(message.from_user.id)
    bet = 100
    if users[user_id]["balance"] < bet:
        await message.reply("❌ Недостаточно средств!")
        return
    users[user_id]["balance"] -= bet
    levels = random.randint(1,5)
    win = bet * levels
    users[user_id]["balance"] += win
    save_users()
    await message.reply(f"🏰 Вы поднялись на {levels} уровней башни!\nВы выиграли {win} mCoin!")

# ======== Админ: выдача денег ========
@dp.message_handler(commands=["give"])
async def give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        user_id = args[1]
        amount = int(args[2])
        if user_id in users:
            users[user_id]["balance"] += amount
            save_users()
            await message.reply(f"✅ Выдано {amount} mCoin пользователю {user_id}")
        else:
            await message.reply("❌ Пользователь не найден")
    except:
        await message.reply("Использование: /give USER_ID AMOUNT")

# ======== Админ: создание промокодов ========
@dp.message_handler(commands=["createpromo"])
async def createpromo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        code = args[1].upper()
        amount = int(args[2])
        promos[code] = amount
        save_promos()
        await message.reply(f"✅ Промокод {code} создан на {amount} mCoin")
    except:
        await message.reply("Использование: /createpromo CODE AMOUNT")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
