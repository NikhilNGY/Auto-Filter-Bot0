import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle, __version__
from pyrogram.raw.all import layer
import time
import asyncio
from datetime import date, datetime
import pytz
from aiohttp import web
from database.ia_filterdb import Media, Media2
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium 
from Lucia.Bot import SilentX
from Lucia.util.keepalive import ping_server
from Lucia.Bot.clients import initialize_clients
import pyrogram.utils
import threading
import os
import requests
from logging_helper import LOGGER

botStartTime = time.time()
ppath = "plugins/*.py"
files = glob.glob(ppath)

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

PORT = int(os.getenv('PORT', 8080))
PING_URL = f"http://127.0.0.1:{PORT}/"

def ping_loop():
    LOGGER.info(f"💡 Ping URL: {PING_URL}")
    while True:
        try:
            r = requests.get(PING_URL, timeout=10)
            if r.status_code == 200:
                LOGGER.info("✅ Ping Successful")
            else:
                LOGGER.error(f"⚠️ Ping Failed: {r.status_code}")
        except Exception as e:
            LOGGER.error(f"❌ Exception During Ping: {e}")
        time.sleep(120)

threading.Thread(target=ping_loop, daemon=True).start()

async def SilentXBotz_start():
    LOGGER.info('Initializing Your Bot!')
    await SilentX.start()
    bot_info = await SilentX.get_me()
    SilentX.username = bot_info.username
    await initialize_clients()

    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            LOGGER.info(f"Import Plugin - {plugin_name}")

    if ON_HEROKU:
        asyncio.create_task(ping_server()) 

    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    await Media.ensure_indexes()
    if MULTIPLE_DB:
        await Media2.ensure_indexes()
        LOGGER.info("Multiple DB Mode ON: Second DB used if first is full.")
    else:
        LOGGER.info("Single DB Mode ON: Files saved in first DB.")

    me = await SilentX.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    SilentX.username = '@' + me.username

    SilentX.loop.create_task(check_expired_premium(SilentX))

    LOGGER.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
    LOGGER.info(script.LOGO)

    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M:%S %p")

    await SilentX.send_message(
        chat_id=LOG_CHANNEL,
        text=script.RESTART_TXT.format(temp.B_LINK, today, current_time)
    )

    for admin in ADMINS:
        try:
            await SilentX.send_message(
                chat_id=admin,
                text=f"<b>๏[-ิ_•ิ]๏ {me.mention} Restarted ✅</b>"
            )
        except Exception as e:
            LOGGER.warning(f"Failed to notify admin {admin}: {e}")

    app = web.AppRunner(await web_server())
    await app.setup()
    await web.TCPSite(app, "0.0.0.0", PORT).start()
    LOGGER.info(f"Web server running on http://0.0.0.0:{PORT}/")

    await idle()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(SilentXBotz_start())
    except KeyboardInterrupt:
        LOGGER.info('Service Stopped. Bye 👋')