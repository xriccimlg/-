import os
import re
import subprocess
import io
import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

token = os.environ['BOT_TOKEN']
admin = os.environ['BOT_ADMIN']
username_regex = re.compile("^[a-zA-Z0-9]+$")
command = 'bash <(curl -sL https://raw.githubusercontent.com/xriccimlg/-/main/reality.sh) '

async def get_users_ezpz():
    local_command = command + '--list-users'
    return await run_command(local_command)

async def get_config_ezpz(username):
    local_command = command + f"--show-user {username} | grep -E '://|^\\{{\"dns\"'"
    return await run_command(local_command)

async def delete_user_ezpz(username):
    local_command = command + f'--delete-user {username}'
    await run_command(local_command)

async def add_user_ezpz(username):
    local_command = command + f'--add-user {username}'
    await run_command(local_command)

async def run_command(command):
    process = subprocess.Popen(['/bin/bash', '-c', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = process.communicate()
    return output.decode().split('\n')[:-1]

def restricted(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        username = None
        if update.message:
            username = update.message.chat.username
        elif update.callback_query and update.callback_query.message:
            username = update.callback_query.message.chat.username
        admin_list = admin.split(',')
        if username in admin_list:
            return await func(update, context, *args, **kwargs)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Вы не авторизованы для использования этого бота.')
    return wrapped

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_text = "Бот управления пользователями Reality-EZPZ\n\nВыберите опцию:"
    keyboard = [
        [InlineKeyboardButton('Показать пользователя', callback_data='show_user')],
        [InlineKeyboardButton('Добавить пользователя', callback_data='add_user')],
        [InlineKeyboardButton('Удалить пользователя', callback_data='delete_user')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=commands_text, reply_markup=reply_markup)

@restricted
async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE, text, callback):
    keyboard = []
    users = await get_users_ezpz()
    for user in users:
        keyboard.append([InlineKeyboardButton(user, callback_data=f'{callback}!{user}')])
    keyboard.append([InlineKeyboardButton('Назад', callback_data='start')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

@restricted
async def show_user(update: Update, context: ContextTypes.DEFAULT_TYPE, username):
    keyboard = [[InlineKeyboardButton('Назад', callback_data='show_user')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Конфигурация для "{username}":', parse_mode='HTML')
    config_list = await get_config_ezpz(username)
    ipv6_pattern = r'"server":"[0-9a-fA-F:]+"'
    
    for config in config_list:
        if config.endswith("-ipv6") or re.search(ipv6_pattern, config):
            config_text = f"IPv6 Конфигурация:\n<pre>{config}</pre>"
        else:
            config_text = f"<pre>{config}</pre>"
        
        qr_img = qrcode.make(config)
        bio = io.BytesIO()
        qr_img.save(bio, 'PNG')
        bio.seek(0)
        
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio, caption=config_text, parse_mode='HTML', reply_markup=reply_markup)

@restricted
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE, username):
    keyboard = []
    if len(await get_users_ezpz()) == 1:
        text = 'Нельзя удалить единственного пользователя.\nНеобходимо хотя бы один пользователь.\nСоздайте нового пользователя, затем удал ите этого.'
        keyboard.append([InlineKeyboardButton('Назад', callback_data='start')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
        return
    text = f'Вы уверены, что хотите удалить "{username}"?'
    keyboard.append([InlineKeyboardButton('Удалить', callback_data=f'approve_delete!{username}')])
    keyboard.append([InlineKeyboardButton('Отмена', callback_data='delete_user')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

@restricted
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = 'Введите имя пользователя:'
    keyboard = [[InlineKeyboardButton('Отмена', callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['expected_input'] = 'username'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

@restricted
async def approve_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, username):
    await delete_user_ezpz(username)
    text = f'Пользователь {username} был удален.'
    keyboard = [[InlineKeyboardButton('Назад', callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

@restricted
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'expected_input' in context.user_data:
        del context.user_data['expected_input']
    await start(update, context)

@restricted
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    response = query.data.split('!')
    if len(response) == 1:
        if response[0] == 'start':
            await start(update, context)
        elif response[0] == 'cancel':
            await cancel(update, context)
        elif response[0] == 'show_user':
            await users_list(update, context, 'Выберите пользователя для просмотра конфигурации:', 'show_user')
        elif response[0] == 'delete_user':
            await users_list(update, context, 'Выберите пользователя для удаления:', 'delete_user')
        elif response[0] == 'add_user':
            await add_user(update, context)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Нажата кнопка: {}'.format(response[0]))
    if len(response) > 1:
        if response[0] == 'show_user':
            await show_user(update, context, response[1])
        if response[0] == 'delete_user':
            await delete_user(update, context, response[1])
        if response[0] == 'approve_delete':
            await approve_delete(update, context, response[1])

@restricted
async def user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'expected_input' in context.user_data:
        expected_input = context.user_data['expected_input']
        del context.user_data['expected_input']
        if expected_input == 'username':
            username = update.message.text
            if username in await get_users_ezpz():
                await update.message.reply_text(f'Пользователь "{username}" уже существует, попробуйте другое имя пользователя.')
                await add_user(update, context)
                return
            if not username_regex.match(username):
                await update.message.reply_text('Имя пользователя может содержать только A-Z, a-z и 0-9, попробуйте другое имя пользователя.')
                await add_user(update, context)
                return
            await add_user_ezpz(username)
            await update.message.reply_text(f'Пользователь "{username}" создан.')
            await show_user(update, context, username)

app = ApplicationBuilder().token(token).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_input))

app.run_polling()
