import asyncio, logging, sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiohttp import web

logging.basicConfig(level=logging.INFO)
TOKEN = "8465639110:AAHd3dBLIeEn0em3GWKM7ZgWrJRnYJeyDK0"

IMG_MAIN = "AgACAgIAAxkBAANKasUV1ZZt2Ay2qH97X_WWkI-JwxUAAqAhaxsUbihK-YQMOfZdxcQBAAMCAAN5AAM9BA" 
ADMIN_ID = 6799133468

bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_CARTS = {}

def init_db():
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, orders_count INTEGER DEFAULT 0, coupons_balance INTEGER DEFAULT 4
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_or_create_user(user_id, username):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT orders_count, coupons_balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, username, orders_count, coupons_balance) VALUES (?, ?, 0, ?)", (user_id, username, 4))
        conn.commit()
        user = (0, 4)
    conn.close()
    return {"orders": user, "coupons": user}

def increment_user_orders(user_id):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET orders_count = orders_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
PRODUCTS = {
    "vostok": {
        "xros6": [
            {"id": "v_xros6_orange", "name": "Jelly Orange", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "v_xros6_blue", "name": "Jelly blue", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "v_xros6_pink", "name": "Jelly pink", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "v_xros6_pblue", "name": "Plume blue", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "v_xros6_ppink", "name": "Plume pink", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "v_xros6_pwhite", "name": "Plume white", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "v_xros6_black", "name": "Titanium black", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN}
        ],
        "liquids": [
            {"id": "v_liq_kiwi", "name": "Ананас киви", "stock": 1, "price": 15.0, "price_str": "15.00 BYN", "img": IMG_MAIN},
            {"id": "v_liq_straw", "name": "Клубника", "stock": 1, "price": 15.0, "price_str": "15.00 BYN", "img": IMG_MAIN}
        ]
    },
    "akadem": {
        "xros6": [
            {"id": "a_xros6_orange", "name": "Jelly Orange", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "a_xros6_blue", "name": "Jelly blue", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "a_xros6_pink", "name": "Jelly pink", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "a_xros6_pblue", "name": "Plume blue", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "a_xros6_ppink", "name": "Plume pink", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "a_xros6_pwhite", "name": "Plume white", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN},
            {"id": "a_xros6_black", "name": "Titanium black", "stock": 1, "price": 65.0, "price_str": "65.00 BYN", "img": IMG_MAIN}
        ],
        "liquids": [
            {"id": "a_liq_kiwi", "name": "Ананас киви", "stock": 1, "price": 15.0, "price_str": "15.00 BYN", "img": IMG_MAIN},
            {"id": "a_liq_straw", "name": "Клубника", "stock": 1, "price": 15.0, "price_str": "15.00 BYN", "img": IMG_MAIN}
        ]
    }
}

PRODUCT_LOOKUP = {p["id"]: p for st in PRODUCTS.values() for cat_list in st.values() for p in cat_list}

kb_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Наличие", callback_data="go_cities"), InlineKeyboardButton(text="🛒 Корзина", callback_data="go_cart")],
    [InlineKeyboardButton(text="👤 Профиль", callback_data="go_profile")]
])
kb_cities = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Минск", callback_data="city_minsk")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
])
kb_stations = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚇 Восток", callback_data="st_vostok"), InlineKeyboardButton(text="🚇 Академия наук", callback_data="st_akadem")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="go_cities")]
])
def get_cat_kb(station):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Устройства", callback_data=f"open_{station}_devices"), InlineKeyboardButton(text="Жидкость", callback_data=f"open_{station}_liquids")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="city_minsk")]
    ])
@dp.message(F.photo)
async def catch_photo_id(m: Message):
    photo_id = m.photo[-1].file_id
    await m.answer(f"ID фото для IMG_MAIN:\n<code>{photo_id}</code>", parse_mode="HTML")

@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    get_or_create_user(m.from_user.id, m.from_user.username)
    await m.answer_photo(photo=IMG_MAIN, caption="<b>PRIME SPOT | VAPE & SNUS</b>\n\nЖдем ваших заказов! 📦", reply_markup=kb_main, parse_mode="HTML")

@dp.callback_query(F.data == "go_cities")
async def screen_cities(c: CallbackQuery):
    await c.message.edit_media(media=InputMediaPhoto(media=IMG_MAIN, caption="🏙 <b>Выберите город для просмотра наличия:</b>", parse_mode="HTML"), reply_markup=kb_cities)
    await c.answer()

