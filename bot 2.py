import sys
import subprocess
import os
import asyncio
from threading import Thread
from flask import Flask

# 🌐 Render Free Web Service Keep-Alive Server
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "🤖 SMS Bomber Bot is Running 24/7 Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()

# 💥 Auto-install missing packages
needed_packages = ["pymongo", "dnspython", "requests", "python-telegram-bot", "certifi", "flask"]
for pkg in needed_packages:
    try:
        mod_name = "telegram" if pkg == "python-telegram-bot" else pkg
        __import__(mod_name)
    except ImportError:
        print(f"📦 Auto-installing missing module: {pkg}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except Exception as e:
            print(f"Failed to install {pkg}: {e}")

import logging
import requests
import json
import certifi
import ssl
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# ===================== CONFIGURATION =====================
TOKEN = "8706041204:AAGJ_C6N-UmRzpLUWbV2sCKhSxfHKoWTYG8"
ADMIN_ID = 7033711819
OWNER_USERNAME = "@Dipcb01"

# 🌐 Vercel WebApp URL
NETLIFY_MINI_APP_URL = "https://add-kz35.vercel.app/"

# 🍃 MongoDB Atlas Connection String
MONGO_URI = "mongodb+srv://pronoychkrbrt_db_user:hBJgqxOL15n2p8Wu@tg.b4f8v3a.mongodb.net/sms_bomber_bot?retryWrites=true&w=majority&appName=tg"

# 🎯 Points & Fee Settings
INITIAL_POINTS = 50       # Initial points for new users
POINT_PER_HIT = 2         # Points deducted per hit
DAILY_BONUS_POINTS = 20   # Daily bonus points
REFERRAL_POINTS = 15      # Referral bonus points
PROTECTION_COST = 100     # Number protection cost (points)
COOLDOWN_SECONDS = 30     # Cooldown time between bombing sessions (seconds)

# ===================== MONGODB CONNECTION =====================
memory_users = {}
memory_settings = {
    "api_url": "https://masterapi-sable.vercel.app/send?phone=",
    "channels": ["@hackxo"],
    "protected_numbers": ["01700000000", "01800000000"]
}
memory_promos = {}

custom_ssl_context = ssl.create_default_context()
custom_ssl_context.check_hostname = False
custom_ssl_context.verify_mode = ssl.CERT_NONE

db = None
users_col = None
settings_col = None
promos_col = None

try:
    mongo_client = MongoClient(
        MONGO_URI, 
        server_api=ServerApi('1'),
        ssl_context=custom_ssl_context,
        serverSelectionTimeoutMS=10000
    )
    db = mongo_client.get_database("sms_bomber_bot")
    users_col = db.get_collection("users")
    settings_col = db.get_collection("settings")
    promos_col = db.get_collection("promos")
    mongo_client.admin.command('ping')
    print("==================================================")
    print("🍃 MongoDB Atlas Connected Successfully!")
    print("==================================================")
except Exception as e:
    print(f"⚠️ MongoDB Atlas Warning: {e}. Using Hybrid Storage.")

# ===================== DATABASE HELPER FUNCTIONS =====================
def get_settings():
    try:
        if settings_col is not None:
            s = settings_col.find_one({"_id": "global_settings"})
            if s:
                memory_settings.update(s)
                return memory_settings
            else:
                settings_col.insert_one({"_id": "global_settings", **memory_settings})
    except Exception as e:
        print(f"Error getting settings: {e}")
    return memory_settings

def update_settings(fields):
    memory_settings.update(fields)
    try:
        if settings_col is not None:
            settings_col.update_one({"_id": "global_settings"}, {"$set": fields}, upsert=True)
    except Exception as e:
        print(f"Error updating settings: {e}")

def init_user(user_id, username="N/A", first_name="User"):
    # Try loading from MongoDB first
    try:
        if users_col is not None:
            u = users_col.find_one({"user_id": user_id})
            if u:
                memory_users[user_id] = u
                if username and username != "N/A": memory_users[user_id]["username"] = username
                if first_name: memory_users[user_id]["first_name"] = first_name
                return memory_users[user_id]
    except Exception as e:
        print(f"MongoDB Fetch Error: {e}")

    if user_id not in memory_users:
        memory_users[user_id] = {
            "user_id": user_id,
            "username": username if username else "N/A",
            "first_name": first_name if first_name else "User",
            "points": INITIAL_POINTS,
            "is_vip": False,
            "vip_expiry": None,
            "last_daily": None,
            "last_bombing": None,
            "referred_by": None,
            "referral_count": 0,
            "total_bombing": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_requests": 0
        }
    else:
        if username and username != "N/A": memory_users[user_id]["username"] = username
        if first_name: memory_users[user_id]["first_name"] = first_name

    try:
        if users_col is not None:
            save_doc = {
                "user_id": user_id,
                "username": memory_users[user_id]["username"],
                "first_name": memory_users[user_id]["first_name"],
                "points": memory_users[user_id]["points"],
                "is_vip": memory_users[user_id]["is_vip"],
                "vip_expiry": memory_users[user_id]["vip_expiry"],
                "last_daily": memory_users[user_id]["last_daily"],
                "last_bombing": memory_users[user_id]["last_bombing"],
                "referred_by": memory_users[user_id]["referred_by"],
                "referral_count": memory_users[user_id]["referral_count"],
                "total_bombing": memory_users[user_id]["total_bombing"],
                "total_success": memory_users[user_id]["total_success"],
                "total_failed": memory_users[user_id]["total_failed"],
                "total_requests": memory_users[user_id]["total_requests"]
            }
            users_col.update_one({"user_id": user_id}, {"$set": save_doc}, upsert=True)
    except Exception as e:
        print(f"MongoDB Sync Error: {e}")

    return memory_users[user_id]

def check_vip_status(user_id):
    u = init_user(user_id)
    if u.get("is_vip") and u.get("vip_expiry"):
        exp = u["vip_expiry"]
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        if datetime.now() > exp:
            u["is_vip"] = False
            u["vip_expiry"] = None
            try:
                if users_col is not None:
                    users_col.update_one({"user_id": user_id}, {"$set": {"is_vip": False, "vip_expiry": None}})
            except Exception: pass
            return False
        return True
    return u.get("is_vip", False)

# 🎯 Robust SMS Count Extractor (Sums total_sent & total_failed from each hit)
def extract_sms_counts(data_obj):
    if isinstance(data_obj, str):
        try:
            data_obj = json.loads(data_obj)
        except Exception:
            return 1, 0

    if isinstance(data_obj, dict):
        sent = 0
        for k in ["total_sent", "sent", "total_success", "success", "success_sms", "successful"]:
            if k in data_obj and data_obj[k] is not None:
                try:
                    v = data_obj[k]
                    sent = 1 if isinstance(v, bool) and v else int(v)
                    break
                except (ValueError, TypeError):
                    pass

        failed = 0
        for k in ["total_failed", "failed", "total_failure", "failure", "fail_sms"]:
            if k in data_obj and data_obj[k] is not None:
                try:
                    v = data_obj[k]
                    failed = 1 if isinstance(v, bool) and v else int(v)
                    break
                except (ValueError, TypeError):
                    pass

        if sent == 0 and failed == 0 and data_obj.get("success") is True:
            sent = 1

        return sent, failed

    return 1, 0

temp_data = {}
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== HELPERS =====================
def is_admin(user_id): return user_id == ADMIN_ID

async def get_unjoined_channels(user_id, context):
    st = get_settings()
    unjoined = []
    for ch in st.get('channels', ["@hackxo"]):
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unjoined.append(ch)
        except Exception:
            unjoined.append(ch)
    return unjoined

# ===================== KEYBOARDS =====================
def get_main_keyboard(user_id):
    keyboard = [
        ["🚀 START BOMBER"],
        ["💰 EARN POINTS", "🎁 DAILY BONUS"],
        ["👥 REFER & EARN", "🏆 LEADERBOARD"],
        ["🎟 REDEEM CODE", "🛡️ PROTECT NUMBER"],
        ["📊 MY INFO", "📞 CONTACT ADMIN"]
    ]
    if is_admin(user_id): keyboard.append(["⚙️ ADMIN PANEL"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard(): return ReplyKeyboardMarkup([["🔙 ব্যাক"]], resize_keyboard=True)

# ===================== MAIN MENU =====================
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    u = init_user(user.id, user.username, user.first_name)
    if user.id in temp_data: del temp_data[user.id]
    
    is_vip = check_vip_status(user.id)
    status_badge = "👑 VIP MEMBER" if is_vip else f"💰 {u.get('points', INITIAL_POINTS)} Points"
    
    await update.message.reply_text(
        f"🔥 <b>WELCOME TO SMS BOMBER BOT</b> 🔥\n\n"
        f"👤 <b>ইউজার:</b> {user.first_name}\n"
        f"🆔 <b>আইডি:</b> <code>{user.id}</code>\n"
        f"🔰 <b>স্ট্যাটাস:</b> <b>{status_badge}</b>\n\n"
        f"📌 <i>নিচের বাটন থেকে আপনার কাঙ্ক্ষিত অপশন সিলেক্ট করুন:</i>",
        parse_mode="HTML", reply_markup=get_main_keyboard(user.id)
    )

async def send_join_prompt(update: Update, unjoined_channels, is_error=False):
    keyboard = []
    for ch in unjoined_channels:
        keyboard.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@', '')}")])
    keyboard.append([InlineKeyboardButton("✅ চেক করুন", callback_data='check_join')])
    
    prefix = "❌ <b>আপনি এখনও সব চ্যানেলে জয়েন করেননি!</b>\n\n" if is_error else "⚠️ <b>বট ব্যবহার করতে নিচের চ্যানেলগুলোতে জয়েন করুন:</b>\n\n"
    
    msg_text = prefix
    for ch in unjoined_channels:
        msg_text += f"🔗 <b>{ch}</b>\n"
    msg_text += "\n📌 <i>সবগুলোতে জয়েন করার পর <b>'✅ চেক করুন'</b> বাটনে ক্লিক করুন।</i>"
    
    if update.message:
        await update.message.reply_text(msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await update.callback_query.message.reply_text(msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ===================== START & AUTO CLAIM =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    u = init_user(user.id, user.username, user.first_name)
    
    # 💥 Auto Point Claim from Mini App Deep Link
    if context.args and context.args[0].lower() == 'claim20pts':
        pts = 20
        u['points'] += pts
        try:
            if users_col is not None:
                users_col.update_one({"user_id": user.id}, {"$inc": {"points": pts}}, upsert=True)
        except Exception as e:
            print(f"Claim update error: {e}")

        await update.message.reply_text(
            f"🎉 <b>এড দেখা সফল হয়েছে!</b>\n\n"
            f"➕ আপনার অ্যাকাউন্টে <b>+{pts} Points</b> যোগ করা হয়েছে!\n"
            f"💰 বর্তমান ব্যালেন্স: <b>{u['points']} Points</b>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(user.id)
        )
        return

    # Referral Check
    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])
        if ref_id != user.id and u.get('referred_by') is None:
            u['referred_by'] = ref_id
            init_user(ref_id)
            if ref_id in memory_users:
                memory_users[ref_id]['points'] += REFERRAL_POINTS
                memory_users[ref_id]['referral_count'] += 1
            try:
                if users_col is not None:
                    users_col.update_one({"user_id": user.id}, {"$set": {"referred_by": ref_id}}, upsert=True)
                    users_col.update_one({"user_id": ref_id}, {"$inc": {"points": REFERRAL_POINTS, "referral_count": 1}}, upsert=True)
                await context.bot.send_message(ref_id, f"🎉 <b>নতুন রেফারেল বোনাস!</b>\n➕ পেয়েছেন: <b>+{REFERRAL_POINTS} Points</b>", parse_mode="HTML")
            except Exception: pass

    unjoined = await get_unjoined_channels(user.id, context)
    if not unjoined: await main_menu(update, context)
    else: await send_join_prompt(update, unjoined)

# ===================== CALLBACKS =====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if not user: return
    user_id = user.id
    init_user(user_id, user.username, user.first_name)
    
    if query.data == 'check_join':
        unjoined = await get_unjoined_channels(user_id, context)
        if not unjoined:
            try: await query.message.delete()
            except Exception: pass
            await update.effective_chat.send_message("🎉 <b>জয়েনিং সফল হয়েছে!</b>", parse_mode="HTML")
            await main_menu(update, context)
        else:
            await send_join_prompt(update, unjoined, is_error=True)

    # 🛑 Bombing Cancel Button
    elif query.data.startswith('cancel_bombing_'):
        target_uid = int(query.data.split('_')[2])
        if user_id == target_uid or is_admin(user_id):
            if target_uid in temp_data:
                temp_data[target_uid]['cancel'] = True
                await query.answer("🛑 বোম্বিং বাতিল করা হচ্ছে...", show_alert=True)
        else:
            await query.answer("❌ আপনি এই বোম্বিং বাতিল করতে পারবেন না!", show_alert=True)

# ===================== ADMIN COMMANDS =====================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    
    all_u_dict = dict(memory_users)
    try:
        if users_col is not None:
            for u_doc in users_col.find().limit(50):
                uid = u_doc.get("user_id")
                if uid: all_u_dict[uid] = u_doc
    except Exception: pass
    
    count = len(all_u_dict)
    text = f"👥 <b>ইউজার লিস্ট (মোট ইউজার: {count})</b>\n\n"
    if count == 0:
        text += "<i>কোনো ইউজার ডাটা পাওয়া যায়নি।</i>"
    else:
        for u_id, u_info in list(all_u_dict.items())[:30]:
            vip_str = "👑 VIP" if check_vip_status(u_id) else "👤 Free"
            text += f"• <code>{u_id}</code> | @{u_info.get('username','N/A')} | 💰 {u_info.get('points',0)} Pts | {vip_str}\n"
    
    await update.message.reply_text(text, parse_mode="HTML")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("❌ ব্যবহার: <code>/broadcast মেসেজ...</code>", parse_mode="HTML")
    
    msg_to_send = " ".join(context.args)
    s, f = 0, 0
    msg = await update.message.reply_text("⏳ ব্রডকাস্ট চলছে...")
    target_ids = list(memory_users.keys())
    for u_id in target_ids:
        try:
            await context.bot.send_message(u_id, f"📢 <b>ADMIN NOTICE</b>\n\n{msg_to_send}", parse_mode="HTML")
            s += 1
        except Exception: f += 1
        await asyncio.sleep(0.04)
    await msg.edit_text(f"✅ <b>ব্রডকাস্ট সম্পন্ন!</b>\n\n🟢 সফল: {s}\n🔴 ব্যর্থ: {f}")

async def admin_makecode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        code, pts, uses, days = context.args[0].upper(), int(context.args[1]), int(context.args[2]), int(context.args[3])
        exp_date = datetime.now() + timedelta(days=days)
        memory_promos[code] = {"code": code, "points": pts, "uses": uses, "used_by": [], "expires_at": exp_date}
        if promos_col is not None:
            promos_col.update_one({"code": code}, {"$set": memory_promos[code]}, upsert=True)
        await update.message.reply_text(f"✅ <b>রিডিম কোড তৈরি হয়েছে!</b>\n🎟 <code>{code}</code> | 💰 {pts} Pts | 👥 {uses} Usages", parse_mode="HTML")
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/makecode CODE PTS USES DAYS</code>", parse_mode="HTML")

async def admin_addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        target_id, pts = int(context.args[0]), int(context.args[1])
        u = init_user(target_id)
        u['points'] += pts
        if users_col is not None:
            users_col.update_one({"user_id": target_id}, {"$inc": {"points": pts}}, upsert=True)
            
        await update.message.reply_text(f"✅ ইউজার <code>{target_id}</code> কে <b>+{pts} Points</b> দেওয়া হয়েছে!", parse_mode="HTML")
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎉 <b>অভিনন্দন!</b>\n\nঅ্যাডমিন আপনাকে <b>+{pts} Points</b> প্রদান করেছে!\n💰 বর্তমান ব্যালেন্স: <b>{u['points']} Points</b>",
                parse_mode="HTML"
            )
        except Exception: pass
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/addpoints USER_ID PTS</code>", parse_mode="HTML")

async def admin_addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        target_id, days = int(context.args[0]), int(context.args[1])
        u = init_user(target_id)
        exp = datetime.now() + timedelta(days=days)
        u['is_vip'] = True
        u['vip_expiry'] = exp
        if users_col is not None:
            users_col.update_one({"user_id": target_id}, {"$set": {"is_vip": True, "vip_expiry": exp}}, upsert=True)
            
        await update.message.reply_text(f"👑 ইউজার <code>{target_id}</code> কে <b>{days} দিনের VIP Access</b> দেওয়া হয়েছে!", parse_mode="HTML")
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"👑 <b>VIP ACCESS ACTIVATED!</b>\n\nঅ্যাডমিন আপনাকে <b>{days} দিনের জন্য VIP Access</b> প্রদান করেছেন!\n✨ এখন থেকে কোনো পয়েন্ট বা এড ছাড়া আনলিমিটেড ফ্রি বোম্বিং উপভোগ করুন।",
                parse_mode="HTML"
            )
        except Exception: pass
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/addvip USER_ID DAYS</code>", parse_mode="HTML")

async def admin_removevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("❌ ব্যবহার: <code>/removevip USER_ID</code>", parse_mode="HTML")
        return
    try:
        target_id = int(context.args[0])
        u = init_user(target_id)
        u['is_vip'] = False
        u['vip_expiry'] = None
        if users_col is not None:
            users_col.update_one({"user_id": target_id}, {"$set": {"is_vip": False, "vip_expiry": None}}, upsert=True)
        
        await update.message.reply_text(f"🚫 <b>ইউজার <code>{target_id}</code> এর VIP সুবিধা সফলভাবে রিমুভ করা হয়েছে!</b>", parse_mode="HTML")
        try:
            await context.bot.send_message(
                chat_id=target_id, 
                text="🚫 <b>আপনার VIP মেম্বারশিপ মেয়াদ শেষ বা বাতিল করা হয়েছে।</b>", 
                parse_mode="HTML"
            )
        except Exception: pass
    except Exception:
        await update.message.reply_text("❌ ব্যবহার: <code>/removevip USER_ID</code>", parse_mode="HTML")

async def admin_protectnumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        num = context.args[0].strip()
        st = get_settings()
        if num not in st.get('protected_numbers', []):
            st.setdefault('protected_numbers', []).append(num)
            if settings_col is not None:
                settings_col.update_one({"_id": "global_settings"}, {"$push": {"protected_numbers": num}}, upsert=True)
            await update.message.reply_text(f"🛡️ নম্বর <code>{num}</code> প্রটেক্টেড তালিকায় যোগ করা হয়েছে!", parse_mode="HTML")
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/protectnumber 018XXXXXXXX</code>", parse_mode="HTML")

async def admin_unprotectnumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        num = context.args[0].strip()
        st = get_settings()
        if num in st.get('protected_numbers', []):
            st['protected_numbers'].remove(num)
            if settings_col is not None:
                settings_col.update_one({"_id": "global_settings"}, {"$pull": {"protected_numbers": num}}, upsert=True)
        await update.message.reply_text(f"🗑 নম্বর <code>{num}</code> সরানো হয়েছে।", parse_mode="HTML")
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/unprotectnumber 018XXXXXXXX</code>", parse_mode="HTML")

async def admin_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        ch = context.args[0] if context.args[0].startswith('@') else '@' + context.args[0]
        st = get_settings()
        if ch not in st.get('channels', []):
            st.setdefault('channels', []).append(ch)
            if settings_col is not None:
                settings_col.update_one({"_id": "global_settings"}, {"$addToSet": {"channels": ch}}, upsert=True)
        await update.message.reply_text(f"✅ চ্যানেল <code>{ch}</code> যোগ হয়েছে।", parse_mode="HTML")
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/addchannel @channel</code>", parse_mode="HTML")

async def admin_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        ch = context.args[0] if context.args[0].startswith('@') else '@' + context.args[0]
        st = get_settings()
        if ch in st.get('channels', []):
            st['channels'].remove(ch)
            if settings_col is not None:
                settings_col.update_one({"_id": "global_settings"}, {"$pull": {"channels": ch}}, upsert=True)
        await update.message.reply_text(f"🗑 চ্যানেল <code>{ch}</code> রিমুভ হয়েছে।", parse_mode="HTML")
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/removechannel @channel</code>", parse_mode="HTML")

async def admin_setapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        new_api = context.args[0]
        update_settings({"api_url": new_api})
        await update.message.reply_text("🌐 <b>API URL চেঞ্জ হয়েছে!</b>", parse_mode="HTML")
    except Exception: await update.message.reply_text("❌ ব্যবহার: <code>/setapi URL</code>", parse_mode="HTML")

async def admin_botstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    try:
        st = get_settings()
        total_u = len(memory_users)
        vips = sum(1 for u in memory_users.values() if u.get('is_vip'))
        total_pts = sum(u.get('points', 0) for u in memory_users.values())
        
        if users_col is not None:
            try:
                total_u = users_col.count_documents({})
                vips = users_col.count_documents({"is_vip": True})
                pipeline = [{"$group": {"_id": None, "total": {"$sum": "$points"}}}]
                res = list(users_col.aggregate(pipeline))
                if res: total_pts = res[0]["total"]
            except Exception: pass
            
        channels_str = ", ".join(st.get('channels', [])) if st.get('channels') else 'None'
        
        await update.message.reply_text(
            f"📊 <b>SYSTEM STATS</b> 📊\n\n👥 মোট ইউজার: <b>{total_u}</b>\n👑 VIP ইউজার: <b>{vips}</b>\n💰 মোট পয়েন্ট: <b>{total_pts}</b>\n🛡️ প্রটেক্টেড নম্বর: <b>{len(st.get('protected_numbers', []))}টি</b>\n📢 চ্যানেল: {channels_str}\n🌐 বর্তমান API: <code>{st.get('api_url', 'Default')}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ এরর: <code>{e}</code>", parse_mode="HTML")

async def admin_panel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id): return
    await update.message.reply_text(
        "⚙️ <b>ADMIN CONTROL PANEL</b> ⚙️\n\n"
        "<code>/users</code> - ইউজার লিস্ট\n"
        "<code>/broadcast &lt;msg&gt;</code> - ব্রডকাস্ট\n"
        "<code>/makecode CODE PTS USES DAYS</code> - রিডিম কোড\n"
        "<code>/addpoints ID PTS</code> - পয়েন্ট দেওয়া\n"
        "<code>/addvip ID DAYS</code> - VIP করা\n"
        "<code>/removevip ID</code> - VIP বাতিল\n"
        "<code>/protectnumber NUM</code> - নম্বর প্রটেক্ট\n"
        "<code>/unprotectnumber NUM</code> - প্রটেক্ট বাতিল\n"
        "<code>/addchannel @ch</code> - চ্যানেল যোগ\n"
        "<code>/removechannel @ch</code> - চ্যানেল বাতিল\n"
        "<code>/setapi URL</code> - API চেঞ্জ\n"
        "<code>/botstats</code> - ওভারঅল স্ট্যাটস",
        parse_mode="HTML"
    )

