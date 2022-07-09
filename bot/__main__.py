from signal import signal, SIGINT
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
from sys import executable
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler

from bot import bot, dispatcher, updater, IMAGE_URL, botStartTime, IGNORE_PENDING_REQUESTS, LOGGER, Interval, INCOMPLETE_TASK_NOTIFIER, DB_URI, alive, app, main_loop
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker

from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, delete, count, leech_settings, search, rss


def stats(update, context):
    if ospath.exists('.git'):
        last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd \n<b>From</b> %cr'"], shell=True).decode()
    else:
        last_commit = 'No UPSTREAM_REPO'
    currentTime = get_readable_time(time() - botStartTime)
    osUptime = get_readable_time(time() - boot_time())
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    swap_t = get_readable_file_size(swap.total)
    memory = virtual_memory()
    mem_p = memory.percent
    mem_t = get_readable_file_size(memory.total)
    mem_a = get_readable_file_size(memory.available)
    mem_u = get_readable_file_size(memory.used)
    stats = f'<b>📊 Time Calculation 📊</b>\n\n'\
            f'<b>⏰ Uptime : {currentTime}</b>\n'\
            f'<b>🖥 OS Uptime : {osUptime}</b>\n\n'\
			f'<b>📊 Data Usage 📊</b>\n\n'\
            f'<b>💨 Storage : {total}</b>\n'\
            f'<b>📈 Used : {used}</b>\n<b>📉 Free : {free}</b>\n'\
            f'<b>📤 Upload : {sent}</b>\n<b>📥 Download : {recv}</b>\n\n'\
			f'<b>📊 Performance Meter 📊</b>\n\n'\
            f'<b>🖥 CPU : {cpuUsage}%</b>\n'\
            f'<b>⚙️ RAM : {mem_p}%</b>\n'\
            f'<b>🗃 DISK : {disk}%</b>\n'\
            f'<b>🪅 Physical Cores : {p_core}</b>\n'\
            f'<b>🎛 Total Cores : {t_core}</b>\n'\
            f'<b>🛡 Swap Memory : {swap_t}</b> | <b>⏳ Used : {swap_p}%</b>\n'\
            f'<b>💽 Memory Total : {mem_t}</b>\n'\
            f'<b>📉 Memory Free : {mem_a}</b>\n'\
            f'<b>📈 Memory Used : {mem_u}</b>\n'
    update.effective_message.reply_photo(IMAGE_URL, stats, parse_mode='HTMl')

def start(update, context):
    buttons = ButtonMaker()

    buttons.buildbutton("😎 My Creator 😎", "https://t.me/hilmay619")

    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        start_string = f'''
Welcome | I'm Ready Help You 😊
Type /{BotCommands.HelpCommand} To View Available Commands
'''
        update.effective_message.reply_photo(IMAGE_URL, start_string, parse_mode = 'Markdown', reply_markup=reply_markup)
    else:
        sendMarkup('<b>🚫 Oops! You Are Not Authorized User 🚫</b>', context.bot, update.message, reply_markup)

def restart(update, context):
    restart_message = sendMessage("<b>🔄 Restarting, Please Wait! 🔄</b>", context.bot, update.message)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    alive.kill()
    clean_all()
    srun(["pkill", "-9", "-f", "gunicorn|extra-api|last-api|megasdkrest|new-api"])
    srun(["python3", "update.py"])
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    osexecl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update.message)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)


