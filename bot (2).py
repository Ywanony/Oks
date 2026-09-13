import asyncio
import html
import logging
import random
import string
import sys
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from supabase import Client, create_client


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "8868005439:AAHGetUn8FwoJNO1VwKWyywr08wP-f1vWDU"

ADMIN_IDS = [
    8863002910,
    8459158216,
]

SUPPORT_USERNAME = "VlPSuppot"

PUBLIC_DEMO_CHANNEL_LINK = "https://t.me/javapythoncourse"

# ============================================================
# HOW TO BUY LINK
# ============================================================
# Apna Telegram course-buy link yahan daalo.
# Example:
# HOW_TO_BUY_LINK = "https://t.me/yourchannel/123"
#
# Ya direct Telegram group/channel/course post ka link.
HOW_TO_BUY_LINK = "https://t.me/your_how_to_buy_link"


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = "https://isgnfbbxkarlomtueyzd.supabase.co"

# IMPORTANT:
# Apni NEW service_role key yahan daalo.
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlzZ25mYmJ4a2FybG9tdHVleXpkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4OTMwMTIzMSwiZXhwIjoyMTA0ODc3MjMxfQ.JkHK0cbvl6olJY817BPpiWM9xkMo-lWgbO7gcc3NQzI"

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# IMAGES
# ============================================================

INTRO_IMAGE_URL = "https://i.ibb.co/JbDHr17/x.jpg"
CUSTOM_PLAN_QR = "https://i.ibb.co/8DzYrm42/x.jpg"
DEFAULT_BANNER_URL = "https://i.ibb.co/wNKNQDGy/x.jpg"


# ============================================================
# PRICING
# ============================================================
PRICING_PLANS = {
    "49": {
        "price": 49,
        "label": "1 Group Starter Plan - ₹49",
        "group_text": "1 Group"
    },
    "99": {
        "price": 99,
        "label": "3 Groups Plan - ₹99",
        "group_text": "3 Groups"
    },
    "249": {
        "price": 249,
        "label": "10 Groups Plan - ₹249",
        "group_text": "10 Groups"
    }
}

ALL_COLLECTION_PLANS = {
    "350": {
        "price": 350,
        "label": "All Zip 5247+ Files - ₹350",
        "group_text": "5247+ Files"
    },
    "499": {
        "price": 499,
        "label": "All Mega 23 Groups - ₹499",
        "group_text": "23 Groups"
    },
    "749": {
        "price": 749,
        "label": "Mega Links + Zip Both - ₹749",
        "group_text": "Mega Links + Zip"
    }
}

CATEGORIES = {
    "cat_all": "🔥 𝖠𝖫𝖫 𝖢𝖮𝖫𝖫𝖤𝖢𝖳𝖨𝖮𝖭 𝖡𝖴𝖸 🔞",
    "cat_study": "CP,RP😍",
    "cat_material": "DESI LEAKED💧",
    "cat_newone": "MOM SON+PEDO",
    "cat_member": "HIDDEN,TANGO",
    "cat_java": "PAK,JAPANESE",
    "cat_python": "MALLU/TAMIL🤩",
}

CATEGORY_PHOTOS = {
    "cat_all": "https://i.ibb.co/6cy5fQjJ/x.jpg",
    "cat_study": "https://i.ibb.co/TMsv6GGf/x.jpg",
    "cat_material": "https://i.ibb.co/Cp4Mdfnb/x.jpg",
    "cat_newone": "https://i.ibb.co/wrS6wxh3/x.jpg",
    "cat_member": "https://i.ibb.co/RTWYpzHW/x.jpg",
    "cat_java": "https://i.ibb.co/RGvhX5rt/x.jpg",
    "cat_python": "https://i.ibb.co/Z6632LTn/x.jpg",
}


# ============================================================
# BROADCAST CONFIG
# ============================================================

# Number of Telegram send operations allowed concurrently.
# 20-30 is a safer starting point.
BROADCAST_CONCURRENCY = 25

# Telegram may return RetryAfter when rate limit is reached.
# The code automatically waits only when Telegram asks it to.
MAX_BROADCAST_RETRIES = 5

# Progress message edit interval.
# 0.7 = smooth progress without editing Telegram message
# hundreds/thousands of times per second.
PROGRESS_UPDATE_INTERVAL = 0.7


# ============================================================
# ROUTER & STATES
# ============================================================

router = Router()


class PaymentStates(StatesGroup):
    waiting_for_screenshot = State()
    waiting_for_custom_link = State()
    waiting_for_rejection_reason = State()
    waiting_for_broadcast_msg = State()


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def generate_order_id() -> str:
    return "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=9
        )
    )


