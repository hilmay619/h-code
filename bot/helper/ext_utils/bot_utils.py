from re import match as re_match, findall as re_findall
from threading import Thread, Event
from time import time
from math import ceil
from html import escape
from psutil import virtual_memory, cpu_percent, disk_usage
from requests import head as rhead
from urllib.request import urlopen
from telegram import InlineKeyboardMarkup
from bot import download_dict, download_dict_lock, STATUS_LIMIT, botStartTime, DOWNLOAD_DIR
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
import shutil
import psutil
from telegram.error import RetryAfter
from telegram.ext import CallbackQueryHandler
from telegram.message import Message
from telegram.update import Update
from bot import *

MAGNET_REGEX = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"

URL_REGEX = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+"

COUNT = 0
PAGE_NO = 1


class MirrorStatus:
    STATUS_UPLOADING = "Uploading. . . 📤"
    STATUS_DOWNLOADING = "Downloading. . . 📥"
    STATUS_CLONING = "Cloning. . . ♻️"
    STATUS_WAITING = "Queued. . . 💤"
    STATUS_FAILED = "Failed 🚫. Cleaning Download. . . 🚫"
    STATUS_PAUSE = "Paused. . . ⛔️"
    STATUS_ARCHIVING = "Archiving. . . 🔐"
    STATUS_EXTRACTING = "Extracting. . . 📂"
    STATUS_SPLITTING = "Splitting. . . ✂️"
    STATUS_CHECKING = "Checking. . . 📝"
    STATUS_SEEDING = "Seeding. . . 🌧"

class EngineStatus:
    STATUS_ARIA = "Aria2c V.1.35.0"
    STATUS_GD = "Google Drive API V.2.51.0"
    STATUS_MEGA = "MegaSDK V.3.12.0"
    STATUS_QB = "qBitTorrent V.4.3.9"
    STATUS_TG = "Pyrogram V.2.0.27"
    STATUS_YT = "YTDL V.22.5.18"
    STATUS_EXT = "Extract | pExtract"
    STATUS_SPLIT = "FFmpeg V.2.9.1"
    STATUS_ZIP = "p7zip V.16.02"