help_string_telegraph = f'''<br>
<b>/{BotCommands.HelpCommand}</b>: Show Available Commands
<br><br>
<b>/{BotCommands.MirrorCommand}</b> : Start Mirroring
<br><br>
<b>/{BotCommands.ZipMirrorCommand}</b> : Start Mirroring and Upload as .Zip
<br><br>
<b>/{BotCommands.UnzipMirrorCommand}</b> : Start Mirroring and Upload as Archive or Extracted Folder/File
<br><br>
<b>/{BotCommands.QbMirrorCommand}</b> : Start Mirroring Using qBittorrent
<br><br>
<b>/{BotCommands.QbZipMirrorCommand}</b> : Start Mirroring Using qBittorrent and Upload as .Zip
<br><br>
<b>/{BotCommands.QbUnzipMirrorCommand}</b> : Start Mirroring Using qBittorrent and Upload as Archive or Extracted Folder/File
<br><br>
<b>/{BotCommands.LeechCommand}</b> : Start Upload/Leech File to Telegram
<br><br>
<b>/{BotCommands.ZipLeechCommand}</b> : Start Upload/Leech File to Telegram and Upload as .Zip
<br><br>
<b>/{BotCommands.UnzipLeechCommand}</b> : Start Upload/Leech File to Telegram and Upload as Archive or Extracted Folder/File
<br><br>
<b>/{BotCommands.QbLeechCommand}</b> : Start Upload/Leech to Telegram Using qBittorrent
<br><br>
<b>/{BotCommands.QbZipLeechCommand}</b> : Start Upload/Leech to Telegram Using qBittorrent and Upload as .Zip
<br><br>
<b>/{BotCommands.QbUnzipLeechCommand}</b> : Start Upload/Leech to Telegram Using qBittorrent and Upload as Archive or Extracted Folder/File
<br><br>
<b>/{BotCommands.CloneCommand}</b> : Copy File/Folder to Google Drive
<br><br>
<b>/{BotCommands.CountCommand}</b> : Count File/Folder of Google Drive
<br><br>
<b>/{BotCommands.DeleteCommand}</b> : Delete File/Folder From Google Drive
<br><br>
<b>/{BotCommands.WatchCommand}</b> : Mirror YTDL Supported Link.
<br><br>
<b>/{BotCommands.ZipWatchCommand}</b> : Mirror YTDL Supported Link and Upload as .Zip
<br><br>
<b>/{BotCommands.LeechWatchCommand}</b> : Upload/Leech YTDL Supported Link to Telegram
<br><br>
<b>/{BotCommands.LeechZipWatchCommand}</b> : Upload/Leech YTDL Supported Link to Telegram and Upload as .Zip
<br><br>
<b>/{BotCommands.CancelMirror}</b>: Reply to the Message or Using /{BotCommands.CancelMirror} GID
<br><br>
<b>/{BotCommands.CancelAllCommand}</b>: Force Cancel All Downloading
<br><br>
<b>/{BotCommands.ListCommand}</b> : Search File/Folder in Google Drive
<br><br>
<b>/{BotCommands.SearchCommand}</b> : Search for torrents with API
<br><br>
<b>/{BotCommands.StatusCommand}</b> : Shows a Status of All The Downloads
<br><br>
<b>/{BotCommands.StatsCommand}</b> : Show Stats of the System
<br><br>
<b>/{BotCommands.LeechSetCommand}</b>: Leech Settings
<br><br>
<b>/{BotCommands.SetThumbCommand}</b>: Reply Photo to Set Thumbnail
<br><br>
<b>/{BotCommands.RssListCommand}</b> : List All Subscribed RSS Feed
<br><br>
<b>/{BotCommands.RssGetCommand}</b> : Force Fetch Last N Links
<br><br>
<b>/{BotCommands.RssSubCommand}</b> : Subscribe New RSS Feed
<br><br>
<b>/{BotCommands.RssUnSubCommand}</b> : Unubscribe RSS Feed by Title
<br><br>
<b>/{BotCommands.RssSettingsCommand}</b>: RSS Settings
'''

help = telegraph.create_page(
        title='Telegraph Search x Google Drive',
        content=help_string_telegraph,
    )["path"]

help_string = f'''

Only For Admin & Sudo User

/{BotCommands.PingCommand} : Check Active

/{BotCommands.AuthorizeCommand} : Authorize A Chat or User to Use The Bot

/{BotCommands.UnAuthorizeCommand} : Unauthorize A Chat or User to Use The Bot

/{BotCommands.AuthorizedUsersCommand} : Show Authorized Chat or Users

/{BotCommands.AddSudoCommand} : Add Sudo Permission

/{BotCommands.RmSudoCommand} : Remove Sudo Permission

/{BotCommands.RestartCommand} : Restart System

/{BotCommands.LogCommand} : Get .Log For Getting Crash Reports
'''

def bot_help(update, context):
    button = ButtonMaker()
    button.buildbutton("🪧 Users Commands 🪧", f"https://telegra.ph/{help}")
    reply_markup = InlineKeyboardMarkup(button.build_menu(1))
    sendMarkup(help_string, context.bot, update.message, reply_markup)

def main():
    start_cleanup()
    if INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
        notifier_dict = DbManger().get_incomplete_tasks()
        if notifier_dict:
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = 'Restarted successfully!'
                else:
                    msg = 'Bot Restarted!'
                for tag, links in data.items():
                     msg += f"\n\n{tag}: "
                     for index, link in enumerate(links, start=1):
                         msg += f" <a href='{link}'>{index}</a> |"
                         if len(msg.encode()) > 4000:
                             if 'Restarted successfully!' in msg and cid == chat_id:
                                 bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                                 osremove(".restartmsg")
                             else:
                                 try:
                                     bot.sendMessage(cid, msg, 'HTML')
                                 except Exception as e:
                                     LOGGER.error(e)
                             msg = ''
                if 'Restarted successfully!' in msg and cid == chat_id:
                     bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                     osremove(".restartmsg")
                else:
                    try:
                        bot.sendMessage(cid, msg, 'HTML')
                    except Exception as e:
                        LOGGER.error(e)

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text("✅ Restarted Successfully! ✅", chat_id, msg_id)
        osremove(".restartmsg")

    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                  bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

app.start()
main()

main_loop.run_forever()