# ===================== MESSAGE HANDLERS =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message or not update.message.text:
        return
        
    user = update.effective_user
    user_id = user.id
    message = update.message.text
    u = init_user(user_id, user.username, user.first_name)
    
    unjoined = await get_unjoined_channels(user_id, context)
    if unjoined:
        await send_join_prompt(update, unjoined)
        return
    
    # ===== START BOMBER =====
    if message == "🚀 START BOMBER":
        is_vip = check_vip_status(user_id)
        
        last_b = u.get('last_bombing')
        if not is_vip and last_b:
            time_passed = (datetime.now() - last_b).seconds
            if time_passed < COOLDOWN_SECONDS:
                await update.message.reply_text(f"⏳ <b>স্প্যাম রোধে অপেক্ষা করুন!</b>\n\nআবার বোম্বিং করতে পারবেন: <b>{COOLDOWN_SECONDS - time_passed} সেকেন্ড</b> পর।\n👑 <i>VIP মেম্বারদের ওয়েটিং টাইম নেই!</i>", parse_mode="HTML")
                return

        if not is_vip and u.get('points', 0) < POINT_PER_HIT:
            await update.message.reply_text(f"❌ <b>পর্যাপ্ত পয়েন্ট নেই!</b>\n💰 ব্যালেন্স: <b>{u.get('points', 0)} Points</b>\n👉 '💰 EARN POINTS' থেকে ফ্রি পয়েন্ট নিন!", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
            return

        temp_data[user_id] = {'step': 'awaiting_number', 'cancel': False}
        await update.message.reply_text("📱 <b>START BOMBER</b>\n\nদয়া করে টার্গেট নম্বর দিন:\nউদাহরণ: <code>018XXXXXXXX</code>", parse_mode="HTML", reply_markup=get_back_keyboard())
        return

    # ===== EARN POINTS =====
    elif message == "💰 EARN POINTS":
        is_vip = check_vip_status(user_id)
        keyboard = [[InlineKeyboardButton("⚡ WATCH ADS & EARN POINTS ⚡", web_app=WebAppInfo(url=NETLIFY_MINI_APP_URL))]]
        status_text = "👑 আপনি VIP Member! পয়েন্ট লাগবে না।" if is_vip else f"💰 ব্যালেন্স: <b>{u.get('points', 0)} Points</b>"
        await update.message.reply_text(f"🎁 <b>EARN FREE POINTS</b> 🎁\n\n🔰 {status_text}\n\n▶ 'WATCH ADS' চেপে এড দেখে ফ্রি পয়েন্ট ক্লেইম করুন!", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ===== REFER & EARN =====
    elif message == "👥 REFER & EARN":
        ref_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(
            f"👥 <b>REFER & EARN</b> 👥\n\n🎉 প্রতি রেফারে পাবেন: <b>+{REFERRAL_POINTS} Points</b>!\n\n👥 মোট রেফার: <b>{u.get('referral_count',0)} জন</b>\n💰 রেফার ইনকাম: <b>{u.get('referral_count',0) * REFERRAL_POINTS} Points</b>\n\n🔗 রেফার লিংক:\n<code>{ref_link}</code>",
            parse_mode="HTML", reply_markup=get_main_keyboard(user_id)
        )
        return

    # ===== LEADERBOARD =====
    elif message == "🏆 LEADERBOARD":
        sorted_users = sorted(memory_users.values(), key=lambda x: x.get('points', 0), reverse=True)[:10]
        text = "🏆 <b>TOP 10 LEADERBOARD</b> 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for idx, u_info in enumerate(sorted_users):
            m_icon = medals[idx] if idx < len(medals) else "👤"
            text += f"{m_icon} <b>{u_info.get('first_name', 'User')}</b> - <code>{u_info.get('points', 0)} Points</code>\n"
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
        return

    # ===== DAILY BONUS =====
    elif message == "🎁 DAILY BONUS":
        last_daily = u.get('last_daily')
        now = datetime.now()
        if last_daily and (now - last_daily) < timedelta(hours=24):
            rem = timedelta(hours=24) - (now - last_daily)
            h, r = divmod(rem.seconds, 3600)
            await update.message.reply_text(f"⏳ আজ বোনাস নিয়েছেন! অপেক্ষা করুন: <b>{h} ঘণ্টা {divmod(r, 60)[0]} মিনিট</b>।", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
        else:
            u['points'] += DAILY_BONUS_POINTS
            u['last_daily'] = now
            try:
                if users_col is not None:
                    users_col.update_one({"user_id": user_id}, {"$inc": {"points": DAILY_BONUS_POINTS}, "$set": {"last_daily": now}}, upsert=True)
            except Exception: pass
            await update.message.reply_text(f"🎉 <b>ডেইলি বোনাস সফল!</b>\n➕ পেয়েছেন: <b>+{DAILY_BONUS_POINTS} Points</b>\n💰 নতুন ব্যালেন্স: <b>{u.get('points', 0)} Points</b>", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
        return

    # ===== NUMBER PROTECTION =====
    elif message == "🛡️ PROTECT NUMBER":
        temp_data[user_id] = {'step': 'awaiting_protection_num'}
        await update.message.reply_text(f"🛡️ <b>NUMBER PROTECTION</b> 🛡️\n\nনম্বর প্রটেক্ট করতে ফি: <b>{PROTECTION_COST} Points</b>\n\nআপনার ১১ ডিজিটের নম্বর লিখুন:", parse_mode="HTML", reply_markup=get_back_keyboard())
        return

    # ===== REDEEM CODE =====
    elif message == "🎟 REDEEM CODE":
        temp_data[user_id] = {'step': 'awaiting_code'}
        await update.message.reply_text("🎟 <b>REDEEM CODE</b>\n\nআপনার প্রাপ্ত কোডটি লিখুন:", parse_mode="HTML", reply_markup=get_back_keyboard())
        return

    # ===== MY INFO =====
    elif message == "📊 MY INFO":
        is_vip = check_vip_status(user_id)
        vip_text = "👑 <b>VIP MEMBER</b>" if is_vip else "👤 <b>FREE USER</b>"
        info_text = (
            f"📊 <b>আমার প্রোফাইল</b> 📊\n\n🆔 আইডি: <code>{user.id}</code>\n👤 নাম: {user.first_name}\n🔰 মেম্বারশিপ: {vip_text}\n💰 পয়েন্ট: <b>{u.get('points',0)} Points</b>\n\n👥 রেফার: <b>{u.get('referral_count',0)} জন</b>\n💣 বোম্বিং সেশন: {u.get('total_bombing',0)}\n✅ সফল SMS: {u.get('total_success',0)}\n❌ ব্যর্থ SMS: {u.get('total_failed',0)}"
        )
        await update.message.reply_text(info_text, parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
        return

    # ===== CONTACT ADMIN =====
    elif message == "📞 CONTACT ADMIN":
        await update.message.reply_text(f"📞 <b>কন্ট্যাক্ট অ্যাডমিন</b>\n\n👨‍💻 অ্যাডমিন: {OWNER_USERNAME}\n🔗 কন্ট্যাক্ট: https://t.me/{OWNER_USERNAME.replace('@', '')}", reply_markup=get_main_keyboard(user_id))
        return

    # ===== ADMIN PANEL BUTTON =====
    elif message == "⚙️ ADMIN PANEL" and is_admin(user_id):
        await admin_panel_menu(update, context)
        return

    # ===== BACK BUTTON =====
    elif message == "🔙 ব্যাক":
        await main_menu(update, context)
        return

    if user_id not in temp_data:
        await main_menu(update, context)
        return

    step = temp_data[user_id].get('step')

    # ===== PROTECTION PROCESS =====
    if step == 'awaiting_protection_num':
        num = message.strip()
        if not num.isdigit() or len(num) != 11 or not num.startswith("01"):
            await update.message.reply_text("❌ <b>ভুল নম্বর!</b> ১১ ডিজিটের বাংলাদেশি নম্বর দিন। (যেমন: 018XXXXXXXX)", parse_mode="HTML", reply_markup=get_back_keyboard())
            return
        
        is_vip = check_vip_status(user_id)
        if not is_vip and u.get('points', 0) < PROTECTION_COST:
            await update.message.reply_text(f"❌ প্রটেকশনের জন্য <b>{PROTECTION_COST} Points</b> লাগবে।", reply_markup=get_main_keyboard(user_id))
            del temp_data[user_id]
            return
        
        st = get_settings()
        if num not in st.get('protected_numbers', []):
            st.setdefault('protected_numbers', []).append(num)
            if not is_vip:
                u['points'] -= PROTECTION_COST
                try:
                    if users_col is not None: users_col.update_one({"user_id": user_id}, {"$inc": {"points": -PROTECTION_COST}}, upsert=True)
                except Exception: pass
            try:
                if settings_col is not None: settings_col.update_one({"_id": "global_settings"}, {"$push": {"protected_numbers": num}}, upsert=True)
            except Exception: pass
            await update.message.reply_text(f"🛡️ <b>অভিনন্দন!</b>\nনম্বর <code>{num}</code> প্রটেক্টেড করা হয়েছে!", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
        else: await update.message.reply_text("⚠️ নম্বরটি আগেই প্রটেক্টেড আছে।", reply_markup=get_main_keyboard(user_id))
        del temp_data[user_id]
        return

    # ===== REDEEM CODE PROCESS =====
    if step == 'awaiting_code':
        code = message.strip().upper()
        p_data = memory_promos.get(code)
        if not p_data and promos_col is not None:
            try: p_data = promos_col.find_one({"code": code})
            except Exception: pass
            
        if p_data:
            if datetime.now() > p_data['expires_at']: await update.message.reply_text("❌ রিডিম কোডের মেয়াদ শেষ!", reply_markup=get_main_keyboard(user_id))
            elif user_id in p_data.get('used_by', []): await update.message.reply_text("❌ আগেই রিডিম করেছেন!", reply_markup=get_main_keyboard(user_id))
            elif p_data.get('uses', 0) <= 0: await update.message.reply_text("❌ লিমিট শেষ!", reply_markup=get_main_keyboard(user_id))
            else:
                p_data['uses'] -= 1
                p_data.setdefault('used_by', []).append(user_id)
                u['points'] += p_data['points']
                try:
                    if promos_col is not None: promos_col.update_one({"code": code}, {"$inc": {"uses": -1}, "$push": {"used_by": user_id}}, upsert=True)
                    if users_col is not None: users_col.update_one({"user_id": user_id}, {"$inc": {"points": p_data['points']}}, upsert=True)
                except Exception: pass
                await update.message.reply_text(f"🎉 <b>কোড রিডিম সফল!</b>\n➕ পেয়েছেন: <b>+{p_data['points']} Points</b>\n💰 নতুন ব্যালেন্স: <b>{u.get('points', 0)} Points</b>", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
        else: await update.message.reply_text("❌ অবৈধ কোড!", reply_markup=get_main_keyboard(user_id))
        del temp_data[user_id]
        return

    # ===== NUMBER INPUT =====
    if step == 'awaiting_number':
        num = message.strip()
        if not num.isdigit() or len(num) != 11 or not num.startswith("01"):
            await update.message.reply_text("❌ <b>ভুল নম্বর!</b> সঠিক ১১ ডিজিটের নম্বর দিন। (যেমন: 018XXXXXXXX)", parse_mode="HTML", reply_markup=get_back_keyboard())
            return
        
        st = get_settings()
        if num in st.get('protected_numbers', []):
            await update.message.reply_text(f"🛡️ <b>নম্বর প্রটেক্টেড!</b>\nনম্বর <code>{num}</code> প্রটেক্টেড রয়েছে, বোম্বিং সম্ভব নয়!", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))
            del temp_data[user_id]
            return
        
        temp_data[user_id]['number'] = num
        temp_data[user_id]['step'] = 'awaiting_amount'
        is_vip = check_vip_status(user_id)
        limit_info = "👑 আপনি <b>VIP User</b>! ফ্রিতে ২০ বার হিট করতে পারবেন।" if is_vip else f"📌 আপনার পয়েন্ট দিয়ে সর্বোচ্চ <b>{min(u.get('points', 0) // POINT_PER_HIT, 20)} বার</b> হিট সম্ভব।"
        await update.message.reply_text(f"✅ নম্বর সেট: <code>{num}</code>\n\n💥 কত বার (হিট) বোম্বিং করবেন?\n{limit_info}", parse_mode="HTML", reply_markup=get_back_keyboard())
        return

    # ===== BOMBING & PROGRESS BAR PROCESS =====
    elif step == 'awaiting_amount':
        try:
            amount = int(message)
            is_vip = check_vip_status(user_id)
            cost = 0 if is_vip else amount * POINT_PER_HIT
            
            if amount < 1 or amount > 20:
                await update.message.reply_text("❌ ১-২০ এর মধ্যে হিট দিন!", reply_markup=get_back_keyboard())
                return
            
            if not is_vip and u.get('points', 0) < cost:
                await update.message.reply_text(f"❌ {amount} হিটের জন্য {cost} পয়েন্ট লাগবে।", reply_markup=get_back_keyboard())
                return

            number = temp_data[user_id]['number']
            if not is_vip:
                u['points'] -= cost
                try:
                    if users_col is not None: users_col.update_one({"user_id": user_id}, {"$inc": {"points": -cost}}, upsert=True)
                except Exception: pass
                
            u['last_bombing'] = datetime.now()
            temp_data[user_id]['cancel'] = False
            
            try:
                if users_col is not None: users_col.update_one({"user_id": user_id}, {"$set": {"last_bombing": datetime.now()}}, upsert=True)
            except Exception: pass
            
            # 🛑 Cancel Bombing Button
            cancel_kbd = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 CANCEL BOMBING", callback_data=f"cancel_bombing_{user_id}")]])
            msg = await update.message.reply_text(f"💣 <b>BOMBING IN PROGRESS...</b>\n\n📱 টার্গেট: <code>{number}</code>\n💥 হিট: {amount} বার", parse_mode="HTML", reply_markup=cancel_kbd)
            
            total_sent_count = 0
            total_failed_count = 0
            last_response = {}
            st = get_settings()
            current_api = st.get('api_url', "https://masterapi-sable.vercel.app/send?phone=")
            
            spinners = ["⏳", "⌛", "⚡", "💥"]
            loop = asyncio.get_event_loop()
            
            for i in range(amount):
                # 🛑 Cancel Check
                if temp_data.get(user_id, {}).get('cancel', False):
                    await msg.edit_text(
                        f"🛑 <b>বোম্বিং মাঝপথে বাতিল করা হয়েছে!</b>\n\n"
                        f"📱 টার্গেট: <code>{number}</code>\n"
                        f"💥 সম্পন্ন হিট: <b>{i}/{amount}</b>\n"
                        f"✅ সফল SMS: <b>{total_sent_count}</b>\n"
                        f"❌ ব্যর্থ SMS: <b>{total_failed_count}</b>",
                        parse_mode="HTML"
                    )
                    break

                try:
                    # 💥 Non-blocking Async Request
                    api_response = await loop.run_in_executor(
                        None, 
                        lambda: requests.get(f"{current_api}{number}", timeout=15)
                    )
                    if api_response.status_code == 200:
                        response_data = api_response.json()
                        if isinstance(response_data, str): response_data = json.loads(response_data)
                        if isinstance(response_data, dict):
                            last_response = response_data
                            sent, failed = extract_sms_counts(response_data)
                            total_sent_count += sent
                            total_failed_count += failed
                        else:
                            total_sent_count += 1
                    else:
                        total_failed_count += 1
                except Exception as e:
                    total_failed_count += 1
                    print(f"Error hit {i+1}: {e}")
                
                percent = int(((i + 1) / amount) * 100)
                filled = int(10 * (i + 1) // amount)
                bar = '▰' * filled + '▱' * (10 - filled)
                sp = spinners[i % len(spinners)]
                
                try:
                    await msg.edit_text(
                        f"💣 <b>BOMBING IN PROGRESS...</b> {sp}\n\n"
                        f"📱 টার্গেট: <code>{number}</code>\n"
                        f"📊 প্রগ্রেস: <code>[{bar}]</code> <b>{percent}%</b> (হিট: {i+1}/{amount})\n\n"
                        f"✅ মোট সফল SMS: <b>{total_sent_count}</b>\n"
                        f"❌ মোট ব্যর্থ SMS: <b>{total_failed_count}</b>",
                        parse_mode="HTML",
                        reply_markup=cancel_kbd
                    )
                except Exception: pass
                
                await asyncio.sleep(1)
            
            # If not cancelled
            if not temp_data.get(user_id, {}).get('cancel', False):
                total_requests = total_sent_count + total_failed_count
                u['total_bombing'] = u.get('total_bombing', 0) + 1
                u['total_success'] = u.get('total_success', 0) + total_sent_count
                u['total_failed'] = u.get('total_failed', 0) + total_failed_count
                u['total_requests'] = u.get('total_requests', 0) + total_requests
                
                try:
                    if users_col is not None:
                        users_col.update_one(
                            {"user_id": user_id},
                            {"$inc": {
                                "total_bombing": 1,
                                "total_success": total_sent_count,
                                "total_failed": total_failed_count,
                                "total_requests": total_requests
                            }},
                            upsert=True
                        )
                except Exception: pass
                
                creator = last_response.get('creator', 'BCZ Team')
                service = last_response.get('service', 'Master API Gateway')
                success_rate = round((total_sent_count / total_requests) * 100, 2) if total_requests > 0 else 0
                
                cost_text = "FREE (VIP)" if is_vip else f"{cost} Points"
                balance_text = "VIP Access" if is_vip else f"{u.get('points', 0)} Points"
                
                result_message = (
                    f"✅ <b>বোম্বিং সফলভাবে সম্পন্ন!</b> ✅\n\n"
                    f"📱 টার্গেট: <code>{number}</code>\n"
                    f"💥 হিট সম্পন্ন: <b>{amount} / {amount} বার</b>\n"
                    f"✅ মোট সফল SMS: <b>{total_sent_count}</b>\n"
                    f"❌ মোট ব্যর্থ SMS: <b>{total_failed_count}</b>\n"
                    f"📊 সফলতার হার: <b>{success_rate}%</b>\n"
                    f"💰 খরচ: <b>{cost_text}</b>\n"
                    f"💳 অবশিষ্ট ব্যালেন্স: <b>{balance_text}</b>\n\n"
                    f"🛠 সার্ভিস: {service}\n"
                    f"👨‍💻 Creator: {creator}"
                )
                await msg.edit_text(result_message, parse_mode="HTML")

            await update.message.reply_text("🏠 মেইন মেনু", reply_markup=get_main_keyboard(user_id))
            if user_id in temp_data: del temp_data[user_id]
                
        except ValueError: await update.message.reply_text("❌ ভুল ইনপুট! সংখ্যা দিন।", reply_markup=get_back_keyboard())

# ===================== MAIN FUNCTION =====================
def main():
    application = Application.builder().token(TOKEN).build()
    
    # 🎯 1. Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", admin_users))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(CommandHandler("makecode", admin_makecode))
    application.add_handler(CommandHandler("addpoints", admin_addpoints))
    application.add_handler(CommandHandler("addvip", admin_addvip))
    application.add_handler(CommandHandler("removevip", admin_removevip))
    application.add_handler(CommandHandler("protectnumber", admin_protectnumber))
    application.add_handler(CommandHandler("unprotectnumber", admin_unprotectnumber))
    application.add_handler(CommandHandler("addchannel", admin_addchannel))
    application.add_handler(CommandHandler("removechannel", admin_removechannel))
    application.add_handler(CommandHandler("setapi", admin_setapi))
    application.add_handler(CommandHandler("botstats", admin_botstats))
    
    # 🎯 2. Message Handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("="*50)
    print("🤖 MASTER SMS BOMBER BOT IS ONLINE WITH ACCURATE SMS COUNTS!")
    print("="*50)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
