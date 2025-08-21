from colorama import Fore

from pyrogram import Client, filters, idle, errors

from pyrogram.types import *

from functools import wraps

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import asyncio

import subprocess

import html

import zipfile

import sqlite3
import sys

import shutil

import signal

import re

import os

#==================== Config =====================#

Admin = 7177420250  # آیدی عددی مالک سلف ساز (قرار دهید آیدی عددی خود را اینجا)
 
Token = "8008986401:AAHAlu9o31Eyj4x8iUZ3dhX5gDstqhkOEFc" # توکن ربات سلف ساز

API_ID = 16827053  # ایپی ایدی اکانت مالک سلف ساز (قرار دهید API ID خود را اینجا)

API_HASH = "398333f2b7999d2074324ac5dc840483" # ایپی هش اکانت مالک سلف ساز

Channel_ID = "SKIPHELP" # چنل سلف ساز بدون @

Helper_ID = "SKIPHelpbot" # ایدی ربات هلپر بدون @

DBName = "" # نام دیتابیس اول (برای sqlite می‌شود فایل، خالی به معنی database.sqlite)

DBUser = "" # یوزر دیتابیس اول (غیر ضروری برای sqlite)

DBPass = "" # پسورد دیتابیس اول (غیر ضروری برای sqlite)

HelperDBName = "" # نام دیتابیس هلپر (برای sqlite می‌شود فایل، خالی به معنی helper.sqlite)

HelperDBUser = "" # یوزر دیتابیس هلپر (غیر ضروری برای sqlite)

HelperDBPass = "" # پسورد دیتابیس هلپر (غیر ضروری برای sqlite)

CardNumber = "65" # شماره کارت برای فروش

CardName = "A" # نام صاحب شماره کارت 

MAIN_DB_FILE = DBName if DBName else "database.sqlite"
HELPER_DB_FILE = HelperDBName if HelperDBName else "helper.sqlite"

#==================== Create =====================#

if not os.path.isdir("sessions"):
    os.mkdir("sessions")
if not os.path.isdir("selfs"):
    os.mkdir("selfs")

#===================== App =======================#

app = Client("Bot", api_id=API_ID, api_hash=API_HASH, bot_token=Token)


scheduler = AsyncIOScheduler()
scheduler.start()

temp_Client = {}

lock = asyncio.Lock()

def _sanitize_sql(q):
    # remove MySQL-specific LIMIT 1 (sqlite doesn't support LIMIT in UPDATE/DELETE) and backticks
    q = re.sub(r"\s+LIMIT\s+1\b", "", q, flags=re.IGNORECASE)
    q = q.replace("`", "")
    return q

def get_conn(file):
    conn = sqlite3.connect(file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_data(query, params=()):
    q = _sanitize_sql(query)
    with get_conn(MAIN_DB_FILE) as conn:
        cur = conn.execute(q, params)
        row = cur.fetchone()
        return dict(row) if row is not None else None

def get_datas(query, params=()):
    q = _sanitize_sql(query)
    with get_conn(MAIN_DB_FILE) as conn:
        cur = conn.execute(q, params)
        result = cur.fetchall()
        return result

def update_data(query, params=()):
    q = _sanitize_sql(query)
    with get_conn(MAIN_DB_FILE) as conn:
        cur = conn.execute(q, params)
        conn.commit()

def helper_getdata(query, params=()):
    q = _sanitize_sql(query)
    with get_conn(HELPER_DB_FILE) as conn:
        cur = conn.execute(q, params)
        row = cur.fetchone()
        return dict(row) if row is not None else None

def helper_updata(query, params=()):
    q = _sanitize_sql(query)
    with get_conn(HELPER_DB_FILE) as conn:
        cur = conn.execute(q, params)
        conn.commit()


# Create necessary tables (SQLite-friendly)
update_data("""
CREATE TABLE IF NOT EXISTS bot(
status TEXT DEFAULT 'ON'
);
""")

update_data("""
CREATE TABLE IF NOT EXISTS user(
id INTEGER PRIMARY KEY,
step TEXT DEFAULT 'none',
phone TEXT DEFAULT NULL,
amount INTEGER DEFAULT 0,
expir INTEGER DEFAULT 0,
account TEXT DEFAULT 'unverified',
self TEXT DEFAULT 'inactive',
pid INTEGER DEFAULT NULL
);
""")

update_data("""
CREATE TABLE IF NOT EXISTS block(
id INTEGER PRIMARY KEY
);
""")

helper_updata("""
CREATE TABLE IF NOT EXISTS ownerlist(
id INTEGER PRIMARY KEY
);
""")

helper_updata("""
CREATE TABLE IF NOT EXISTS adminlist(
id INTEGER PRIMARY KEY
);
""")

bot = get_data("SELECT * FROM bot")
if bot is None:
    update_data("INSERT INTO bot(status) VALUES('ON')")

OwnerUser = helper_getdata(f"SELECT * FROM ownerlist WHERE id = '{Admin}'")
if OwnerUser is None:
    helper_updata(f"INSERT INTO ownerlist(id) VALUES({Admin})")

AdminUser = helper_getdata(f"SELECT * FROM adminlist WHERE id = '{Admin}'")
if AdminUser is None:
    helper_updata(f"INSERT INTO adminlist(id) VALUES({Admin})")

def add_admin(user_id):
    if helper_getdata(f"SELECT * FROM adminlist WHERE id = '{user_id}'") is None:
        helper_updata(f"INSERT INTO adminlist(id) VALUES({user_id})")

def delete_admin(user_id):
    if helper_getdata(f"SELECT * FROM adminlist WHERE id = '{user_id}'") is not None:
        helper_updata(f"DELETE FROM adminlist WHERE id = '{user_id}'")

def terminate_process(pid):
    try:
        # Try POSIX kill first
        os.kill(pid, signal.SIGKILL)
    except Exception:
        # Fallback for Windows: taskkill
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def checker(func):
    @wraps(func)
    async def wrapper(c, m, *args, **kwargs):
        chat_id = m.chat.id if hasattr(m, "chat") else m.from_user.id
        bot = get_data("SELECT * FROM bot")
        block = get_data(f"SELECT * FROM block WHERE id = '{chat_id}'")

        if block is not None and chat_id != Admin:
            return
        
        try:
            await app.get_chat_member(Channel_ID, chat_id)
        except errors.UserNotParticipant:
            await app.send_message(chat_id, """**• برای استفاده از خدمات ما باید ابتدا در کانال ما عضو باشید ، بعد از اینکه عضو شدید ربات را مجدد استارت کنید.
/start**""", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="عضویت", url=f"https://t.me/{Channel_ID}")
                        ]
                    ]
                ))
            return
        except errors.ChatAdminRequired:
            if chat_id == Admin:
                await app.send_message(Admin, "ربات برای فعال شدن جوین اجباری در کانال مورد نظر ادمین نمی باشد!\nلطفا ربات را با دسترسی های لازم در کانال مورد نظر ادمین کنید")
            return

        if bot["status"] == "OFF" and chat_id != Admin:
            await app.send_message(chat_id, "**ربات خاموش میباشد!**")
            return
        
        return await func(c, m, *args, **kwargs)
    return wrapper

async def expirdec(user_id):
    user = get_data(f"SELECT * FROM user WHERE id = '{user_id}'")
    user_expir = user["expir"]
    if user_expir > 0:
        user_upexpir = user_expir - 1
        update_data(f"UPDATE user SET expir = '{user_upexpir}' WHERE id = '{user_id}'")
    else:
        job = scheduler.get_job(str(user_id))
        if job:
            scheduler.remove_job(str(user_id))
        if user_id != Admin:
            delete_admin(user_id)
        if os.path.isdir(f"selfs/self-{user_id}"):
            pid = user["pid"]
            if pid:
                terminate_process(pid)
            await asyncio.sleep(1)
            shutil.rmtree(f"selfs/self-{user_id}")
        if os.path.isfile(f"sessions/{user_id}.session"):
            async with Client(f"sessions/{user_id}") as user_client:
                await user_client.log_out()
            if os.path.isfile(f"sessions/{user_id}.session"):
                os.remove(f"sessions/{user_id}.session")
        if os.path.isfile(f"sessions/{user_id}.session-journal"):
            os.remove(f"sessions/{user_id}.session-journal")
        await app.send_message(user_id, "کاربر گرامی اشتراک سلف شما به پایان رسید. برای خرید مجدد اشتراک به قسمت خرید اشتراک مراجعه کنید")
        update_data(f"UPDATE user SET self = 'inactive' WHERE id = '{user_id}'")
        update_data(f"UPDATE user SET pid = NULL WHERE id = '{user_id}'")