async def supabase_request_with_retry(
    query_func,
    retries: int = 3,
    delay: int = 2
):
    """
    Supabase Python client is synchronous.
    Run it in a worker thread so the Telegram event loop
    does not get blocked.
    """

    for attempt in range(retries):
        try:
            return await asyncio.to_thread(query_func)

        except Exception as e:
            error_text = str(e)

            retryable = any(
                err in error_text
                for err in [
                    "11001",
                    "getaddrinfo",
                    "Temporary failure",
                    "Connection",
                    "timeout",
                    "timed out"
                ]
            )

            if retryable:
                logging.warning(
                    f"Database error "
                    f"(Attempt {attempt + 1}/{retries}): {e}"
                )

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(delay)

            else:
                raise


async def log_user_to_db(user):
    try:
        await supabase_request_with_retry(
            lambda: supabase.table("bot_users").upsert(
                {
                    "user_id": user.id,
                    "full_name": user.full_name,
                    "username": (
                        f"@{user.username}"
                        if user.username
                        else "No Username"
                    ),
                }
            ).execute()
        )

    except Exception as e:
        logging.error(
            f"Supabase user log error: {e}"
        )


async def safe_edit_message(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    photo_url: Optional[str] = None
):
    try:

        if photo_url and message.photo:

            await message.edit_media(
                media=InputMediaPhoto(
                    media=photo_url,
                    caption=text,
                    parse_mode=ParseMode.MARKDOWN
                ),
                reply_markup=reply_markup
            )

        elif photo_url:

            try:
                await message.delete()
            except Exception:
                pass

            await message.answer_photo(
                photo=photo_url,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        elif message.photo:

            try:
                await message.delete()
            except Exception:
                pass

            await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        else:

            await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:

        logging.info(
            f"Fallback answer triggered: {e}"
        )

        if photo_url:

            await message.answer_photo(
                photo=photo_url,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        else:

            await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )


# ============================================================
# KEYBOARDS
# ============================================================

def get_main_menu_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🔥 𝖡𝗎𝗒 𝖬𝖾𝗆𝖻𝖾𝗋𝗌𝗁𝗂𝗉",
                    callback_data="buy_membership"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔍 𝖢𝗁𝖾𝖼𝗄 𝖲𝗍𝖺𝗍𝗎𝗌",
                    callback_data="check_status"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔞 𝖯𝗋𝖾𝗆𝗂𝗎𝗆 𝖣𝖾𝗆𝗈",
                    callback_data="demo_preview"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💬 𝖢𝗈𝗇𝗍𝖺𝖼𝗍 𝖲𝗎𝗉𝗉𝗈𝗋𝗍",
                    callback_data="support"
                )
            ],
        ]
    )


def get_membership_categories_keyboard():

    keys = list(CATEGORIES.keys())

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=f"🌟 {CATEGORIES[keys[0]]}",
                    callback_data=keys[0]
                )
            ],

            [
                InlineKeyboardButton(
                    text=f"🔹 {CATEGORIES[keys[1]]}",
                    callback_data=keys[1]
                ),
                InlineKeyboardButton(
                    text=f"🔹 {CATEGORIES[keys[2]]}",
                    callback_data=keys[2]
                ),
            ],

            [
                InlineKeyboardButton(
                    text=f"🔹 {CATEGORIES[keys[3]]}",
                    callback_data=keys[3]
                ),
                InlineKeyboardButton(
                    text=f"🔹 {CATEGORIES[keys[4]]}",
                    callback_data=keys[4]
                ),
            ],

            [
                InlineKeyboardButton(
                    text=f"🔹 {CATEGORIES[keys[5]]}",
                    callback_data=keys[5]
                ),
                InlineKeyboardButton(
                    text=f"🔹 {CATEGORIES[keys[6]]}",
                    callback_data=keys[6]
                ),
            ],

            [
                InlineKeyboardButton(
                    text="« Back to Main Menu",
                    callback_data="main_menu"
                )
            ],
        ]
    )


def get_membership_plans_keyboard(category_code: str):

    if category_code == "cat_all":

        return InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text=f"⭐ [ {ALL_COLLECTION_PLANS['350']['label']} ]",
                        callback_data=f"plan_350_{category_code}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text=f"⚡ [ {ALL_COLLECTION_PLANS['499']['label']} ]",
                        callback_data=f"plan_499_{category_code}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text=f"🔥 [ {ALL_COLLECTION_PLANS['749']['label']} ]",
                        callback_data=f"plan_749_{category_code}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="« Back to Categories",
                        callback_data="buy_membership"
                    )
                ],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=f"⭐ [ {PRICING_PLANS['49']['label']} ]",
                    callback_data=f"plan_49_{category_code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text=f"⚡ [ {PRICING_PLANS['99']['label']} ]",
                    callback_data=f"plan_99_{category_code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text=f"🔥 [ {PRICING_PLANS['249']['label']} ]",
                    callback_data=f"plan_249_{category_code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text="« Back to Categories",
                    callback_data="buy_membership"
                )
            ],
        ]
    )