@dp.callback_query(F.data == "back_to_main")
async def screen_main(c: CallbackQuery):
    await c.message.edit_media(media=InputMediaPhoto(media=IMG_MAIN, caption="<b>PRIME SPOT | VAPE & SNUS</b>\n\nЖдем ваших заказов! 📦", parse_mode="HTML"), reply_markup=kb_main)
    await c.answer()

@dp.callback_query(F.data == "city_minsk")
async def screen_minsk(c: CallbackQuery):
    txt = "📍 <b>Выберите станцию самовывоза:</b>\n\n🚚 <i>Доставка по metro бесплатно, по адресу обговаривается.</i>\n\n@ghostwalk12"
    await c.message.edit_caption(caption=txt, reply_markup=kb_stations, parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("st_"))
async def screen_station_categories(c: CallbackQuery):
    station = c.data.replace("st_", "")
    st_title = "Восток" if station == "vostok" else "Академия наук"
    await c.message.edit_caption(caption=f"<b>🚇 Станция {st_title}</b>\n\nВыберите категорию:", reply_markup=get_cat_kb(station), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("open_"))
async def screen_models_or_brands(c: CallbackQuery):
    dt = c.data.split("_")
    station, mode = dt[1], dt[2]
    if mode == "devices":
        kb_models = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 XROS 6 mini", callback_data=f"showcolors_{station}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"st_{station}")]
        ])
        await c.message.edit_caption(caption="🛍 <b>XROS 6 mini</b>\n\nВыберите модель.", reply_markup=kb_models, parse_mode="HTML")
    else:
        kb_liq = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📁 ANNIMA", callback_data=f"showliq_{station}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"st_{station}")]
        ])
        await c.message.edit_caption(caption="🛍 <b>Жидкость</b>\n\nВыберите бренд жидкости:", reply_markup=kb_liq, parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("showcolors_"))