PROGRESS_MAX_SIZE = 100 // 9
PROGRESS_INCOMPLETE = ['◔', '◔', '◑', '◑', '◑', '◕', '◕']

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = Event()
        thread = Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time() + self.interval
        while not self.stopEvent.wait(nextTime - time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'

def getDownloadByGid(gid):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            status = dl.status()
            if (
                status
                not in [
                    MirrorStatus.STATUS_ARCHIVING,
                    MirrorStatus.STATUS_EXTRACTING,
                    MirrorStatus.STATUS_SPLITTING,
                ]
                and dl.gid() == gid
            ):
                return dl
    return None

def getAllDownload(req_status: str):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            status = dl.status()
            if status not in [MirrorStatus.STATUS_ARCHIVING, MirrorStatus.STATUS_EXTRACTING, MirrorStatus.STATUS_SPLITTING] and dl:
                if req_status == 'down' and (status not in [MirrorStatus.STATUS_SEEDING,
                                                            MirrorStatus.STATUS_UPLOADING,
                                                            MirrorStatus.STATUS_CLONING]):
                    return dl
                elif req_status == 'up' and status == MirrorStatus.STATUS_UPLOADING:
                    return dl
                elif req_status == 'clone' and status == MirrorStatus.STATUS_CLONING:
                    return dl
                elif req_status == 'seed' and status == MirrorStatus.STATUS_SEEDING:
                    return dl
                elif req_status == 'all':
                    return dl
    return None

def get_progress_bar_string(status):
    completed = status.processed_bytes() / 8
    total = status.size_raw() / 8
    p = 0 if total == 0 else round(completed * 100 / total)
    p = min(max(p, 0), 100)
    cFull = p // 8
    cPart = p % 8 - 1
    p_str = '●' * cFull
    if cPart >= 0:
        p_str += PROGRESS_INCOMPLETE[cPart]
    p_str += '○' * (PROGRESS_MAX_SIZE - cFull)
    p_str = f"「{p_str}」"
    return p_str

def get_readable_message():
    with download_dict_lock:
        msg = ""
        if STATUS_LIMIT is not None:
            tasks = len(download_dict)
            global pages
            pages = ceil(tasks/STATUS_LIMIT)
            if PAGE_NO > pages and pages != 0:
                globals()['COUNT'] -= STATUS_LIMIT
                globals()['PAGE_NO'] -= 1
        for index, download in enumerate(list(download_dict.values())[COUNT:], start=1):
            msg += f"<b>📄 Name :-</b> <code>{escape(str(download.name()))}</code>"
            msg += f"\n<b>🗃️ Total Size :- {download.size()}</b>"
            msg += f"\n<b>🌀 Status :- {download.status()}</b>"
            if download.status() not in [
                MirrorStatus.STATUS_ARCHIVING,
                MirrorStatus.STATUS_EXTRACTING,
                MirrorStatus.STATUS_SPLITTING,
                MirrorStatus.STATUS_SEEDING,
            ]:
                msg += f"\n🚀 <b>{get_progress_bar_string(download)} {download.progress()}</b> 💨"
                if download.status() == MirrorStatus.STATUS_CLONING:
                    msg += f"\n♻️ <b>Cloned :- {get_readable_file_size(download.processed_bytes())} of {download.size()}</b>"
                elif download.status() == MirrorStatus.STATUS_UPLOADING:
                    msg += f"\n🔺 <b>Uploaded :- {get_readable_file_size(download.processed_bytes())} of {download.size()}</b>"
                else:
                    msg += f"\n🔻 <b>Downloaded :- {get_readable_file_size(download.processed_bytes())} of {download.size()}</b>"
                msg += f"\n<b>⚡️ Speed :- {download.speed()}</b>" \
                           f"\n<b>⌛️ Estimated :- {download.eta()}</b>"
                msg += f"\n<b>⏳ Elapsed :- {get_readable_time(time() - download.message.date.timestamp())}</b>"
                msg += f'\n<b>👨‍⚖️ Users :- <a href="https://t.me/c/{str(download.message.chat.id)[4:]}/{download.message.message_id}">{download.message.from_user.first_name}</a></b> ✨'
                msg += f"\n<b>🐍 Python :- {download.eng()}</b>"
                try:
                    msg += f"\n<b>🔍 Tracker :- 🧲 Seeds :- {download.aria_download().num_seeders}</b>" \
                            f" | <b>🧲 Peers :- {download.aria_download().connections}</b>"
                except:
                    pass
                try:
                    msg += f"\n<b>🔍 Tracker :- 🧲 Seeds :- {download.torrent_info().num_seeds}</b>" \
                            f" | <b>🧲 Leechs :- {download.torrent_info().num_leechs}</b>"
                except:
                    pass
                msg += f"\n<b>🔰 GID :- {download.gid()}</b>" \
                       f"\n<b>🚫 Cancel :-</b> <code>/{BotCommands.CancelMirror} {download.gid()}</code>" \
                       f"\n\n"

            elif download.status() == MirrorStatus.STATUS_SEEDING:
                msg += f"\n<b>🗃️ Size :- {download.size()}</b>"
                msg += f"\n<b>🐍 Python :- qBittorrent V.4.4.2</b>"
                msg += f"\n<b>⚡️ Speed :- {get_readable_file_size(download.torrent_info().upspeed)}/s</b>"
                msg += f" | <b>🔺 Uploaded:- {get_readable_file_size(download.torrent_info().uploaded)}</b>"
                msg += f"\n<b>🌧 Ratio :- {round(download.torrent_info().ratio, 3)}</b>"
                msg += f" | <b>⏰ Time :- {get_readable_time(download.torrent_info().seeding_time)}</b>"
                msg += f"\n<b>🚫 Cancel :-</b> <code>/{BotCommands.CancelMirror} {download.gid()}</code>"
                msg += f"\n\n"
            else:
                msg += f"\n<b>🗃️ Size :- {download.size()}</b>"
                msg += f"\n<b>🐍 Python :- {download.eng()}</b>"
                msg += "\n\n"
            if STATUS_LIMIT is not None and index == STATUS_LIMIT:
                break
        bmsg = f"<b>📊 Performance Meter 📊</b>\n\n<b>🖥 CPU            :- {cpu_percent()}%</b>\n<b>🗃 DISK           :- {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}</b>"
        bmsg += f"\n<b>⚙️ RAM           :- {virtual_memory().percent}%</b>\n<b>⏰ UPTIME     :- {get_readable_time(time() - botStartTime)}</b>"
        dlspeed_bytes = 0
        upspeed_bytes = 0
        for download in list(download_dict.values()):
            spd = download.speed()
            if download.status() == MirrorStatus.STATUS_DOWNLOADING:
                if 'K' in spd:
                    dlspeed_bytes += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    dlspeed_bytes += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_UPLOADING:
                if 'KB/s' in spd:
                    upspeed_bytes += float(spd.split('K')[0]) * 1024
                elif 'MB/s' in spd:
                    upspeed_bytes += float(spd.split('M')[0]) * 1048576
        bmsg += f"\n\n<b>⚡️ Internet Speed Meter ⚡️</b>\n\n<b>🔻 D :- {get_readable_file_size(dlspeed_bytes)}/s</b> | <b>🔺 U :- {get_readable_file_size(upspeed_bytes)}/s</b>"

        buttons = ButtonMaker()
        buttons.sbutton("📊 Statistics 📊", str(THREE))
        sbutton = InlineKeyboardMarkup(buttons.build_menu(1))

        if STATUS_LIMIT is not None and tasks > STATUS_LIMIT:
            msg += f"<b>📌 Page :- {PAGE_NO}/{pages}</b> | <b>🔖 Tasks :- {tasks}</b>\n\n"
            buttons = ButtonMaker()
            buttons.sbutton("↩️ Previous ↩️", "status pre")
            buttons.sbutton(f"{PAGE_NO}/{pages}", str(THREE))
            buttons.sbutton("↪️ Next ↪️", "status nex")
            button = InlineKeyboardMarkup(buttons.build_menu(3))
            return msg + bmsg, button
        return msg + bmsg, sbutton

def turn(data):
    try:
        with download_dict_lock:
            global COUNT, PAGE_NO
            if data[1] == "nex":
                if PAGE_NO == pages:
                    COUNT = 0
                    PAGE_NO = 1
                else:
                    COUNT += STATUS_LIMIT
                    PAGE_NO += 1
            elif data[1] == "pre":
                if PAGE_NO == 1:
                    COUNT = STATUS_LIMIT * (pages - 1)
                    PAGE_NO = pages
                else:
                    COUNT -= STATUS_LIMIT
                    PAGE_NO -= 1
        return True
    except:
        return False

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days} Days '
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours} Hours '
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes} Minutes '
    seconds = int(seconds)
    result += f'{seconds} Seconds '
    return result