def get_admin_panel_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📊 View History",
                    callback_data="admin_history"
                ),

                InlineKeyboardButton(
                    text="📈 Stats & Users",
                    callback_data="admin_stats"
                ),
            ],

            [
                InlineKeyboardButton(
                    text="📢 Broadcast Message",
                    callback_data="admin_broadcast_start"
                )
            ],
        ]
    )


# ============================================================
# USER START
# ============================================================

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    # DB logging is now non-blocking for Telegram handlers.
    asyncio.create_task(
        log_user_to_db(message.from_user)
    )

    welcome_text = (
        "🔥 **Welcome to Exclusive Premium Videos!**\n\n"
        "⚡ *Tap the buttons below to unlock your access "
        "or check your subscription status.*"
    )

    await message.answer_photo(
        photo=INTRO_IMAGE_URL,
        caption=welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# ============================================================
# MAIN MENU
# ============================================================

@router.callback_query(F.data == "main_menu")
async def process_main_menu(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    menu_text = (
        "🔥 **Welcome to Exclusive Premium Videos!**\n\n"
        "⚡ *Tap the buttons below to unlock your access "
        "or check your subscription status.*"
    )

    await safe_edit_message(
        callback.message,
        menu_text,
        get_main_menu_keyboard(),
        photo_url=INTRO_IMAGE_URL
    )

    await callback.answer()


# ============================================================
# BUY MEMBERSHIP
# ============================================================

@router.callback_query(F.data == "buy_membership")
async def process_buy_membership(
    callback: CallbackQuery
):

    plans_text = (
        "💎 **𝗦𝗮𝗹𝗲𝗰𝘁 𝘄𝗵𝗶𝗰𝗵 𝗰𝗮𝘁𝗲𝗴𝗼𝗿𝘆 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁.**\n\n"
        "Choose any category option below to open "
        "the corresponding plan checkout:"
    )

    await safe_edit_message(
        callback.message,
        plans_text,
        get_membership_categories_keyboard(),
        photo_url=DEFAULT_BANNER_URL
    )

    await callback.answer()


# ============================================================
# CATEGORY
# ============================================================

@router.callback_query(
    F.data.in_(list(CATEGORIES.keys()))
)
async def process_selected_category(
    callback: CallbackQuery,
    state: FSMContext
):

    cat_code = callback.data

    await state.update_data(
        current_category=cat_code
    )

    category_display_name = CATEGORIES.get(
        cat_code,
        "Premium"
    )

    category_photo = CATEGORY_PHOTOS.get(
        cat_code,
        DEFAULT_BANNER_URL
    )

    plan_select_text = (
        f"💎 **𝗦𝗲𝗹𝗲𝗰𝘁 𝘆𝗼𝘂𝗿 𝗩𝗜𝗣 𝗺𝗲𝗺𝗯𝗲𝗿𝘀𝗵𝗶𝗽 "
        f"𝗽𝗹𝗮𝗻 𝗳𝗼𝗿 {category_display_name}**\n\n"
        "Choose a plan from the options below:"
    )

    await safe_edit_message(
        callback.message,
        plan_select_text,
        get_membership_plans_keyboard(cat_code),
        photo_url=category_photo
    )

    await callback.answer()


# ============================================================
# PLAN
# ============================================================

@router.callback_query(
    F.data.startswith("plan_")
)
async def process_selected_plan(
    callback: CallbackQuery,
    state: FSMContext
):

    parts = callback.data.split("_")

    amount_str = parts[1]

    cat_code = (
        f"{parts[2]}_{parts[3]}"
        if len(parts) > 3
        else parts[2]
    )

    order_id = generate_order_id()

    if cat_code == "cat_all":

        plan_info = ALL_COLLECTION_PLANS.get(
            amount_str,
            ALL_COLLECTION_PLANS["350"]
        )

    else:

        plan_info = PRICING_PLANS.get(
            amount_str,
            PRICING_PLANS["49"]
        )

    amount = plan_info["price"]

    group_text = plan_info["group_text"]

    category_clean_name = CATEGORIES.get(
        cat_code,
        "VIP Plan"
    )

    full_plan_name = (
        f"{plan_info['label']} - "
        f"{category_clean_name}"
    )

    await state.update_data(
        current_order_id=order_id,
        current_amount=amount,
        current_plan_name=full_plan_name
    )

    details_text = (
        f"🎁 **𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝘆 & 𝗣𝗹𝗮𝗻:** "
        f"{full_plan_name}\n"
        f"💰 **𝗔𝗺𝗼𝘂𝗻𝘁:** ₹{amount} INR\n"
        f"👥 **𝗚𝗿𝗼𝘂𝗽𝘀:** {group_text}\n"
        f"🆔 **𝗢𝗿𝗱𝗲𝗿 𝗜𝗱:** `{order_id}`\n\n"
        "📱 **Pay using any UPI app** "
        "(GPay, PhonePe, Paytm)\n\n"
        "⏱️ *QR code is valid for 10 minutes only*\n\n"
        "📲 **Scan the QR Code above to pay.**\n"
        "👇 Click **'I Have Paid'** after completing payment."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="💳 I Have Paid",
                    callback_data="pay_now"
                )
            ],

            [
                InlineKeyboardButton(
                    text="« Back to Plans",
                    callback_data=cat_code
                )
            ],
        ]
    )

    await safe_edit_message(
        callback.message,
        details_text,
        keyboard,
        photo_url=CUSTOM_PLAN_QR
    )

    await callback.answer()