async def setscheduler(user_id):
    job = scheduler.get_job(str(user_id))
    if not job:
        scheduler.add_job(expirdec, "interval", hours=24, args=[user_id], id=str(user_id))

Main = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="👤 حساب کاربری", callback_data="MyAccount")
        ],
        [
            InlineKeyboardButton(text="💰 خرید سلف", callback_data="BuySub")
        ],
        [
            InlineKeyboardButton(text="💎 قیمت ها", callback_data="Price"),
            InlineKeyboardButton(text="💳 کیف پول", callback_data="Wallet")
        ],
        [
            InlineKeyboardButton(text="✅ احراز هویت", callback_data="AccVerify"),
            InlineKeyboardButton(text="🔰 اطلاعات سلف", callback_data="Subinfo")
        ],
        [
            InlineKeyboardButton(text="📢 کانال ما", url="https://t.me/DisVpn"),
            InlineKeyboardButton(text="❓ سلف چیست؟", callback_data="WhatSelf")
        ],
        [
            InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="Support")
        ]
    ]
)

@app.on_message(filters.private, group=-1)
async def update(c, m):
    user = get_data(f"SELECT * FROM user WHERE id = '{m.chat.id}'")
    if user is None:
        update_data(f"INSERT INTO user(id) VALUES({m.chat.id})")

@app.on_message(filters.private&filters.command("start"))
@checker
async def update(c, m):
    await app.send_message(m.chat.id, f"""**╭─────────────────────╮
│   🌟 سلام عزیز {html.escape(m.chat.first_name)} 🌟   │
│ 🎉 به Wenos Self خوش آمدید 🎉 │
╰─────────────────────╯

🤖 من دستیار هوشمند شما هستم
💡 بهترین تجربه مدیریت اکانت را برایتان فراهم می‌کنم

🔹━━━━━━━━━━━━━━━━━━━━━━━🔹
       ✨ ویژگی‌های برتر ما ✨
🔹━━━━━━━━━━━━━━━━━━━━━━━🔹

⚡ سرعت بی‌نظیر
🚀 امکانات پیشرفته
🔄 بدون قطعی
🚫 بدون تبلیغات مزاحم

🎯 یک خرید، تجربه‌ای بی‌نقص! 🎯**""", reply_markup=Main)
    update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
    async with lock:
        if m.chat.id in temp_Client:
            del temp_Client[m.chat.id]
    if os.path.isfile(f"sessions/{m.chat.id}.session") and not os.path.isfile(f"sessions/{m.chat.id}.session-journal"):
        os.remove(f"sessions/{m.chat.id}.session")

