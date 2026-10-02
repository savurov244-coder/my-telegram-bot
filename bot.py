import os
import re
import asyncio
import tempfile
from pathlib import Path
from threading import Thread

from flask import Flask
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
# WEB SERVER (RENDER PORT BINDING FIX)
# =========================================================

web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# Serverni orqa fonda ishga tushirish
Thread(target=run_web, daemon=True).start()


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
# FAST SEARCH (10 RESULTS)
# =========================================================

async def search_yt(query: str):
    search_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def fetch():
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            res = ydl.extract_info(f"ytsearch10:{query}", download=False)
            results = []
            if "entries" in res:
                for entry in res["entries"]:
                    if entry:
                        results.append({
                            "id": entry.get("id"),
                            "title": entry.get("title") or "Noma'lum ijro",
                            "duration": entry.get("duration") or 0
                        })
            return results

    return await loop.run_in_executor(None, fetch)


# =========================================================
# DOWNLOAD AUDIO BY ID OR URL
# =========================================================

async def download_audio(target: str):
    options = YDL_OPTS.copy()

    if is_url(target):
        url = target
    else:
        url = f"https://www.youtube.com/watch?v={target}"

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def download():
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

            if "entries" in info:
                info = info["entries"][0]

            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in [".m4a", ".webm", ".opus", ".ogg", ".mp3", ".mp4"]:
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

            return filename, title, int(duration)

    return await loop.run_in_executor(None, download)


# =========================================================
# SEND AUDIO
# =========================================================

async def send_audio(
    client: Client,
    chat_id: int,
    reply_to_id: int,
    file_path: str,
    title: str,
    duration: int
):
    minutes = duration // 60
    seconds = duration % 60

    caption = (
        f"🎵 **{title}**\n\n"
        f"⏱ Davomiyligi: `{minutes}:{seconds:02d}`"
    )

    try:
        await client.send_audio(
            chat_id=chat_id,
            audio=file_path,
            title=title[:64],
            performer="Music Bot",
            duration=duration if duration > 0 else None,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=reply_to_id
        )
    except Exception:
        await client.send_document(
            chat_id=chat_id,
            document=file_path,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=reply_to_id
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
async def start_handler(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔍 Qidirish", callback_data="search"),
                InlineKeyboardButton("📥 Link orqali", callback_data="link")
            ],
            [
                InlineKeyboardButton("📸 Instagram", url=INSTAGRAM_URL),
                InlineKeyboardButton("ℹ️ Yordam", callback_data="help")
            ]
        ]
    )

    text = (
        "🎵 **Music Downloader Bot** ga xush kelibsiz!\n\n"
        "Men sizga qo'shiq topib beraman yoki Instagram / YouTube / TikTok "
        "videolardan audio ajratib beraman.\n\n"
        "**Qanday ishlatish:**\n\n"
        "🎵 Qo'shiq nomini yozing → 10 ta natija chiqaraman\n"
        "🔗 Link yuboring → audiosini ajratib beraman."
    )

    await message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

@app.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):
    data = callback.data

    try:
        if data == "help":
            await callback.message.edit_text(
                "📖 **Yordam**\n\n"
                "🎵 Qo'shiq nomini yozing, bot 10 ta natija beradi.\n\n"
                "🔗 Yoki YouTube / Instagram / TikTok linkini yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data == "search":
            await callback.message.edit_text(
                "🔍 **Qidiruv**\n\nShunchaki qo'shiq nomini yozing.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data == "link":
            await callback.message.edit_text(
                "📥 **Link orqali yuklash**\n\n"
                "YouTube, Instagram yoki TikTok linkini yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif data.startswith("dl_"):
            yt_id = data.split("dl_")[1]

            await callback.message.edit_text("⬇️ Qo'shiq yuklanmoqda...")

            file_path = None
            try:
                file_path, title, duration = await download_audio(yt_id)

                if not file_path or not os.path.exists(file_path):
                    await callback.message.edit_text("❌ Audio topilmadi.")
                    return

                file_size = os.path.getsize(file_path)
                if file_size > 49 * 1024 * 1024:
                    os.remove(file_path)
                    await callback.message.edit_text("❌ Fayl hajmi 50 MB dan katta.")
                    return

                await callback.message.edit_text("📤 Audio yuborilmoqda...")

                await send_audio(
                    client,
                    callback.message.chat.id,
                    callback.message.id,
                    file_path,
                    title,
                    duration
                )

                await callback.message.delete()

            except Exception as e:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                await callback.message.edit_text(
                    f"❌ **Xatolik:**\n\n`{str(e)[:500]}`",
                    parse_mode=ParseMode.MARKDOWN
                )

        await callback.answer()

    except Exception:
        await callback.answer("Xatolik yuz berdi", show_alert=True)


# =========================================================
# MAIN MESSAGE HANDLER
# =========================================================

@app.on_message(filters.text & ~filters.command("start"))
async def main_handler(client: Client, message: Message):
    text = message.text.strip()

    if not text:
        return

    status = await message.reply_text("🔍 Qidirilmoqda...")

    try:
        if is_url(text):
            await status.edit_text("⬇️ Link tahlil qilinmoqda...")
            file_path, title, duration = await download_audio(text)

            if not file_path or not os.path.exists(file_path):
                await status.edit_text("❌ Audio topilmadi.")
                return

            file_size = os.path.getsize(file_path)
            if file_size > 49 * 1024 * 1024:
                os.remove(file_path)
                await status.edit_text("❌ Fayl hajmi 50 MB dan katta.")
                return

            await status.edit_text("📤 Audio yuborilmoqda...")
            await send_audio(
                client,
                message.chat.id,
                message.id,
                file_path,
                title,
                duration
            )
            await status.delete()

        else:
            await status.edit_text("🔍 Qo'shiqlar topilmoqda...")
            results = await search_yt(text)

            if not results:
                await status.edit_text("❌ Hech narsa topilmadi.")
                return

            buttons = []
            for idx, item in enumerate(results, start=1):
                m = item['duration'] // 60
                s = item['duration'] % 60
                btn_text = f"{idx}. {item['title'][:35]} ({m}:{s:02d})"
                buttons.append([
                    InlineKeyboardButton(btn_text, callback_data=f"dl_{item['id']}")
                ])

            keyboard = InlineKeyboardMarkup(buttons)
            await status.edit_text(
                f"🔎 **\"{text}\"** bo'yicha topilgan qo'shiqlar:\n\n"
                f"Keraklisini tanlang 👇",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        await status.edit_text(
            f"❌ **Xatolik:**\n\n`{str(e)[:500]}`",
            parse_mode=ParseMode.MARKDOWN
        )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    print("🤖 Bot muvaffaqiyatli ishga tushdi...")
    app.run()