# ============================================================
# PAYMENT NOW
# ============================================================

@router.callback_query(F.data == "pay_now")
async def process_pay_now(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        PaymentStates.waiting_for_screenshot
    )

    await callback.message.answer(
        "📸 **Please send the payment screenshot now.**\n\n"
        "After confirmation, you'll get the link here.",
        parse_mode=ParseMode.MARKDOWN
    )

    await callback.answer()


# ============================================================
# SCREENSHOT
# ============================================================

@router.message(
    PaymentStates.waiting_for_screenshot,
    F.photo
)
async def receive_screenshot(
    message: Message,
    state: FSMContext
):

    photo_id = message.photo[-1].file_id

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "No Username"
    )

    data = await state.get_data()

    order_id = data.get(
        "current_order_id",
        generate_order_id()
    )

    amount = data.get(
        "current_amount",
        49
    )

    duration = data.get(
        "current_duration",
        30
    )

    plan_name = data.get(
        "current_plan_name",
        "VIP Collection"
    )

    await log_user_to_db(user)

    try:

        await supabase_request_with_retry(
            lambda: supabase.table(
                "payments"
            ).insert(
                {
                    "user_id": user.id,
                    "order_id": order_id,
                    "username": username,
                    "plan_name": plan_name,
                    "amount": amount,
                    "duration_days": duration,
                    "photo_id": photo_id,
                    "status": "pending",
                }
            ).execute()
        )

    except Exception as e:

        logging.error(
            f"Supabase payment entry error: {e}"
        )

    await message.answer(
        "⏳ **Payment Screenshot Received!**\n\n"
        "Please wait. Verification will be done by "
        "our admin team.\n"
        "Your access link will be sent here shortly.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Back to Main Menu",
                        callback_data="main_menu"
                    )
                ]
            ]
        ),
        parse_mode=ParseMode.MARKDOWN
    )

    await state.clear()

    safe_name = html.escape(
        user.full_name or "Unknown"
    )

    safe_username = html.escape(username)

    admin_caption = (
        "🚨 <b>NEW PAYMENT PENDING VERIFICATION</b> 🚨\n\n"
        f"👤 <b>Name:</b> {safe_name}\n"
        f"🔗 <b>Username:</b> "
        f"<code>{safe_username}</code>\n"
        f"🆔 <b>Chat/User ID:</b> "
        f"<code>{user.id}</code>\n"
        f"📦 <b>Plan Selected:</b> "
        f"{html.escape(plan_name)}\n"
        f"💰 <b>Amount Transferred:</b> "
        f"₹{amount}\n"
        f"🏷️ <b>Order ID:</b> "
        f"<code>{order_id}</code>\n\n"
        "👉 <i>Review screenshot and choose action:</i>"
    )

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [

                InlineKeyboardButton(
                    text="✅ Approve",
                    callback_data=(
                        f"approve_{user.id}_{order_id}"
                    )
                ),

                InlineKeyboardButton(
                    text="❌ Reject",
                    callback_data=(
                        f"reject_{user.id}_{order_id}"
                    )
                ),

            ]
        ]
    )

    # Notify admins concurrently.
    await asyncio.gather(
        *[
            send_admin_payment_notification(
                message.bot,
                admin_id,
                photo_id,
                admin_caption,
                admin_keyboard
            )
            for admin_id in ADMIN_IDS
        ],
        return_exceptions=True
    )