@app.on_callback_query()
@checker
async def call(c, call):
    global temp_Client
    user = get_data(f"SELECT * FROM user WHERE id = '{call.from_user.id}'")
    phone_number = user["phone"]
    account_status = "تایید شده" if user["account"] == "verified" else "تایید نشده"
    expir = user["expir"]
    amount = user["amount"]
    chat_id = call.from_user.id
    m_id = call.message.id
    data = call.data
    username = f"@{call.from_user.username}" if call.from_user.username else "وجود ندارد"

    if data == "MyAccount":
        await app.edit_message_text(chat_id, m_id, "**╭─────────────────────────╮\n│     👤 حساب کاربری شما     │\n╰─────────────────────────╯\n\n📊 اطلاعات کامل حساب شما:**", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="نام شما", callback_data="text"),
                    InlineKeyboardButton(text=f"{call.from_user.first_name}", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text="آیدی شما", callback_data="text"),
                    InlineKeyboardButton(text=f"{call.from_user.id}", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text="یوزرنیم شما", callback_data="text"),
                    InlineKeyboardButton(text=f"{username}", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text="موجودی شما", callback_data="text"),
                    InlineKeyboardButton(text=f"{amount} تومان", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text="وضعیت حساب شما", callback_data="text"),
                    InlineKeyboardButton(text=f"{account_status}", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text="----------------", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text=f"انقضای شما ({expir}) روز", callback_data="text")
                ],
                [
                    InlineKeyboardButton(text="برگشت", callback_data="Back")
                ]
            ]
        ))
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data == "BuySub" or data == "Back2":
        if user["phone"] is None:
            await app.delete_messages(chat_id, m_id)
            await app.send_message(chat_id, "**لطفا با استفاده از دکمه زیر شماره خود را به اشتراک بگذارید**", reply_markup=ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton(text="اشتراک گذاری شماره", request_contact=True)
                    ]
                ],resize_keyboard=True
            ))
            update_data(f"UPDATE user SET step = 'contact' WHERE id = '{call.from_user.id}'")
        else:
            if user["account"] == "verified":
                if not os.path.isfile(f"sessions/{chat_id}.session-journal"):
                    await app.edit_message_text(chat_id, m_id, "**🛒 انتخاب پلن اشتراک**\n\n💰 لطفاً پلن مورد نظر خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(text="⏰ یک هفته  •  💰 20 تومان", callback_data="Login-7-20")
                            ],
                            [
                                InlineKeyboardButton(text="📅 یک ماهه  •  💰 50 تومان", callback_data="Login-30-50")
                            ],
                            [
                                InlineKeyboardButton(text="📅 دو ماهه  •  💰 100 تومان", callback_data="Login-60-100")
                            ],
                            [
                                InlineKeyboardButton(text="📅 سه ماهه  •  💰 150 تومان", callback_data="Login-90-150")
                            ],
                            [
                                InlineKeyboardButton(text="📅 چهار ماهه  •  💰 200 تومان", callback_data="Login-120-200")
                            ],
                            [
                                InlineKeyboardButton(text="📅 پنج ماهه  •  💰 250 تومان", callback_data="Login-150-250")
                            ],
                            [
                                InlineKeyboardButton(text="برگشت", callback_data="Back")
                            ]
                        ]
                    ))
                    update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
                    async with lock:
                        if chat_id in temp_Client:
                            del temp_Client[chat_id]
                    if os.path.isfile(f"sessions/{chat_id}.session") and not os.path.isfile(f"sessions/{chat_id}.session-journal"):
                        os.remove(f"sessions/{chat_id}.session")
                else:
                    await app.answer_callback_query(call.id, text="اشتراک سلف برای شما فعال است!", show_alert=True)
            else:
                await app.edit_message_text(chat_id, m_id, "برای خرید اشتراک ابتدا باید احراز هویت کنید", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="احراز هویت", callback_data="AccVerify")
                        ],
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data.split("-")[0] == "Login":
        expir_count = data.split("-")[1]
        cost = data.split("-")[2]
        if int(amount) >= int(cost):
            mess = await app.edit_message_text(chat_id, m_id, "در حال پردازش...")
            async with lock:
                if chat_id not in temp_Client:
                    temp_Client[chat_id] = {}
                temp_Client[chat_id]["client"] = Client(f"sessions/{chat_id}", api_id=API_ID, api_hash=API_HASH, device_model="Wenos-Self", system_version="Linux")
                temp_Client[chat_id]["number"] = phone_number
                await temp_Client[chat_id]["client"].connect()
            try:
                await app.edit_message_text(chat_id, mess.id, "کد تایید 5 رقمی را با فرمت زیر ارسال کنید:\n1.2.3.4.5", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back2")
                        ]
                    ]
                ))
                async with lock:
                    temp_Client[chat_id]["response"] = await temp_Client[chat_id]["client"].send_code(temp_Client[chat_id]["number"])
                update_data(f"UPDATE user SET step = 'login1-{expir_count}-{cost}' WHERE id = '{call.from_user.id}'")

            except errors.BadRequest:
                await app.edit_message_text(chat_id, mess.id, "اتصال ناموفق بود! لطفا دوباره تلاش کنید", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back2")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
                async with lock:
                    await temp_Client[chat_id]["client"].disconnect()
                    if chat_id in temp_Client:
                        del temp_Client[chat_id]
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat_id}.session")

            except errors.PhoneNumberInvalid:
                await app.edit_message_text(chat_id, mess.id, "این شماره نامعتبر است!", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back2")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
                async with lock:
                    await temp_Client[chat_id]["client"].disconnect()
                    if chat_id in temp_Client:
                        del temp_Client[chat_id]
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat_id}.session")

            except errors.PhoneNumberBanned:
                await app.edit_message_text(chat_id, mess.id, "این اکانت محدود است!", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back2")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
                async with lock:
                    await temp_Client[chat_id]["client"].disconnect()
                    if chat_id in temp_Client:
                        del temp_Client[chat_id]
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat.id}.session")

            except Exception:
                async with lock:
                    await temp_Client[chat_id]["client"].disconnect()
                    if chat_id in temp_Client:
                        del temp_Client[chat_id]
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat_id}.session")
        else:
            await app.edit_message_text(chat_id, m_id, "موجودی حساب شما برای خرید این اشتراک کافی نیست", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="افزایش موجودی", callback_data="Wallet")
                    ],
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back2")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data == "Price":
        await app.edit_message_text(chat_id, m_id, """**💎 جدول قیمت اشتراک سلف 💎

╭─────────────────────────╮
│        📋 تعرفه ها         │
╰─────────────────────────╯

⏰ 1 هفته     ►  20,000 تومان 💰
📅 1 ماهه     ►  50,000 تومان 💰
📅 2 ماهه     ►  100,000 تومان 💰
📅 3 ماهه     ►  150,000 تومان 💰
📅 4 ماهه     ►  200,000 تومان 💰
📅 5 ماهه     ►  250,000 تومان 💰

🎯 هر چه بیشتر، ارزان‌تر! 🎯**""", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="برگشت", callback_data="Back")
                ]
            ]
        ))
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data == "Wallet" or data == "Back3":
        await app.edit_message_text(chat_id, m_id, f"**💳 کیف پول شما**\n\n💰 موجودی فعلی: {amount:,} تومان\n\n🔽 عملیات مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="💳 خرید موجودی", callback_data="BuyAmount"),
                    InlineKeyboardButton(text="📤 انتقال موجودی", callback_data="TransferAmount")
                ],
                [
                    InlineKeyboardButton(text="برگشت", callback_data="Back")
                ]
            ]
        ))
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
    
    elif data == "BuyAmount":
        if user["account"] == "verified":
            await app.edit_message_text(chat_id, m_id, "میزان موجودی مورد نظر خود را برای شارژ حساب وارد کنید:\nحداقل موجودی قابل خرید 10000 تومان است!", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back3")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'buyamount1' WHERE id = '{call.from_user.id}'")
        else:
            await app.edit_message_text(chat_id, m_id, "برای خرید موجودی ابتدا باید احراز هویت کنید", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="احراز هویت", callback_data="AccVerify")
                    ],
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back3")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
    
    elif data.split("-")[0] == "AcceptAmount":
        user_id = int(data.split("-")[1])
        count = int(data.split("-")[2])
        user_amount = get_data(f"SELECT amount FROM user WHERE id = '{user_id}'")
        user_upamount = int(user_amount["amount"]) + int(count)
        update_data(f"UPDATE user SET amount = '{user_upamount}' WHERE id = '{user_id}'")
        await app.edit_message_text(Admin, m_id, f"تایید انجام شد\nمبلغ {count} تومان به حساب کاربر [ {user_id} ] انتقال یافت\nموجودی جدید کاربر: {user_upamount} تومان")
        await app.send_message(user_id, f"درخواست شما برای افزایش موجودی تایید شد\nمبلغ {count} تومان به حساب شما انتقال یافت\nموجودی جدید شما: {user_upamount} تومان")
    
    elif data.split("-")[0] == "RejectAmount":
        user_id = int(data.split("-")[1])
        await app.edit_message_text(Admin, m_id, "درخواست کاربر مورد نظر برای افزایش موجودی رد شد")
        await app.send_message(user_id, "درخواست شما برای افزایش موجودی رد شد")
    
    elif data == "TransferAmount":
        if user["account"] == "verified":
            await app.edit_message_text(chat_id, m_id, "آیدی عددی کاربری که قصد انتقال موجودی به او را دارید ارسال کنید:", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back3")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'transferam1' WHERE id = '{call.from_user.id}'")
        else:
            await app.edit_message_text(chat_id, m_id, "برای انتقال موجودی ابتدا باید احراز هویت کنید", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="احراز هویت", callback_data="AccVerify")
                    ],
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back3")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
    
    elif data == "AccVerify":
        if user["account"] != "verified":
            await app.edit_message_text(chat_id, m_id, """**

به بخش احراز هویت خوش آمدید.

نکات :

1) شماره کارت و نام صاحب کارت کاملا مشخص باشد.

2) لطفا تاریخ اعتبار و Cvv2 کارت خود را بپوشانید!

3) اسکرین شات و عکس از کارت از داخل موبایل بانک قابل قبول نیستند

4) فقط با کارتی که احراز هویت میکنید میتوانید خرید انجام بدید و اگر با کارت دیگری اقدام کنید تراکنش ناموفق میشود و هزینه از سمت خودِ بانک به شما بازگشت داده میشود.

5) در صورتی که توانایی ارسال عکس از کارت را ندارید تنها راه حل ارسال عکس از کارت ملی یا شناسنامه صاحب کارت است.



لطفا عکس از کارتی که میخواهید با آن خرید انجام دهید ارسال کنید.

**""", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'accverify' WHERE id = '{call.from_user.id}'")
        else:
            await app.answer_callback_query(call.id, "حساب شما تایید شده است!", show_alert=True)
    
    elif data.split("-")[0] == "AcceptVerify":
        user_id = int(data.split("-")[1])
        update_data(f"UPDATE user SET account = 'verified' WHERE id = '{user_id}'")
        await app.edit_message_text(Admin, m_id, f"حساب کاربر [ {user_id} ] تایید شد")
        await app.send_message(user_id, "حساب کاربری شما تایید شد و اکنون می توانید بدون محدودیت از ربات استفاده کنید")
    
    elif data.split("-")[0] == "RejectVerify":
        user_id = int(data.split("-")[1])
        await app.edit_message_text(Admin, m_id, "درخواست کاربر مورد نظر برای تایید حساب کاربری رد شد")
        await app.send_message(user_id, "درخواست شما برای تایید حساب کاربری رد شد")

    elif data == "Subinfo" or data == "Back4":
        if os.path.isfile(f"sessions/{chat_id}.session-journal"):
            substatus = "فعال" if user["self"] == "active" else "غیرفعال"
            await app.edit_message_text(chat_id, m_id, f"وضعیت اشتراک: {substatus}\nشماره اکانت: {phone_number}\nانقضا: {expir} روز", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="خرید انقضا", callback_data="BuyExpir"),
                        InlineKeyboardButton(text="انتقال انقضا", callback_data="TransferExpir")
                    ],
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back")
                    ]
                ]
            ))
        else:
            await app.answer_callback_query(call.id, text="شما اشتراک فعالی ندارید!", show_alert=True)

    elif data == "BuyExpir":
        if user["account"] == "verified":
            await app.edit_message_text(chat_id, m_id, "میزان انقضای مورد نظر خود را برای افزایش وارد کنید:\nهزینه هر یک روز انقضا 1000 تومان است", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back4")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'buyexpir1' WHERE id = '{call.from_user.id}'")
        else:
            await app.edit_message_text(chat_id, m_id, "برای خرید انقضا ابتدا باید احراز هویت کنید", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="احراز هویت", callback_data="AccVerify")
                    ],
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back4")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data.split("-")[0] == "AcceptExpir":
        user_id = int(data.split("-")[1])
        count = int(data.split("-")[2])
        user_expir = get_data(f"SELECT expir FROM user WHERE id = '{user_id}'")
        user_upexpir = int(user_expir["expir"]) + int(count)
        update_data(f"UPDATE user SET expir = '{user_upexpir}' WHERE id = '{user_id}'")
        await app.edit_message_text(Admin, m_id, f"تایید انجام شد\n{count} روز به انقضای کاربر [ {user_id} ] افزوده شد\nانقضای جدید کاربر: {user_upexpir} روز")
        await app.send_message(user_id, f"درخواست شما برای افزایش انقضا تایید شد\n{count} روز به انقضای شما افزوده شد\nانقضای جدید شما: {user_upexpir} روز")

    elif data.split("-")[0] == "RejectExpir":
        user_id = int(data.split("-")[1])
        await app.edit_message_text(Admin, m_id, "درخواست کاربر مورد نظر برای افزایش انقضا رد شد")
        await app.send_message(user_id, "درخواست شما برای افزایش انقضا رد شد")

    elif data == "TransferExpir":
        if user["account"] == "verified":
            await app.edit_message_text(chat_id, m_id, "آیدی عددی کاربری که قصد انتقال انقضا به او را دارید ارسال کنید:", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back4")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'transferex1' WHERE id = '{call.from_user.id}'")
        else:
            await app.edit_message_text(chat_id, m_id, "برای انتقال انقضا ابتدا باید احراز هویت کنید", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="احراز هویت", callback_data="AccVerify")
                    ],
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back4")
                    ]
                ]
            ))
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data == "WhatSelf":
        await app.edit_message_text(chat_id, m_id, """**

سلف به رباتی گفته میشه که روی اکانت شما نصب میشه و امکانات خاصی رو در اختیارتون میزاره ، لازم به ذکر هست که نصب شدن بر روی اکانت شما به معنی وارد شدن ربات به اکانت شما هست ( به دلیل دستور گرفتن و انجام فعالیت ها )

از جمله امکاناتی که در اختیار شما قرار میدهد شامل موارد زیر است:



❈ گذاشتن ساعت با فونت های مختلف بر روی بیو ، اسم

❈ قابلیت تنظیم حالت خوانده شدن خودکار پیام ها

❈ تنظیم حالت پاسخ خودکار

❈ پیام انیمیشنی

❈ منشی هوشمند

❈ دریافت پنل و تنظیمات اکانت هوشمند

❈ دو زبانه بودن دستورات و جواب ها

❈ تغییر نام و کاور فایل ها

❈ اعلان پیام ادیت و حذف شده در پیوی

❈ ذخیره پروفایل های جدید و اعلان حذف پروفایل مخاطبین

----------------------------------------------------
❈ لازم به ذکر است که امکاناتی که در بالا گفته شده تنها ذره ای از امکانات سلف میباشد .

**""", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="برگشت", callback_data="Back")
                ]
            ]
        ))
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")

    elif data == "Support":
        await app.edit_message_text(chat_id, m_id, "پیام خود را ارسال کنید:", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="برگشت", callback_data="Back")
                ]
            ]
        ))
        update_data(f"UPDATE user SET step = 'support' WHERE id = '{call.from_user.id}'")

    elif data.split("-")[0] == "Reply":
        exit = data.split("-")[1]
        getuser = await app.get_users(exit)
        await app.send_message(Admin, f"پیام خود را برای کاربر [ {html.escape(getuser.first_name)} ] ارسال کنید:", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="صفحه اصلی", callback_data="Back"),
                    InlineKeyboardButton(text="پنل مدیریت", callback_data="Panel")
                ]
            ]
        ))
        update_data(f"UPDATE user SET step = 'ureply-{exit}' WHERE id = '{Admin}'")

    elif data.split("-")[0] == "Block":
        exit = data.split("-")[1]
        getuser = await app.get_users(exit)
        block = get_data(f"SELECT * FROM block WHERE id = '{exit}'")
        if block is None:
            await app.send_message(exit, "کاربر محترم شما به دلیل نقض قوانین از ربات مسدود شدید")
            await app.send_message(Admin, f"کاربر [ {html.escape(getuser.first_name)} ] از ربات بلاک شد")
            update_data(f"INSERT INTO block(id) VALUES({exit})")
        else:
            await app.send_message(Admin, f"کاربر [ {html.escape(getuser.first_name)} ] از قبل بلاک است")

    elif data == "Back":
        await app.edit_message_text(chat_id, m_id, f"""**╭─────────────────────────╮
│   🌟 سلام عزیز {html.escape(m.chat.first_name)} 🌟   │
│ 🎉 به خوش آمدید 🎉 │
╰─────────────────────────╯

🤖 من دستیار هوشمند شما هستم
💡 بهترین تجربه مدیریت اکانت را برایتان فراهم می‌کنم

🔹━━━━━━━━━━━━━━━━━━━━━━━🔹
       ✨ ویژگی‌های برتر ما ✨
🔹━━━━━━━━━━━━━━━━━━━━━━━🔹

⚡ سرعت بی‌نظیر
🚀 امکانات پیشرفته
🔄 بدون قطعی
🚫 بدون تبلیغات مزاحم

🎯 یک خرید، تجربه‌ای بی‌نقص! 🎯**""", reply_markup=Main)
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{call.from_user.id}'")
        async with lock:
            if chat_id in temp_Client:
                del temp_Client[chat_id]

    elif data == "text":
        await app.answer_callback_query(call.id, text="این دکمه نمایشی است", show_alert=True)

