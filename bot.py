import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ===== CONFIG =====
BOT_TOKEN = "7429115282:AAHOc7UESTfl648pUr6_tavWqlhCYtVHLsw"  # From @BotFather
ADMIN_ID = 8142148294         # Your Telegram ID
SUPPORT_USERNAME = "@Maxamy1" # Support channel

# Compulsory channels
REQUIRED_CHANNEL = "@testnetprof"  # Change to your channel
REQUIRED_GROUP = "@promoterprof"   # Change to your group

# Payment rates (100 Stars = $1)
STARS_PER_DOLLAR = 100
AD_PRICE_STARS = 100          # 100 Stars per ad
MONTHLY_PRICE_STARS = 2000    # 2000 Stars monthly

# Crypto addresses (your addresses)
PAYMENT_ADDRESSES = {
    "usdt_bnb": "0xA7E6F87de16d880eEacF94B5Dee91b584B2059B5",
    "usdt_eth": "0xA7E6F87de16d880eEacF94B5Dee91b584B2059B5",
    "usdt_trx": "TTZnPBeSoX95NhB7xQ4gfac5HF4qqAJ5xW",
    "bnb": "0xA7E6F87de16d880eEacF94B5Dee91b584B2059B5",
    "ton": "UQAmPfO35H-q2sXMsi4kVQ5AhsVnG1TbFBeRxIxnZBRR4Em-",
    "trx": "TTZnPBeSoX95NhB7xQ4gfac5HF4qqAJ5xW",
    "pol": "0xA7E6F87de16d880eEacF94B5Dee91b584B2059B5"
}

# ===== DATABASE =====
def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            ads_remaining INTEGER DEFAULT 0,
            premium_expiry TEXT,
            verified_member BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT,
            tx_hash TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# ===== MEMBERSHIP VERIFICATION =====
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        channel_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        group_member = await context.bot.get_chat_member(REQUIRED_GROUP, user_id)
        return channel_member.status != 'left' and group_member.status != 'left'
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_member(user_id, context):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET verified_member = 1 WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            "✅ Verification complete! You can now use all bot features.\n"
            "Use /pricing to see advertising options."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton("Join Group", url=f"https://t.me/{REQUIRED_GROUP[1:]}")],
            [InlineKeyboardButton("I've Joined ✅", callback_data="verify_membership")]
        ]
        await update.message.reply_text(
            "📢 To use this bot, you must join our channel and group:\n\n"
            f"1. {REQUIRED_CHANNEL}\n"
            f"2. {REQUIRED_GROUP}\n\n"
            "After joining, click the button below:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def verify_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if await is_member(query.from_user.id, context):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, verified_member) VALUES (?, 1)
        ''', (query.from_user.id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            "✅ Verification complete! You can now use all bot features.\n"
            "Use /pricing to see advertising options."
        )
    else:
        await query.answer("You haven't joined both channel and group yet!", show_alert=True)

# ===== COMMAND HANDLERS WITH VERIFICATION =====
def verified_command(handler):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT verified_member FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return await handler(update, context)
        else:
            return await check_membership(update, context)
    return wrapped

# ===== MODIFIED COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_membership(update, context)

@verified_command
async def pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"💳 1 Ad ({AD_PRICE_STARS} Stars)", callback_data='pay_single')],
        [InlineKeyboardButton(f"🚀 Monthly ({MONTHLY_PRICE_STARS} Stars)", callback_data='pay_monthly')],
        [InlineKeyboardButton("📩 Contact Support", url=f"t.me/{SUPPORT_USERNAME[1:]}")]
    ]
    
    crypto_options = "\n".join([f"• {n.upper()}: `{a}`" for n,a in PAYMENT_ADDRESSES.items()])
    
    await update.message.reply_text(
        f"🌟 *Pricing*\n\n"
        f"🔸 *Single Ad*:\n"
        f"   - {AD_PRICE_STARS} Stars (${AD_PRICE_STARS/STARS_PER_DOLLAR})\n"
        f"   - OR crypto equivalent\n\n"
        f"🔸 *Monthly Unlimited*:\n"
        f"   - {MONTHLY_PRICE_STARS} Stars (${MONTHLY_PRICE_STARS/STARS_PER_DOLLAR})\n\n"
        f"*Crypto Addresses*:\n{crypto_options}\n\n"
        f"📌 After payment, send:\n"
        f"1. Screenshot\n2. Transaction Hash\n"
        f"to {SUPPORT_USERNAME}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

@verified_command
async def handle_payment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'pay_single':
        await show_payment_methods(query, AD_PRICE_STARS, "1 Ad")
    elif query.data == 'pay_monthly':
        await show_payment_methods(query, MONTHLY_PRICE_STARS, "Monthly Subscription")

async def show_payment_methods(query, stars_amount: int, plan_name: str):
    keyboard = [
        [InlineKeyboardButton("USDT (TRC20)", callback_data=f'crypto_usdt_trx_{stars_amount}')],
        [InlineKeyboardButton("TON", callback_data=f'crypto_ton_{stars_amount}')],
        [InlineKeyboardButton("Telegram Stars", callback_data=f'stars_{stars_amount}')],
    ]
    
    await query.edit_message_text(
        f"💎 *{plan_name} - {stars_amount} Stars*\n\n"
        "Choose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ===== ADMIN TOOLS =====
async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        currency = context.args[2].lower()
        tx_hash = context.args[3] if len(context.args) > 3 else "manual"
        
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        amount_usd = amount / STARS_PER_DOLLAR if currency == "stars" else amount
        
        if amount_usd >= (MONTHLY_PRICE_STARS / STARS_PER_DOLLAR):
            expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, premium_expiry) VALUES (?, ?)
            ''', (user_id, expiry))
            msg = f"✅ Added 30-day premium for {user_id}"
        else:
            ads_added = int(amount_usd * (STARS_PER_DOLLAR / AD_PRICE_STARS))
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id) VALUES (?)
            ''', (user_id,))
            cursor.execute('''
                UPDATE users SET ads_remaining = ads_remaining + ? 
                WHERE user_id = ?
            ''', (ads_added, user_id))
            msg = f"✅ Added {ads_added} ads for {user_id}"
        
        cursor.execute('''
            INSERT INTO payments 
            (user_id, amount, currency, tx_hash)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, currency, tx_hash))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(msg)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Payment verified! You received {'unlimited ads' if amount_usd >= 20 else f'{ads_added} ad credits'}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}\nUsage: /verify USER_ID AMOUNT CURRENCY [TX_HASH]")

# ===== BOT SETUP =====
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pricing", pricing))
    app.add_handler(CommandHandler("verify", verify_payment))
    app.add_handler(CommandHandler("check", check_membership))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_payment_choice, pattern='^pay_(single|monthly)$'))
    app.add_handler(CallbackQueryHandler(verify_membership_callback, pattern='^verify_membership$'))
    app.add_handler(CallbackQueryHandler(
        lambda u,c: show_payment_methods(u.callback_query, int(u.callback_query.data.split('_')[-1])),
        pattern='^(crypto|stars)_'
    ))
    
    print("🤖 Bot is running with compulsory channel/group verification...")
    app.run_polling()

if __name__ == "__main__":
    main()