async def send_admin_payment_notification(
    bot: Bot,
    admin_id: int,
    photo_id: str,
    caption: str,
    keyboard: InlineKeyboardMarkup
):

    try:

        await bot.send_photo(
            chat_id=admin_id,
            photo=photo_id,
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        logging.error(
            f"Failed to notify admin {admin_id}: {e}"
        )


@router.message(
    PaymentStates.waiting_for_screenshot
)
async def invalid_screenshot_type(
    message: Message
):

    await message.answer(
        "⚠️ Please send a valid **image/screenshot** "
        "of your payment receipt.",
        parse_mode=ParseMode.MARKDOWN
    )


# ============================================================
# CHECK STATUS
# ============================================================

@router.callback_query(F.data == "check_status")
async def process_check_status(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    try:

        res = await supabase_request_with_retry(
            lambda: supabase.table(
                "payments"
            )
            .select("*")
            .eq("user_id", user_id)
            .order(
                "created_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

        if res.data:

            record = res.data[0]

            status_msg = (
                "🔍 **Subscription Status**\n\n"
                f"Plan: {record['plan_name']}\n"
                f"Order ID: `{record['order_id']}`\n"
                f"Status: **"
                f"{str(record['status']).upper()}"
                f"**"
            )

        else:

            status_msg = (
                "🔍 **Subscription Status**\n\n"
                "❌ You do not have an active "
                "subscription yet."
            )

    except Exception:

        status_msg = (
            "🔍 **Subscription Status**\n\n"
            "❌ Could not fetch data from database."
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🛍️ Buy Membership",
                    callback_data="buy_membership"
                )
            ],

            [
                InlineKeyboardButton(
                    text="« Back to Main Menu",
                    callback_data="main_menu"
                )
            ],

        ]
    )

    await safe_edit_message(
        callback.message,
        status_msg,
        keyboard,
        photo_url=INTRO_IMAGE_URL
    )

    await callback.answer()


# ============================================================
# DEMO
# ============================================================

@router.callback_query(F.data == "demo_preview")
async def process_demo(
    callback: CallbackQuery
):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🔗 Tap Here to View Demo Preview",
                    url=PUBLIC_DEMO_CHANNEL_LINK
                )
            ],

            [
                InlineKeyboardButton(
                    text="🛒 How To Buy",
                    url=HOW_TO_BUY_LINK
                )
            ],

            [
                InlineKeyboardButton(
                    text="« Back to Main Menu",
                    callback_data="main_menu"
                )
            ],

        ]
    )

    await safe_edit_message(
        callback.message,
        (
            "🚀 **Premium Demo Channel**\n\n"
            "Click below to join our public demo channel.\n\n"
            "🛒 **Want to purchase the course?**\n"
            "Tap **How To Buy** for the complete buying process."
        ),
        keyboard,
        photo_url=DEFAULT_BANNER_URL
    )

    await callback.answer()


# ============================================================
# SUPPORT
# ============================================================

@router.callback_query(F.data == "support")
async def process_support(
    callback: CallbackQuery
):

    support_text = (
        "💬 **Customer Support**\n\n"
        "Contact support admin directly:"
    )

    support_url = (
        f"https://t.me/{SUPPORT_USERNAME}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="💬 Contact Support Admin",
                    url=support_url
                )
            ],

            [
                InlineKeyboardButton(
                    text="« Back to Main Menu",
                    callback_data="main_menu"
                )
            ],

        ]
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        support_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

    await callback.answer()


# ============================================================
# ADMIN PANEL
# ============================================================