async def screen_device_colors(c: CallbackQuery):
    station = c.data.replace("showcolors_", "")
    p_list = PRODUCTS[station]["xros6"]
    buttons = []
    for idx, p in enumerate(p_list):
        buttons.append([InlineKeyboardButton(text=p["name"], callback_data=f"nav_{station}_xros6_{idx}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"open_{station}_devices")])
    await c.message.edit_caption(caption="🛍 <b>XROS 6 mini</b>\n\nВыберите нужный цвет:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("showliq_"))
async def screen_liquids_list(c: CallbackQuery):
    station = c.data.replace("showliq_", "")
    p_list = PRODUCTS[station]["liquids"]
    buttons = []
    for idx, p in enumerate(p_list):
        buttons.append([InlineKeyboardButton(text=p["name"], callback_data=f"nav_{station}_liquids_{idx}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"open_{station}_liquids")])
    await c.message.edit_caption(caption="🛍 <b>Жидкость ANNIMA</b>\n\nВыберите вкус из списка:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("nav_"))
async def product_carousel(c: CallbackQuery):
    dt = c.data.split("_")
    station, category, curr_idx = dt[1], dt[2], int(dt[3])
    p_list = PRODUCTS[station][category]
    prod = p_list[curr_idx]
    tot = len(p_list)
    st_title = "Восток" if station == "vostok" else "Академия наук"
    back_target = f"showcolors_{station}" if category == "xros6" else f"showliq_{station}"
    title_prefix = f"XROS 6 mini {prod['name']}" if category == "xros6" else f"ANNIMA {prod['name']}"
    cap = f"📦 <b>КАРТОЧКА ТОВАРА</b>\n\n<b>Название:</b> {title_prefix}\n<b>💰 Цена:</b> {prod['price_str']}\n<b>В наличии:</b> {prod['stock']} шт.\n🚇 <b>Станция:</b> {st_title}"
    kb_prod = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️", callback_data=f"nav_{station}_{category}_{(curr_idx-1)%tot}"),
         InlineKeyboardButton(text=f"{curr_idx+1}/{tot}", callback_data="dummy"),
         InlineKeyboardButton(text="▶️", callback_data=f"nav_{station}_{category}_{(curr_idx+1)%tot}")],
        [InlineKeyboardButton(text="➕ В корзину", callback_data=f"add_{prod['id']}"), InlineKeyboardButton(text="🛒 Корзина", callback_data="go_cart")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back_target)]
    ])
    await c.message.edit_media(media=InputMediaPhoto(media=prod["img"], caption=cap, parse_mode="HTML"), reply_markup=kb_prod)
    await c.answer()

@dp.callback_query(F.data.startswith("add_"))
async def add_to_cart(c: CallbackQuery):
    p_id = c.data.replace("add_", "")
    u_id = c.from_user.id
    if u_id not in USER_CARTS: USER_CARTS[u_id] = {}
    USER_CARTS[u_id][p_id] = USER_CARTS[u_id].get(p_id, 0) + 1
    await c.answer("Товар добавлен в корзину! 🛒", show_alert=True)

@dp.callback_query(F.data == "go_cart")
async def show_cart(c: CallbackQuery):
    u_id = c.from_user.id
    cart = USER_CARTS.get(u_id, {})
    if not cart or sum(cart.values()) == 0:
        await c.answer("Ваша корзина пуста.", show_alert=True)
        return
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    total = 0.0
    for p_id, count in cart.items():
        if count > 0 and p_id in PRODUCT_LOOKUP:
            prod = PRODUCT_LOOKUP[p_id]
            cost = prod["price"] * count
            total += cost
            text += f"▪️ {prod['name']}\n  {count} шт. х {prod['price_str']} = {cost:.2f} BYN\n\n"
    text += f"<b>Итого к оплате: {total:.2f} BYN</b>"
    kb_cart = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart")],
        [InlineKeyboardButton(text="⌂ Меню", callback_data="back_to_main")]
    ])
    await c.message.edit_media(media=InputMediaPhoto(media=IMG_MAIN, caption=text, parse_mode="HTML"), reply_markup=kb_cart)
    await c.answer()

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(c: CallbackQuery):
    USER_CARTS[c.from_user.id] = {}
    await c.answer("Корзина очищена")
    await screen_main(c)

@dp.callback_query(F.data == "checkout")
async def checkout_cart(c: CallbackQuery):
    u_id = c.from_user.id
    username = f"@{c.from_user.username}" if c.from_user.username else f"ID: {u_id}"
    cart = USER_CARTS.get(u_id, {})
    admin_text = f"🔔 <b>НОВЫЙ ЗАКАЗ В МАГАЗИНЕ!</b>\n\n<b>Покупатель:</b> {username}\n<b>ID:</b> <code>{u_id}</code>\n\n<b>Состав корзины:</b>\n"
    total = 0.0
    for p_id, count in cart.items():
        if count > 0 and p_id in PRODUCT_LOOKUP:
            prod = PRODUCT_LOOKUP[p_id]
            cost = prod["price"] * count
            total += cost
            admin_text += f"• {prod['name']} — {count} шт. ({cost:.2f} BYN)\n"
    admin_text += f"\n<b>Итого к оплате: {total:.2f} BYN</b>"
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка уведомления админа: {e}")
    increment_user_orders(u_id)
    st = "🎉 <b>Заказ успешно оформлен!</b>\n\nМенеджер @ghostwalk12 свяжется с вами для подтверждения."
    USER_CARTS[u_id] = {}
    await c.message.edit_media(media=InputMediaPhoto(media=IMG_MAIN, caption=st, parse_mode="HTML"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⌂ В меню", callback_data="back_to_main")]]))
    await c.answer()

@dp.callback_query(F.data == "go_profile")
async def screen_profile(c: CallbackQuery):
    u_id = c.from_user.id
    u_name = f"@{c.from_user.username}" if c.from_user.username else "Не установлен"
    user_data = get_or_create_user(u_id, c.from_user.username)
    pt = f"👤 <b>Личный кабинет профиля</b>\n\n<b>Аккаунт:</b> {u_name}\n<b>ID:</b> <code>{u_id}</code>\n<b>Завершённых заказов:</b> {user_data['orders']}\n\n<b>🎟 Купоны:</b> {user_data['coupons']} (1 купон = 1 BYN)\n<b>Рассылка:</b> Активна"
    kb_profile = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⌂ В меню", callback_data="back_to_main")]])
    await c.message.edit_media(media=InputMediaPhoto(media=IMG_MAIN, caption=pt, parse_mode="HTML"), reply_markup=kb_profile)
    await c.answer()

@dp.callback_query(F.data == "dummy_cat")
async def dummy_cat(c: CallbackQuery): await c.answer("В этой локации товаров пока нет.")

@dp.callback_query(F.data == "dummy_alert")
async def dummy_alert(c: CallbackQuery): await c.answer("Раздел находится в разработке!", show_alert=True)

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_bot():
    print("Магазин D&A SHOP запущен в PaaS-облаке!")
    asyncio.create_task(dp.start_polling(bot))
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    while True:
        await asyncio.sleep(3600)

asyncio.run(start_bot())
