import os
import re
import asyncio
import tempfile
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ParseMode

import yt_dlp


# =========================================================
# TELEGRAM CONFIG
# =========================================================

API_ID = 34584412

API_HASH = "3aa0cabec466727017e6770381a68102"

BOT_TOKEN = "8349584164:AAGtmvoHrmo-g9bFMF4eenZpoHJspR95VZ8"


# =========================================================
# INSTAGRAM
# =========================================================

INSTAGRAM_URL = "https://instagram.com/_savurov._u_"


# =========================================================
# TEMPORARY FOLDER
# =========================================================

TEMP_DIR = Path(tempfile.gettempdir()) / "music_bot_temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# YT-DLP SETTINGS
# =========================================================

YDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    "outtmpl": str(TEMP_DIR / "%(id)s.%(ext)s"),
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "geo_bypass": True,
    "nocheckcertificate": True,
}


# =========================================================
# TELEGRAM BOT
# =========================================================

app = Client(
    "MusicBotSession",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =========================================================
# URL CHECK
# =========================================================

def is_url(text: str) -> bool:

    pattern = re.compile(
        r"https?://(?:www\.)?"
        r"(?:youtube\.com|youtu\.be|"
        r"instagram\.com|"
        r"tiktok\.com|vm\.tiktok\.com|"
        r"music\.youtube\.com|m\.youtube\.com)/[^\s]+",
        re.IGNORECASE
    )

    return bool(pattern.search(text))


# =========================================================
# DOWNLOAD AUDIO
# =========================================================

async def download_audio(
    query: str,
    is_search: bool = False
):

    options = YDL_OPTS.copy()

    if is_search:
        search_query = f"ytsearch1:{query}"
    else:
        search_query = query

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def download():

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                search_query,
                download=True
            )

            if "entries" in info:

                entries = info["entries"]

                if not entries:
                    raise Exception("Qo'shiq topilmadi")

                info = entries[0]

            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):

                base = os.path.splitext(filename)[0]

                for ext in [
                    ".m4a",
                    ".webm",
                    ".opus",
                    ".ogg",
                    ".mp3",
                    ".mp4"
                ]:

                    possible = base + ext

                    if os.path.exists(possible):

                        filename = possible
                        break

            title = (
                info.get("title")
                or info.get("fulltitle")
                or "Unknown Track"
            )

            duration = info.get("duration") or 0

            return (
                filename,
                title,
                int(duration)
            )

    return await loop.run_in_executor(
        None,
        download
    )


# =========================================================
# SEND AUDIO
# =========================================================

async def send_audio(
    client: Client,
    message: Message,
    file_path: str,
    title: str,
    duration: int
):

    minutes = duration // 60
    seconds = duration % 60

    caption = (
        f"🎵 **{title}**\n\n"
        f"⏱ Davomiyligi: "
        f"`{minutes}:{seconds:02d}`"
    )

    try:

        await client.send_audio(
            chat_id=message.chat.id,
            audio=file_path,
            title=title[:64],
            performer="Music Bot",
            duration=duration if duration > 0 else None,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.id
        )

    except Exception:

        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.id
        )

    finally:

        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception:
            pass


# =========================================================
# START COMMAND
# =========================================================

@app.on_message(filters.command("start"))
async def start_handler(
    client: Client,
    message: Message
):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔍 Qidirish",
                    callback_data="search"
                ),

                InlineKeyboardButton(
                    "📥 Link orqali",
                    callback_data="link"
                )
            ],

            [
                InlineKeyboardButton(
                    "📸 Instagram",
                    url=INSTAGRAM_URL
                ),

                InlineKeyboardButton(
                    "ℹ️ Yordam",
                    callback_data="help"
                )
            ]
        ]
    )

    text = (
        "🎵 **Music Downloader Bot** ga xush kelibsiz!\n\n"

        "Men sizga qo'shiq topib beraman "
        "yoki Instagram / YouTube / TikTok "
        "videolardan audio ajratib beraman.\n\n"

        "**Qanday ishlatish:**\n\n"

        "🎵 Qo'shiq nomini yozing\n"
        "→ audio yuboraman\n\n"

        "🔗 Instagram / YouTube / TikTok "
        "linkini yuboring\n"
        "→ audiosini ajratib beraman."
    )

    await message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


# =========================================================
# BUTTONS
# =========================================================

@app.on_callback_query()
async def callback_handler(
    client: Client,
    callback: CallbackQuery
):

    data = callback.data

    try:

        if data == "help":

            await callback.message.edit_text(
                "📖 **Yordam**\n\n"
                "🎵 Qo'shiq nomini yozing.\n\n"
                "🔗 Yoki YouTube / Instagram / "
                "TikTok linkini yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data == "search":

            await callback.message.edit_text(
                "🔍 **Qidiruv**\n\n"
                "Shunchaki qo'shiq nomini yozing.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data == "link":

            await callback.message.edit_text(
                "📥 **Link orqali yuklash**\n\n"
                "YouTube, Instagram yoki TikTok "
                "linkini yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )

        await callback.answer()

    except Exception as e:

        await callback.answer(
            "Xatolik yuz berdi",
            show_alert=True
        )


# =========================================================
# MAIN MESSAGE
# =========================================================

@app.on_message(
    filters.text & ~filters.command("start")
)
async def main_handler(
    client: Client,
    message: Message
):

    text = message.text.strip()

    if not text:
        return

    status = await message.reply_text(
        "🔍 Qidirilmoqda..."
    )

    file_path = None

    try:

        if is_url(text):

            await status.edit_text(
                "⬇️ Link tahlil qilinmoqda..."
            )

            file_path, title, duration = (
                await download_audio(
                    text,
                    is_search=False
                )
            )

        else:

            await status.edit_text(
                "🔍 Qo'shiq qidirilmoqda..."
            )

            file_path, title, duration = (
                await download_audio(
                    text,
                    is_search=True
                )
            )

        if not file_path or not os.path.exists(file_path):

            await status.edit_text(
                "❌ Audio topilmadi."
            )

            return

        file_size = os.path.getsize(file_path)

        if file_size > 49 * 1024 * 1024:

            os.remove(file_path)

            await status.edit_text(
                "❌ Fayl hajmi 50 MB dan katta."
            )

            return

        await status.edit_text(
            "📤 Audio yuborilmoqda..."
        )

        await send_audio(
            client,
            message,
            file_path,
            title,
            duration
        )

        await status.delete()

    except Exception as e:

        if file_path and os.path.exists(file_path):

            try:
                os.remove(file_path)
            except:
                pass

        await status.edit_text(
            f"❌ **Xatolik:**\n\n"
            f"`{str(e)[:500]}`",
            parse_mode=ParseMode.MARKDOWN
        )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print("🤖 Bot muvaffaqiyatli ishga tushdi...")

    try:
        main_loop = asyncio.get_event_loop()
    except RuntimeError:
        main_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(main_loop)

    app.run()