@router.message(Command("admin"))
async def cmd_admin(
    message: Message
):

    if not is_admin(message.from_user.id):

        await message.answer(
            "⛔ **Access Denied.**",
            parse_mode=ParseMode.MARKDOWN
        )

        return

    await message.answer(
        "👑 **Admin Control Hub**\n\n"
        "Select an operation:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# ============================================================
# HISTORY
# ============================================================

@router.message(Command("history"))
async def cmd_history(
    message: Message
):

    if not is_admin(message.from_user.id):
        return

    await send_history_view(message)


async def send_history_view(
    target_message
):

    try:

        res = await supabase_request_with_retry(
            lambda: supabase.table(
                "payments"
            )
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .limit(10)
            .execute()
        )

        if not res.data:

            await target_message.answer(
                "📂 No payment records found."
            )

            return

        text = "📊 **Recent Payment Records:**\n\n"

        for r in res.data:

            text += (
                f"🆔 Chat/User ID: "
                f"`{r.get('user_id')}`\n"
                f"🔗 Username: "
                f"{r.get('username')}\n"
                f"📦 Plan: "
                f"{r.get('plan_name')} | "
                f"Amt: ₹{r.get('amount')}\n"
                f"🏷️ Order: "
                f"`{r.get('order_id')}` | "
                f"Status: **"
                f"{str(r.get('status')).upper()}"
                f"**\n"
                "-------------------\n"
            )

        await target_message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:

        await target_message.answer(
            f"❌ Error fetching history: {e}"
        )


@router.callback_query(
    F.data == "admin_history"
)
async def process_admin_history_cb(
    callback: CallbackQuery
):

    if is_admin(callback.from_user.id):

        await send_history_view(
            callback.message
        )

    await callback.answer()


# ============================================================
# ADMIN STATS
# ============================================================

@router.callback_query(
    F.data == "admin_stats"
)
async def process_admin_stats_cb(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    try:

        users_res = await supabase_request_with_retry(
            lambda: supabase.table(
                "bot_users"
            )
            .select(
                "user_id",
                count="exact"
            )
            .execute()
        )

        pay_res = await supabase_request_with_retry(
            lambda: supabase.table(
                "payments"
            )
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        total_users = (
            users_res.count
            if hasattr(users_res, "count")
            else len(users_res.data)
        )

        total_payments = (
            pay_res.count
            if hasattr(pay_res, "count")
            else len(pay_res.data)
        )

        stats_text = (
            "📈 **Bot Statistics & Database Overview**\n\n"
            f"👥 **Total Users:** `{total_users}`\n"
            f"💳 **Total Orders:** `{total_payments}`"
        )

        await callback.message.answer(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:

        await callback.message.answer(
            f"❌ Error pulling stats: {e}"
        )

    await callback.answer()


# ============================================================
# BROADCAST START
# ============================================================

@router.callback_query(
    F.data == "admin_broadcast_start"
)
async def process_broadcast_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    await state.set_state(
        PaymentStates.waiting_for_broadcast_msg
    )

    await callback.message.answer(
        "📢 **Broadcast Setup**\n\n"
        "Send the message you want to broadcast.\n\n"
        "The message will be sent to all users stored "
        "in `bot_users`.",
        parse_mode=ParseMode.MARKDOWN
    )

    await callback.answer()


# ============================================================
# GET ALL USERS
# ============================================================

async def get_all_bot_users():
    """
    Fetch ALL users from Supabase using pagination.

    This avoids the normal API row-limit problem.
    """

    all_users = []

    page_size = 1000
    offset = 0

    while True:

        response = await supabase_request_with_retry(
            lambda offset=offset: supabase.table(
                "bot_users"
            )
            .select("user_id")
            .range(
                offset,
                offset + page_size - 1
            )
            .execute()
        )

        rows = response.data or []

        if not rows:
            break

        all_users.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    # Remove duplicates.
    unique_ids = []
    seen = set()

    for row in all_users:

        user_id = row.get("user_id")

        if user_id is None:
            continue

        try:
            user_id = int(user_id)
        except Exception:
            continue

        if user_id not in seen:

            seen.add(user_id)
            unique_ids.append(user_id)

    return unique_ids


# ============================================================
# PROGRESS BAR
# ============================================================

def make_progress_bar(
    current: int,
    total: int,
    width: int = 18
):

    if total <= 0:

        return "░" * width, 0

    percentage = int(
        (current / total) * 100
    )

    filled = int(
        (percentage / 100) * width
    )

    filled = min(
        filled,
        width
    )

    bar = (
        "█" * filled
        + "░" * (width - filled)
    )

    return bar, percentage


def build_broadcast_progress(
    total: int,
    sent: int,
    failed: int,
    processing: int = 0
):

    done = sent + failed

    bar, percentage = make_progress_bar(
        done,
        total
    )

    return (
        "📢 <b>Broadcasting...</b>\n\n"
        f"⏳ <code>{bar}</code> <b>{percentage}%</b>\n\n"
        f"👥 Total: <b>{total}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"⚡ Processing: <b>{processing}</b>\n\n"
        "Please wait..."
    )


# ============================================================
# SEND ONE BROADCAST
# ============================================================

async def send_broadcast_to_user(
    bot: Bot,
    user_id: int,
    content: str,
    semaphore: asyncio.Semaphore
):

    async with semaphore:

        for attempt in range(
            MAX_BROADCAST_RETRIES
        ):

            try:

                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        "📢 <b>Announcement</b>\n\n"
                        f"{html.escape(content)}"
                    ),
                    parse_mode=ParseMode.HTML
                )

                return True

            except TelegramRetryAfter as e:

                retry_seconds = float(
                    getattr(
                        e,
                        "retry_after",
                        1
                    )
                )

                logging.warning(
                    f"Telegram rate limit for "
                    f"{user_id}. "
                    f"Waiting {retry_seconds}s"
                )

                await asyncio.sleep(
                    retry_seconds
                )

            except TelegramNetworkError as e:

                logging.warning(
                    f"Network error for "
                    f"{user_id}: {e}"
                )

                if attempt < MAX_BROADCAST_RETRIES - 1:

                    await asyncio.sleep(
                        min(
                            2 ** attempt,
                            10
                        )
                    )

                else:

                    return False

            except Exception as e:

                logging.debug(
                    f"Broadcast failed for "
                    f"{user_id}: {e}"
                )

                return False

        return False


# ============================================================
# BROADCAST ENGINE
# ============================================================

async def run_broadcast(
    bot: Bot,
    progress_message: Message,
    content: str
):

    # --------------------------------------------------------
    # STEP 1: FETCH ALL USERS
    # --------------------------------------------------------

    try:

        user_ids = await get_all_bot_users()

    except Exception as e:

        await progress_message.edit_text(
            (
                "❌ <b>Broadcast Failed</b>\n\n"
                f"Database error:\n"
                f"<code>{html.escape(str(e))}</code>"
            ),
            parse_mode=ParseMode.HTML
        )

        return

    total = len(user_ids)

    if total == 0:

        await progress_message.edit_text(
            "⚠️ <b>No users found.</b>\n\n"
            "The `bot_users` table is empty.",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------

    sent = 0
    failed = 0
    completed = 0

    counter_lock = asyncio.Lock()

    semaphore = asyncio.Semaphore(
        BROADCAST_CONCURRENCY
    )

    # --------------------------------------------------------
    # INITIAL PROGRESS
    # --------------------------------------------------------

    try:

        await progress_message.edit_text(
            build_broadcast_progress(
                total=total,
                sent=0,
                failed=0,
                processing=0
            ),
            parse_mode=ParseMode.HTML
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # WORKER
    # --------------------------------------------------------

    async def worker(user_id):

        nonlocal sent
        nonlocal failed
        nonlocal completed

        success = await send_broadcast_to_user(
            bot=bot,
            user_id=user_id,
            content=content,
            semaphore=semaphore
        )

        async with counter_lock:

            if success:
                sent += 1
            else:
                failed += 1

            completed += 1

    # --------------------------------------------------------
    # CREATE TASKS
    # --------------------------------------------------------

    tasks = [
        asyncio.create_task(
            worker(user_id)
        )
        for user_id in user_ids
    ]

    # --------------------------------------------------------
    # LIVE PROGRESS UPDATER
    # --------------------------------------------------------

    async def progress_updater():

        last_done = -1

        while True:

            await asyncio.sleep(
                PROGRESS_UPDATE_INTERVAL
            )

            async with counter_lock:

                current_done = completed
                current_sent = sent
                current_failed = failed

            if current_done == last_done:

                if current_done >= total:
                    break

                continue

            last_done = current_done

            try:

                processing = max(
                    0,
                    min(
                        BROADCAST_CONCURRENCY,
                        total - current_done
                    )
                )

                await progress_message.edit_text(
                    build_broadcast_progress(
                        total=total,
                        sent=current_sent,
                        failed=current_failed,
                        processing=processing
                    ),
                    parse_mode=ParseMode.HTML
                )

            except Exception:
                pass

            if current_done >= total:
                break

    progress_task = asyncio.create_task(
        progress_updater()
    )

    # --------------------------------------------------------
    # WAIT FOR ALL
    # --------------------------------------------------------

    await asyncio.gather(
        *tasks,
        return_exceptions=True
    )

    # Make sure updater exits.
    await progress_task

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    final_bar, final_percentage = make_progress_bar(
        completed,
        total
    )

    final_text = (
        "✅ <b>Broadcast Completed!</b>\n\n"
        f"📊 <code>{final_bar}</code> "
        f"<b>{final_percentage}%</b>\n\n"
        f"👥 Total Users: <b>{total}</b>\n"
        f"✅ Successfully Sent: <b>{sent}</b>\n"
        f"❌ Failed / Blocked: <b>{failed}</b>\n\n"
        "🚀 Broadcast process finished."
    )

    try:

        await progress_message.edit_text(
            final_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👑 Admin Panel",
                            callback_data="admin_panel"
                        )
                    ]
                ]
            )
        )

    except Exception:

        await progress_message.answer(
            final_text,
            parse_mode=ParseMode.HTML
        )