def is_url(url: str):
    url = re_findall(URL_REGEX, url)
    return bool(url)

def is_gdrive_link(url: str):
    return "drive.google.com" in url

def is_gdtot_link(url: str):
    url = re_match(r'https?://.+\.gdtot\.\S+', url)
    return bool(url)

def is_appdrive_link(url: str):
    url = re_match(r'https?://(?:\S*\.)?(?:appdrive|driveapp)\.in/\S+', url)
    return bool(url)

def is_mega_link(url: str):
    return "mega.nz" in url or "mega.co.nz" in url

def get_mega_link_type(url: str):
    if "folder" in url:
        return "folder"
    elif "file" in url:
        return "file"
    elif "/#F!" in url:
        return "folder"
    return "file"

def is_magnet(url: str):
    magnet = re_findall(MAGNET_REGEX, url)
    return bool(magnet)

def new_thread(fn):
    """To use as decorator to make a function call threaded.
    Needs import
    from threading import Thread"""

    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper

def get_content_type(link: str) -> str:
    try:
        res = rhead(link, allow_redirects=True, timeout=5, headers = {'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            info = res.info()
            content_type = info.get_content_type()
        except:
            content_type = None
    return content_type

ONE, TWO, THREE = range(3)
def pop_up_stats(update, context):
    query = update.callback_query
    stats = bot_sys_stats()
    query.answer(text=stats, show_alert=True)
def bot_sys_stats():
    currentTime = get_readable_time(time() - botStartTime)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage(DOWNLOAD_DIR).percent
    total, used, free = shutil.disk_usage(DOWNLOAD_DIR)
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    num_active = 0
    num_upload = 0
    num_split = 0
    num_extract = 0
    num_archi = 0
    tasks = len(download_dict)
    for stats in list(download_dict.values()):
       if stats.status() == MirrorStatus.STATUS_DOWNLOADING:
                num_active += 1
       if stats.status() == MirrorStatus.STATUS_UPLOADING:
                num_upload += 1
       if stats.status() == MirrorStatus.STATUS_ARCHIVING:
                num_archi += 1
       if stats.status() == MirrorStatus.STATUS_EXTRACTING:
                num_extract += 1
       if stats.status() == MirrorStatus.STATUS_SPLITTING:
                num_split += 1
    stats = f""
    stats += f"""

⏰ Uptime :- {currentTime}
📥 Download :- {recv}
📤 Upload :- {sent}
🖥 CPU :- {cpu}%
⚙️ RAM :- {mem}%
🗃 Disk :- {total}
📈 Disk Used :- {used}
📉 Disk Free :- {free}

"""
    return stats
dispatcher.add_handler(
    CallbackQueryHandler(pop_up_stats, pattern="^" + str(THREE) + "$")
)