@app.on_message(filters.contact)
@checker
async def update(c, m):
    user = get_data(f"SELECT * FROM user WHERE id = '{m.chat.id}'")
    if user is None:
        update_data(f"INSERT INTO user(id) VALUES({m.chat.id})")
        user = get_data(f"SELECT * FROM user WHERE id = '{m.chat.id}'")
    if user["step"] == "contact":
        phone_number = str(m.contact.phone_number)
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        contact_id = m.contact.user_id
        if m.contact and m.chat.id == contact_id:
            mess = await app.send_message(m.chat.id, "شماره شما تایید شد", reply_markup=ReplyKeyboardRemove())
            update_data(f"UPDATE user SET phone = '{phone_number}' WHERE id = '{m.chat.id}'")
            await asyncio.sleep(1)
            await app.delete_messages(m.chat.id, mess.id)
            await app.send_message(m.chat.id, f"""**╭─────────────────────────╮
│   🌟 سلام عزیز {html.escape(m.chat.first_name)} 🌟   │
│ 🎉   خوش آمدید 🎉 │
╰─────────────────────────╯

🤖 من دستیار هوشمند شما هستم
💡 بهترین تجربه مدیریت اکانت را برایتان فراهم می‌کنم

🔹━━━━━━━━━━━━━━━━━━━━━━━🔹
       ✨ ویژگی‌های برتر ما ✨
🔹━━━━━━━━━━━━━━━━━━━━━━━🔹

⚡ سرعت بی‌نظیر
🚀 امکانات پیشرفته
🔄 بدون قطعی
🚫 بدون تبلیغات مزاحم

🎯 یک خرید، تجربه‌ای بی‌نقص! 🎯**""", reply_markup=Main)
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
        else:
            await app.send_message(m.chat.id, "لطفا از دکمه اشتراک گذاری شماره استفاده کنید!")