# ============================================================
# BROADCAST MESSAGE HANDLER
# ============================================================

@router.message(
    PaymentStates.waiting_for_broadcast_msg,
    F.from_user.id.in_(ADMIN_IDS)
)
async def execute_broadcast(
    message: Message,
    state: FSMContext
):

    # Accept text OR caption.
    content = (
        message.text
        or message.caption
        or ""
    ).strip()

    if not content:

        await message.answer(
            "⚠️ Please send a text message for broadcast."
        )

        return

    # Clear state immediately.
    # This keeps the admin bot responsive while broadcast
    # runs in the background.
    await state.clear()

    # Start broadcast without blocking admin handlers.
    progress_message = await message.answer(
        "⏳ <b>Preparing broadcast...</b>\n\n"
        "Fetching all users from database...",
        parse_mode=ParseMode.HTML
    )

    asyncio.create_task(
        run_broadcast(
            bot=message.bot,
            progress_message=progress_message,
            content=content
        )
    )


# ============================================================
# ADMIN PANEL CALLBACK
# ============================================================

@router.callback_query(
    F.data == "admin_panel"
)
async def admin_panel_callback(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    await callback.message.answer(
        "👑 <b>Admin Control Hub</b>\n\n"
        "Select an operation:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer()


# ============================================================
# APPROVE
# ============================================================

@router.callback_query(
    F.data.startswith("approve_")
)
async def admin_approve_prompt(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    parts = callback.data.split("_")

    if len(parts) < 3:

        await callback.answer(
            "Invalid order.",
            show_alert=True
        )

        return

    target_user_id = int(parts[1])
    order_id = parts[2]

    await state.set_state(
        PaymentStates.waiting_for_custom_link
    )

    await state.update_data(
        target_user_id=target_user_id,
        order_id=order_id
    )

    await callback.message.answer(
        f"🔗 Send the invite link for Order "
        f"<code>{html.escape(order_id)}</code>\n\n"
        f"User: <code>{target_user_id}</code>",
        parse_mode=ParseMode.HTML
    )

    await callback.answer()


# ============================================================
# APPROVE LINK
# ============================================================

@router.message(
    PaymentStates.waiting_for_custom_link,
    F.from_user.id.in_(ADMIN_IDS)
)
async def process_custom_link_input(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    target_user_id = data.get(
        "target_user_id"
    )

    order_id = data.get(
        "order_id"
    )

    invite_link = (
        message.text or ""
    ).strip()

    if not target_user_id or not order_id:

        await message.answer(
            "❌ Session error. Try again."
        )

        await state.clear()

        return

    if not invite_link:

        await message.answer(
            "⚠️ Please send the invite link."
        )

        return

    try:

        await supabase_request_with_retry(
            lambda: supabase.table(
                "payments"
            )
            .update(
                {
                    "status": "approved",
                    "admin_reason": invite_link
                }
            )
            .eq(
                "order_id",
                order_id
            )
            .execute()
        )

        await message.bot.send_message(
            chat_id=target_user_id,
            text=(
                "🎉 <b>Payment Approved!</b>\n\n"
                "🔗 <b>Private Link:</b>\n"
                f"{html.escape(invite_link)}"
            ),
            parse_mode=ParseMode.HTML
        )

        await message.answer(
            f"✅ Approved and link sent to "
            f"<code>{target_user_id}</code>!",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        await message.answer(
            f"❌ Error during approval:\n"
            f"<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )

    await state.clear()


# ============================================================
# REJECT
# ============================================================

@router.callback_query(
    F.data.startswith("reject_")
)
async def admin_reject_prompt(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    parts = callback.data.split("_")

    if len(parts) < 3:

        await callback.answer(
            "Invalid order.",
            show_alert=True
        )

        return

    target_user_id = int(parts[1])
    order_id = parts[2]

    await state.set_state(
        PaymentStates.waiting_for_rejection_reason
    )

    await state.update_data(
        target_user_id=target_user_id,
        order_id=order_id
    )

    await callback.message.answer(
        f"❌ Type reason for rejecting Order "
        f"<code>{html.escape(order_id)}</code>:",
        parse_mode=ParseMode.HTML
    )

    await callback.answer()


# ============================================================
# REJECT REASON
# ============================================================

@router.message(
    PaymentStates.waiting_for_rejection_reason,
    F.from_user.id.in_(ADMIN_IDS)
)
async def process_rejection_reason_input(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    target_user_id = data.get(
        "target_user_id"
    )

    order_id = data.get(
        "order_id"
    )

    reason = (
        message.text or ""
    ).strip()

    if not target_user_id or not order_id:

        await message.answer(
            "❌ Session error. Try again."
        )

        await state.clear()

        return

    if not reason:

        await message.answer(
            "⚠️ Please type a rejection reason."
        )

        return

    try:

        await supabase_request_with_retry(
            lambda: supabase.table(
                "payments"
            )
            .update(
                {
                    "status": "rejected",
                    "admin_reason": reason
                }
            )
            .eq(
                "order_id",
                order_id
            )
            .execute()
        )

        await message.bot.send_message(
            chat_id=target_user_id,
            text=(
                "❌ <b>Payment Rejected!</b>\n\n"
                "📌 <b>Reason:</b>\n"
                f"{html.escape(reason)}"
            ),
            parse_mode=ParseMode.HTML
        )

        await message.answer(
            f"✅ Rejection sent to user "
            f"<code>{target_user_id}</code>.",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        await message.answer(
            f"❌ Error rejecting order:\n"
            f"<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )

    await state.clear()


# ============================================================
# ERROR HANDLER
# ============================================================

@router.errors()
async def global_error_handler(
    event
):

    logging.error(
        f"Unhandled router error: {event.exception}"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        )
    )

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher()

    dp.include_router(router)

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logging.info(
        "Bot started successfully."
    )

    while True:

        try:

            logging.info(
                "Starting polling..."
            )

            await dp.start_polling(
                bot
            )

        except TelegramNetworkError as e:

            logging.warning(
                f"Network error: {e}. "
                "Reconnecting..."
            )

            await asyncio.sleep(3)

        except Exception as e:

            logging.error(
                f"Polling exception: {e}. "
                "Restarting..."
            )

            await asyncio.sleep(5)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logging.info(
            "Bot stopped safely."
        )