@app.on_message(filters.private)
@checker
async def update(c, m):
    global temp_Client
    user = get_data(f"SELECT * FROM user WHERE id = '{m.chat.id}'")
    if user is None:
        update_data(f"INSERT INTO user(id) VALUES({m.chat.id})")
        user = get_data(f"SELECT * FROM user WHERE id = '{m.chat.id}'")
    username = f"@{m.from_user.username}" if m.from_user.username else "وجود ندارد"
    phone_number = user["phone"]
    expir = user["expir"]
    amount = user["amount"]
    chat_id = m.chat.id
    text = m.text
    m_id = m.id

    if user["step"].split("-")[0] == "login1":
        if text and re.match(r'^\d\.\d\.\d\.\d\.\d$', text):
            code = ''.join(re.findall(r'\d', text))
            expir_count = user["step"].split("-")[1]
            cost = user["step"].split("-")[2]

            mess = await app.send_message(chat_id, "در حال پردازش...")
            try:
                async with lock:
                    await temp_Client[chat_id]["client"].sign_in(temp_Client[chat_id]["number"], temp_Client[chat_id]["response"].phone_code_hash, code)
                    await temp_Client[chat_id]["client"].disconnect()
                    if chat_id in temp_Client:
                        del temp_Client[chat_id]
                mess = await app.edit_message_text(chat_id, mess.id, "لاگین با موفقیت انجام شد")
                mess = await app.edit_message_text(chat_id, mess.id, "در حال فعالسازی سلف...\n(ممکن است چند لحظه طول بکشد)")
                if not os.path.isdir(f"selfs/self-{m.chat.id}"):
                    os.mkdir(f"selfs/self-{m.chat.id}")
                    with zipfile.ZipFile("source/Self.zip", "r") as extract:
                        extract.extractall(f"selfs/self-{m.chat.id}")
                process = subprocess.Popen([sys.executable, "self.py", str(m.chat.id), str(API_ID), API_HASH, Helper_ID], cwd=f"selfs/self-{m.chat.id}")
                await asyncio.sleep(10)
                if process.poll() is None:
                    await app.edit_message_text(chat_id, mess.id, f"سلف با موفقیت برای اکانت شما فعال شد\nمدت زمان اشتراک: {expir_count} روز", reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(text="برگشت", callback_data="Back")
                            ]
                        ]
                    ))
                    upamount = int(amount) - int(cost)
                    update_data(f"UPDATE user SET amount = '{upamount}' WHERE id = '{m.chat.id}'")
                    update_data(f"UPDATE user SET expir = '{expir_count}' WHERE id = '{m.chat.id}'")
                    update_data(f"UPDATE user SET self = 'active' WHERE id = '{m.chat.id}'")
                    update_data(f"UPDATE user SET pid = '{process.pid}' WHERE id = '{m.chat.id}'")
                    update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                    add_admin(m.chat.id)
                    await setscheduler(m.chat.id)
                    await app.send_message(Admin, f"#گزارش_خرید_اشتراک\n\nآیدی کاربر: `{m.chat.id}`\nشماره کاربر: {phone_number}\nقیمت اشتراک: {cost} تومان\nمدت زمان اشتراک: {expir_count} روز")
                else:
                    await app.edit_message_text(chat_id, mess.id, "در فعالسازی سلف برای اکانت شما مشکلی رخ داد! هیچ مبلغی از حساب شما کسر نشد\nلطفا دوباره امتحان کنید و در صورتی که مشکل ادامه داشت با پشتیبانی تماس بگیرید", reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(text="برگشت", callback_data="Back")
                            ]
                        ]
                    ))
                    update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                    if os.path.isfile(f"sessions/{chat_id}.session"):
                        os.remove(f"sessions/{chat_id}.session")

            except errors.SessionPasswordNeeded:
                await app.edit_message_text(chat_id, mess.id, "رمز تایید دو مرحله ای برای اکانت شما فعال است\nرمز را وارد کنید:", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("برگشت", callback_data="Back2")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'login2-{expir_count}-{cost}' WHERE id = '{m.chat.id}'")

            except errors.BadRequest:
                await app.edit_message_text(chat_id, mess.id, "کد نامعتبر است!")
            except errors.PhoneCodeInvalid:
                await app.edit_message_text(chat_id, mess.id, "کد نامعتبر است!")
            except errors.PhoneCodeExpired:
                await app.edit_message_text(chat_id, mess.id, "کد منقضی شده است! لطفا عملیات ورود را دوباره تکرار کنید", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back2")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                async with lock:
                    await temp_Client[chat_id]["client"].disconnect()
                    if chat_id in temp_Client:
                        del temp_Client[chat_id]
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat_id}.session")
            
            except Exception:
                async with lock:
                    if chat_id in temp_Client and "client" in temp_Client[chat_id]:
                        try:
                            await temp_Client[chat_id]["client"].disconnect()
                        except Exception:
                            pass
                        del temp_Client[chat_id]
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat_id}.session")
        else:
            await app.send_message(chat_id, "فرمت نامعتبر است! لطفا کد را با فرمت ذکر شده وارد کنید:")

    elif user["step"].split("-")[0] == "login2":
        password = text.strip() if text else ""
        expir_count = user["step"].split("-")[1]
        cost = user["step"].split("-")[2]

        mess = await app.send_message(chat_id, "در حال پردازش...")
        try:
            async with lock:
                await temp_Client[chat_id]["client"].check_password(password)
                await temp_Client[chat_id]["client"].disconnect()
                if chat_id in temp_Client:
                    del temp_Client[chat_id]
            mess = await app.edit_message_text(chat_id, mess.id, "لاگین با موفقیت انجام شد")
            mess = await app.edit_message_text(chat_id, mess.id, "در حال فعالسازی سلف...\n(ممکن است چند لحظه طول بکشد)")
            if not os.path.isdir(f"selfs/self-{m.chat.id}"):
                os.mkdir(f"selfs/self-{m.chat.id}")
                with zipfile.ZipFile("source/Self.zip", "r") as extract:
                    extract.extractall(f"selfs/self-{m.chat.id}")
            process = subprocess.Popen([sys.executable, "self.py", str(m.chat.id), str(API_ID), API_HASH, Helper_ID], cwd=f"selfs/self-{m.chat.id}")
            await asyncio.sleep(10)
            if process.poll() is None:
                await app.edit_message_text(chat_id, mess.id, f"سلف با موفقیت برای اکانت شما فعال شد\nمدت زمان اشتراک: {expir_count} روز", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back")
                        ]
                    ]
                ))
                upamount = int(amount) - int(cost)
                update_data(f"UPDATE user SET amount = '{upamount}' WHERE id = '{m.chat.id}'")
                update_data(f"UPDATE user SET expir = '{expir_count}' WHERE id = '{m.chat.id}'")
                update_data(f"UPDATE user SET self = 'active' WHERE id = '{m.chat.id}'")
                update_data(f"UPDATE user SET pid = '{process.pid}' WHERE id = '{m.chat.id}'")
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                add_admin(m.chat.id)
                await setscheduler(m.chat.id)
                await app.send_message(Admin, f"#گزارش_خرید_اشتراک\n\nآیدی کاربر: `{m.chat.id}`\nشماره کاربر: {phone_number}\nقیمت اشتراک: {cost} تومان\nمدت زمان اشتراک: {expir_count} روز")
            else:
                await app.edit_message_text(chat_id, mess.id, "در فعالسازی سلف برای اکانت شما مشکلی رخ داد! هیچ مبلغی از حساب شما کسر نشد\nلطفا دوباره امتحان کنید و در صورتی که مشکل ادامه داشت با پشتیبانی تماس بگیرید", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                if os.path.isfile(f"sessions/{chat_id}.session"):
                    os.remove(f"sessions/{chat_id}.session")

        except errors.BadRequest:
            await app.edit_message_text(chat_id, mess.id, "رمز نادرست است!\nرمز را وارد کنید:", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="برگشت", callback_data="Back2")
                    ]
                ]
            ))

        except Exception:
            async with lock:
                if chat_id in temp_Client and "client" in temp_Client[chat_id]:
                    try:
                        await temp_Client[chat_id]["client"].disconnect()
                    except Exception:
                        pass
                    del temp_Client[chat_id]
            if os.path.isfile(f"sessions/{chat_id}.session"):
                os.remove(f"sessions/{chat_id}.session")

    elif user["step"] == "buyamount1":
        if text and text.isdigit():
            count = text.strip()
            if int(count) >= 10000:
                await app.send_message(chat_id, f"فاکتور افزایش موجودی به مبلغ {count} تومان ایجاد شد\n\nشماره کارت: `{CardNumber}`\nبه نام {CardName}\nمبلغ قابل پرداخت: {count} تومان\n\nبعد از پرداخت رسید تراکنش را در همین قسمت ارسال کنید", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back3")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'buyamount2-{count}' WHERE id = '{m.chat.id}'")
            else:
                await app.send_message(chat_id, "حداقل موجودی قابل خرید 10000 تومان است!")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عدد مجاز است")

    elif user["step"].split("-")[0] == "buyamount2":
        if m.photo:
            count = int(user["step"].split("-")[1])
            mess = await app.forward_messages(from_chat_id=chat_id, chat_id=Admin, message_ids=m_id)
            await app.send_message(Admin, f"""

مدیر گرامی درخواست افزایش موجودی جدید دارید



نام کاربر: {html.escape(m.chat.first_name)}

آیدی کاربر: `{m.chat.id}`

یوزرنیم کاربر: {username}

مبلغ درخواستی کاربر: {count} تومان

""", reply_to_message_id=mess.id, reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("تایید", callback_data=f"AcceptAmount-{chat_id}-{count}"),
                        InlineKeyboardButton("رد کردن", callback_data=f"RejectAmount-{chat_id}")
                    ]
                ]
            ))
            await app.send_message(chat_id, "رسید تراکنش شما ارسال شد. لطفا منتظر تایید توسط مدیر باشید", reply_to_message_id=m_id)
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عکس مجاز است")
    
    elif user["step"] == "transferam1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                if user_id != m.chat.id:
                    await app.send_message(chat_id, "میزان موجودی مورد نظر خود را برای انتقال وارد کنید:\nحداقل موجودی قابل ارسال 10000 تومان است")
                    update_data(f"UPDATE user SET step = 'transferam2-{user_id}' WHERE id = '{m.chat.id}'")
                else:
                    await app.send_message(chat_id, "شما نمی توانید به خودتان موجودی انتقال دهید!")
            else:
                await app.send_message(chat_id, "چنین کاربری در ربات یافت نشد!")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عدد مجاز است")
    
    elif user["step"].split("-")[0] == "transferam2":
        if text and text.isdigit():
            user_id = int(user["step"].split("-")[1])
            count = text.strip()
            if int(amount) >= int(count):
                if int(count) >= 10000:
                    user_amount = get_data(f"SELECT amount FROM user WHERE id = '{user_id}'")
                    upamount = int(amount) - int(count)
                    user_upamount = int(user_amount["amount"]) + int(count)
                    update_data(f"UPDATE user SET amount = '{upamount}' WHERE id = '{m.chat.id}'")
                    update_data(f"UPDATE user SET amount = '{user_upamount}' WHERE id = '{user_id}'")
                    await app.send_message(chat_id, f"مبلغ {count} تومان از حساب شما کسر شد و به حساب کاربر [ {user_id} ] انتقال یافت\nموجودی جدید شما: {upamount} تومان", reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(text="برگشت", callback_data="Back3")
                            ]
                        ]
                    ))
                    await app.send_message(user_id, f"مبلغ {count} تومان از حساب کاربر [ {m.chat.id} ] به حساب شما انتقال یافت\nموجودی جدید شما: {user_upamount} تومان")
                    update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                else:
                    await app.send_message(chat_id, "حداقل موجودی قابل ارسال 10000 تومان است!")
            else:
                await app.send_message(chat_id, "موجودی شما کافی نیست!")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عدد مجاز است")

    elif user["step"] == "accverify":
        if m.photo:
            mess = await app.forward_messages(from_chat_id=chat_id, chat_id=Admin, message_ids=m_id)
            await app.send_message(Admin, f"""

مدیر گرامی درخواست تایید حساب کاربری دارید



نام کاربر: {html.escape(m.chat.first_name)}

آیدی کاربر: `{m.chat.id}`

یوزرنیم کاربر: {username}

""", reply_to_message_id=mess.id, reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("تایید", callback_data=f"AcceptVerify-{chat_id}"),
                        InlineKeyboardButton("رد کردن", callback_data=f"RejectVerify-{chat_id}")
                    ]
                ]
            ))
            await app.send_message(chat_id, "درخواست شما برای تایید حساب کاربری ارسال شد. لطفا منتظر تایید توسط مدیر باشید", reply_to_message_id=m_id)
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عکس مجاز است")

    elif user["step"] == "buyexpir1":
        if text and text.isdigit():
            count = int(text.strip())
            if int(count) > 0:
                await app.send_message(chat_id, f"فاکتور افزایش انقضای به مدت {count} روز ایجاد شد\n\nشماره کارت: `{CardNumber}`\nبه نام {CardName}\nمبلغ قابل پرداخت: {count*1000} تومان\n\nبعد از پرداخت رسید تراکنش را در همین قسمت ارسال کنید", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(text="برگشت", callback_data="Back4")
                        ]
                    ]
                ))
                update_data(f"UPDATE user SET step = 'buyexpir2-{count}' WHERE id = '{m.chat.id}'")
            else:
                await app.send_message(chat_id, "حداقل انقضای قابل خرید 1 روز است!")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عدد مجاز است")

    elif user["step"].split("-")[0] == "buyexpir2":
        if m.photo:
            count = int(user["step"].split("-")[1])
            mess = await app.forward_messages(from_chat_id=chat_id, chat_id=Admin, message_ids=m_id)
            await app.send_message(Admin, f"""

مدیر گرامی درخواست افزایش انقضای جدید دارید



نام کاربر: {html.escape(m.chat.first_name)}

آیدی کاربر: `{m.chat.id}`

یوزرنیم کاربر: {username}

تعداد روز های درخواستی کاربر: {count} روز

""", reply_to_message_id=mess.id, reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("تایید", callback_data=f"AcceptExpir-{chat_id}-{count}"),
                        InlineKeyboardButton("رد کردن", callback_data=f"RejectExpir-{chat_id}")
                    ]
                ]
            ))
            await app.send_message(chat_id, "رسید تراکنش شما ارسال شد. لطفا منتظر تایید توسط مدیر باشید", reply_to_message_id=m_id)
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عکس مجاز است")
        
    elif user["step"] == "transferex1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                if user_id != m.chat.id:
                    if os.path.isfile(f"sessions/{user_id}.session-journal"):
                        await app.send_message(chat_id, "میزان انقضای مورد نظر خود را برای انتقال وارد کنید:\nحداقل باید 10 روز انقضا برای شما باقی بماند!")
                        update_data(f"UPDATE user SET step = 'transferex2-{user_id}' WHERE id = '{m.chat.id}'")
                    else:
                        await app.send_message(chat_id, "اشتراک سلف برای این کاربر فعال نیست!")
                else:
                    await app.send_message(chat_id, "شما نمی توانید به خودتان انقضا انتقال دهید!")
            else:
                await app.send_message(chat_id, "چنین کاربری در ربات یافت نشد!")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عدد مجاز است")
    
    elif user["step"].split("-")[0] == "transferex2":
        if text and text.isdigit():
            user_id = int(user["step"].split("-")[1])
            count = text.strip()
            if int(expir) >= int(count):
                if int(expir) - int(count) >= 10:
                    user_expir = get_data(f"SELECT expir FROM user WHERE id = '{user_id}'")
                    upexpir = int(expir) - int(count)
                    user_upexpir = int(user_expir["expir"]) + int(count)
                    update_data(f"UPDATE user SET expir = '{upexpir}' WHERE id = '{m.chat.id}'")
                    update_data(f"UPDATE user SET expir = '{user_upexpir}' WHERE id = '{user_id}'")
                    await app.send_message(chat_id, f"{count} روز از انقضای شما کسر شد و به کاربر [ {user_id} ] انتقال یافت\nانقضای جدید شما: {upexpir} روز", reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(text="برگشت", callback_data="Back4")
                            ]
                        ]
                    ))
                    await app.send_message(user_id, f"{count} روز از انقضای کاربر [ {m.chat.id} ] به شما انتقال یافت\nانقضای جدید شما: {user_upexpir} روز")
                    update_data(f"UPDATE user SET step = 'none' WHERE id = '{m.chat.id}'")
                else:
                    await app.send_message(chat_id, "حداقل باید 10 روز انقضا برای شما باقی بماند!")
            else:
                await app.send_message(chat_id, "انقضای شما کافی نیست!")
        else:
            await app.send_message(chat_id, "ورودی نامعتبر! فقط ارسال عدد مجاز است")

    elif user["step"] == "support":
        mess = await app.forward_messages(from_chat_id=chat_id, chat_id=Admin, message_ids=m_id)
        await app.send_message(Admin, f"""

مدیر گرامی پیام ارسال شده جدید دارید



نام کاربر: {html.escape(m.chat.first_name)}

آیدی کاربر: `{m.chat.id}`

یوزرنیم کاربر: {username}

""", reply_to_message_id=mess.id, reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("پاسخ", callback_data=f"Reply-{chat_id}"),
                    InlineKeyboardButton("بلاک", callback_data=f"Block-{chat_id}")
                ]
            ]
        ))
        await app.send_message(chat_id, "پیام شما ارسال شد و در اسرع وقت به آن پاسخ داده خواهد شد", reply_to_message_id=m_id)

    elif user["step"].split("-")[0] == "ureply":
        exit = user["step"].split("-")[1]
        mess = await app.copy_message(from_chat_id=Admin, chat_id=exit, message_id=m_id)
        await app.send_message(exit, "کاربر گرامی پیام ارسال شده جدید از پشتیبانی دارید", reply_to_message_id=mess.id)
        await app.send_message(Admin, "پیام شما ارسال شد پیام دیگری ارسال یا روی یکی از گزینه های زیر کلیک کنید:", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="صفحه اصلی", callback_data="Back"),
                    InlineKeyboardButton(text="پنل مدیریت", callback_data="Panel")
                ]
            ]
        ))

#===================== Panel ======================#

Panel = ReplyKeyboardMarkup(
    [
        [
            ("📊 آمار سیستم")
        ],
        [
            ("📢 ارسال همگانی"),
            ("🔄 فوروارد همگانی")
        ],
        [
            ("🚫 بلاک کاربر"),
            ("✅ آنبلاک کاربر")
        ],
        [
            ("💰 افزودن موجودی"),
            ("💸 کسر موجودی")
        ],
        [
            ("⏰ افزودن اشتراک"),
            ("⏱️ کسر اشتراک")
        ],
        [
            ("🟢 فعال کردن سلف"),
            ("🔴 غیرفعال کردن سلف")
        ],
        [
            ("🔵 روشن کردن ربات"),
            ("🔴 خاموش کردن ربات")
        ],
        [
            ("🏠 صفحه اصلی")
        ]
    ],resize_keyboard=True
)

AdminBack = ReplyKeyboardMarkup(
    [
        [
            ("🔙 برگشت")
        ]
    ],resize_keyboard=True
)

@app.on_message(filters.private&filters.user(Admin)&filters.command("panel"), group=1)
async def update(c, m):
    await app.send_message(Admin, """**╭─────────────────────────╮
│     👑 پنل مدیریت ارشد     │
│    🛠️ Wenos Self Admin    │
╰─────────────────────────╯

🎛️ به پنل مدیریت خوش آمدید!
🔐 دسترسی کامل به سیستم**""", reply_markup=Panel)
    update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
    async with lock:
        if Admin in temp_Client:
            del temp_Client[Admin]

@app.on_callback_query(filters.user(Admin), group=-1)
async def call(c, call):
    data = call.data
    m_id = call.message.id
    if data == "Panel":
        await app.send_message(Admin, "مدیر گرامی به پنل مدیریت Wenos Self خوش آمدید!", reply_markup=Panel)
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        async with lock:
            if Admin in temp_Client:
                del temp_Client[Admin]
    
    elif data.split("-")[0] == "DeleteSub":
        user_id = int(data.split("-")[1])
        await app.edit_message_text(Admin, m_id, "**هشدار! با این کار اشتراک کاربر مورد نظر به طور کامل حذف می شود و امکان فعالسازی دوباره از پنل مدیریت وجود ندارد\n\nاگر از این کار اطمینان دارید روی گزینه تایید و در غیر این صورت روی گزینه برگشت کلیک کنید**", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="تایید", callback_data=f"AcceptDelSub-{user_id}")
                ],
                [
                    InlineKeyboardButton(text="برگشت", callback_data="AdminBack")
                ]
            ]
        ))
    
    elif data.split("-")[0] == "AcceptDelSub":
        await app.edit_message_text(Admin, m_id, "اشتراک سلف کاربر مورد نظر به طور کامل حذف شد", reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="برگشت", callback_data="AdminBack")
                ]
            ]
        ))
        user_id = int(data.split("-")[1])
        if os.path.isdir(f"selfs/self-{user_id}"):
            shutil.rmtree(f"selfs/self-{user_id}")
        if os.path.isfile(f"sessions/{user_id}.session"):
            async with Client(f"sessions/{user_id}") as user_client:
                await user_client.log_out()
            if os.path.isfile(f"sessions/{user_id}.session"):
                os.remove(f"sessions/{user_id}.session")
        if os.path.isfile(f"sessions/{user_id}.session-journal"):
            os.remove(f"sessions/{user_id}.session-journal")
        update_data(f"UPDATE user SET expir = '0' WHERE id = '{user_id}'")
        update_data(f"UPDATE user SET self = 'inactive' WHERE id = '{user_id}'")
        update_data(f"UPDATE user SET pid = NULL WHERE id = '{user_id}'")
        await app.send_message(user_id, "کاربر گرامی اشتراک سلف شما توسط مدیر حذف شد\nبرای کسب اطلاعات بیشتر و دلیل حذف اشتراک به پشتیبانی مراجعه کنید")
    
    elif data == "AdminBack":
        await app.delete_messages(Admin, m_id)
        await app.send_message(Admin, "مدیر گرامی به پنل مدیریت Wenos Self خوش آمدید!", reply_markup=Panel)
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        async with lock:
            if Admin in temp_Client:
                del temp_Client[Admin]

@app.on_message(filters.private&filters.user(Admin), group=1)
async def update(c, m):
    bot = get_data("SELECT * FROM bot")
    user = get_data(f"SELECT * FROM user WHERE id = '{Admin}'")
    text = m.text
    m_id = m.id

    if text == "برگشت ↪️" or text == "🔙 برگشت":
        await app.send_message(Admin, """**╭─────────────────────────╮
│     👑 پنل مدیریت ارشد     │
│    🛠️ Self Admin    │
╰─────────────────────────╯

🎛️ به پنل مدیریت خوش آمدید!
🔐 دسترسی کامل به سیستم**""", reply_markup=Panel)
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        async with lock:
            if Admin in temp_Client:
                del temp_Client[Admin]

    elif text == "آمار 📊":
        mess = await app.send_message(Admin, "در حال دریافت اطلاعات...")
        botinfo = await app.get_me()
        allusers = get_datas("SELECT COUNT(id) FROM user")[0][0]
        allblocks = get_datas("SELECT COUNT(id) FROM block")[0][0]
        await app.edit_message_text(Admin, mess.id, f"""

تعداد کاربران ربات: {allusers}

تعداد کاربران بلاک شده: {allblocks}

--------------------------

نام ربات: {botinfo.first_name}

آیدی ربات: `{botinfo.id}`

یوزرنیم ربات: @{botinfo.username}

""")
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")

    elif text == "ارسال همگانی ✉️":
        await app.send_message(Admin, "پیام خود را ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'sendall' WHERE id = '{Admin}'")
    
    elif user["step"] == "sendall":
        mess = await app.send_message(Admin, "در حال ارسال به همه کاربران...")
        users = get_datas(f"SELECT id FROM user")
        for user in users:
            await app.copy_message(from_chat_id=Admin, chat_id=user[0], message_id=m_id)
            await asyncio.sleep(0.1)
        await app.edit_message_text(Admin, mess.id, "پیام شما برای همه کاربران ارسال شد")
    
    elif text == "فوروارد همگانی ✉️":
        await app.send_message(Admin, "پیام خود را ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'forall' WHERE id = '{Admin}'")
    
    elif user["step"] == "forall":
        mess = await app.send_message(Admin, "در حال فوروارد به همه کاربران...")
        users = get_datas(f"SELECT id FROM user")
        for user in users:
            await app.forward_messages(from_chat_id=Admin, chat_id=user[0], message_ids=m_id)
            await asyncio.sleep(0.1)
        await app.edit_message_text(Admin, mess.id, "پیام شما برای همه کاربران فوروارد شد")
    
    elif text == "بلاک کاربر 🚫":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید بلاک کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'userblock' WHERE id = '{Admin}'")
    
    elif user["step"] == "userblock":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                if get_data(f"SELECT * FROM block WHERE id = '{user_id}'") is None:
                    update_data(f"INSERT INTO block(id) VALUES({user_id})")
                    await app.send_message(Admin, "کاربر مورد نظر بلاک شد")
                    await app.send_message(user_id, "به دلیل نقض قوانین اکانت شما از ربات بلاک شد")
                    update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
                else:
                    await app.send_message(Admin, "این کاربر قبلا بلاک شده است")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif text == "آنبلاک کاربر ✅":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید آنبلاک کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'userunblock' WHERE id = '{Admin}'")
    
    elif user["step"] == "userunblock":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM block WHERE id = '{user_id}'") is not None:
                update_data(f"DELETE FROM block WHERE id = '{user_id}'")
                await app.send_message(Admin, "کاربر مورد نظر آنبلاک شد")
                await app.send_message(user_id, "اکانت شما از بلاک خارج شد")
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "این کاربر بلاک نیست")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif text == "افزودن موجودی 💰":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید به او موجودی اضافه کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'addamount1' WHERE id = '{Admin}'")
    
    elif user["step"] == "addamount1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                await app.send_message(Admin, "مقدار موجودی که می خواهید اضافه کنید را وارد کنید:", reply_markup=AdminBack)
                update_data(f"UPDATE user SET step = 'addamount2-{user_id}' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif user["step"].split("-")[0] == "addamount2":
        if text and text.isdigit():
            user_id = int(user["step"].split("-")[1])
            count = int(text.strip())
            user_amount = get_data(f"SELECT amount FROM user WHERE id = '{user_id}'")
            user_upamount = int(user_amount["amount"]) + count
            update_data(f"UPDATE user SET amount = '{user_upamount}' WHERE id = '{user_id}'")
            await app.send_message(Admin, f"موجودی کاربر {user_id} به میزان {count} تومان افزایش یافت\nموجودی جدید: {user_upamount} تومان")
            await app.send_message(user_id, f"موجودی حساب شما به میزان {count} تومان افزایش یافت\nموجودی جدید شما: {user_upamount} تومان")
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        else:
            await app.send_message(Admin, "ورودی نامعتبر است")
    
    elif text == "کسر موجودی 💸":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید از او موجودی کسر کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'remamount1' WHERE id = '{Admin}'")
    
    elif user["step"] == "remamount1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                await app.send_message(Admin, "مقدار موجودی که می خواهید کسر کنید را وارد کنید:", reply_markup=AdminBack)
                update_data(f"UPDATE user SET step = 'remamount2-{user_id}' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif user["step"].split("-")[0] == "remamount2":
        if text and text.isdigit():
            user_id = int(user["step"].split("-")[1])
            count = int(text.strip())
            user_amount = get_data(f"SELECT amount FROM user WHERE id = '{user_id}'")
            user_upamount = int(user_amount["amount"]) - count
            if user_upamount < 0:
                user_upamount = 0
            update_data(f"UPDATE user SET amount = '{user_upamount}' WHERE id = '{user_id}'")
            await app.send_message(Admin, f"از موجودی کاربر {user_id} به میزان {count} تومان کسر شد\nموجودی جدید: {user_upamount} تومان")
            await app.send_message(user_id, f"از موجودی حساب شما به میزان {count} تومان کسر شد\nموجودی جدید شما: {user_upamount} تومان")
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        else:
            await app.send_message(Admin, "ورودی نامعتبر است")
    
    elif text == "افزودن اشتراک ⏰":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید به او اشتراک اضافه کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'addexp1' WHERE id = '{Admin}'")
    
    elif user["step"] == "addexp1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                await app.send_message(Admin, "تعداد روزی که می خواهید اضافه کنید را وارد کنید:", reply_markup=AdminBack)
                update_data(f"UPDATE user SET step = 'addexp2-{user_id}' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif user["step"].split("-")[0] == "addexp2":
        if text and text.isdigit():
            user_id = int(user["step"].split("-")[1])
            count = int(text.strip())
            user_expir = get_data(f"SELECT expir FROM user WHERE id = '{user_id}'")
            user_upexpir = int(user_expir["expir"]) + count
            update_data(f"UPDATE user SET expir = '{user_upexpir}' WHERE id = '{user_id}'")
            await app.send_message(Admin, f"{count} روز به انقضای کاربر {user_id} افزوده شد\nانقضای جدید: {user_upexpir} روز")
            await app.send_message(user_id, f"{count} روز به انقضای اشتراک شما افزوده شد\nانقضای جدید شما: {user_upexpir} روز")
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        else:
            await app.send_message(Admin, "ورودی نامعتبر است")
    
    elif text == "کسر اشتراک ⏱️":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید از او اشتراک بکاهید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'remexp1' WHERE id = '{Admin}'")
    
    elif user["step"] == "remexp1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                await app.send_message(Admin, "تعداد روزی که می خواهید کسر کنید را وارد کنید:", reply_markup=AdminBack)
                update_data(f"UPDATE user SET step = 'remexp2-{user_id}' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif user["step"].split("-")[0] == "remexp2":
        if text and text.isdigit():
            user_id = int(user["step"].split("-")[1])
            count = int(text.strip())
            user_expir = get_data(f"SELECT expir FROM user WHERE id = '{user_id}'")
            user_upexpir = int(user_expir["expir"]) - count
            if user_upexpir < 0:
                user_upexpir = 0
            update_data(f"UPDATE user SET expir = '{user_upexpir}' WHERE id = '{user_id}'")
            await app.send_message(Admin, f"{count} روز از انقضای کاربر {user_id} کسر شد\nانقضای جدید: {user_upexpir} روز")
            await app.send_message(user_id, f"{count} روز از انقضای اشتراک شما کسر شد\nانقضای جدید شما: {user_upexpir} روز")
            update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
        else:
            await app.send_message(Admin, "ورودی نامعتبر است")
    
    elif text == "🟢 فعال کردن سلف":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید سلف او را فعال کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'actself1' WHERE id = '{Admin}'")
    
    elif user["step"] == "actself1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                await app.send_message(Admin, "درحال فعال کردن سلف برای کاربر ...", reply_markup=AdminBack)
                # Attempt to activate by creating folder and copying source
                if not os.path.isdir(f"selfs/self-{user_id}"):
                    os.mkdir(f"selfs/self-{user_id}")
                    try:
                        with zipfile.ZipFile("source/Self.zip", "r") as extract:
                            extract.extractall(f"selfs/self-{user_id}")
                    except Exception:
                        pass
                await app.send_message(user_id, "سلف برای شما فعال شد (توسط مدیر)")
                update_data(f"UPDATE user SET self = 'active' WHERE id = '{user_id}'")
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif text == "🔴 غیرفعال کردن سلف":
        await app.send_message(Admin, "آیدی عددی کاربری را که می خواهید سلف او را غیرفعال کنید ارسال کنید:", reply_markup=AdminBack)
        update_data(f"UPDATE user SET step = 'dactself1' WHERE id = '{Admin}'")
    
    elif user["step"] == "dactself1":
        if text and text.isdigit():
            user_id = int(text.strip())
            if get_data(f"SELECT * FROM user WHERE id = '{user_id}'") is not None:
                if os.path.isdir(f"selfs/self-{user_id}"):
                    shutil.rmtree(f"selfs/self-{user_id}")
                if os.path.isfile(f"sessions/{user_id}.session"):
                    async with Client(f"sessions/{user_id}") as user_client:
                        await user_client.log_out()
                    if os.path.isfile(f"sessions/{user_id}.session"):
                        os.remove(f"sessions/{user_id}.session")
                if os.path.isfile(f"sessions/{user_id}.session-journal"):
                    os.remove(f"sessions/{user_id}.session-journal")
                update_data(f"UPDATE user SET self = 'inactive' WHERE id = '{user_id}'")
                update_data(f"UPDATE user SET expir = '0' WHERE id = '{user_id}'")
                await app.send_message(Admin, "سلف کاربر غیرفعال شد")
                await app.send_message(user_id, "سلف شما توسط مدیر غیرفعال شد")
                update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
            else:
                await app.send_message(Admin, "چنین کاربری وجود ندارد")
        else:
            await app.send_message(Admin, "آیدی نامعتبر است")
    
    elif text == "🔵 روشن کردن ربات":
        update_data("UPDATE bot SET status = 'ON'")
        await app.send_message(Admin, "ربات روشن شد")
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
    
    elif text == "🔴 خاموش کردن ربات":
        update_data("UPDATE bot SET status = 'OFF'")
        await app.send_message(Admin, "ربات خاموش شد")
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")
    
    elif text == "🏠 صفحه اصلی":
        await app.send_message(Admin, "پنل مدیریتی", reply_markup=Panel)
        update_data(f"UPDATE user SET step = 'none' WHERE id = '{Admin}'")

# Keep the bot running
if __name__ == "__main__":
    try:
        print(Fore.GREEN + "[*] Bot Starting..." + Fore.RESET)
        app.run()
    except Exception as e:
        print(Fore.RED + "[!] Bot Crashed: " + str(e) + Fore.RESET)