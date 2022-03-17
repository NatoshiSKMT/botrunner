#!/usr/bin/env python
"""This application provides the launch of a telegram bot"""
import sys
import logging
import time
from datetime import datetime, timezone
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode, ChatAction
import yaml
from threading import Timer
from pymongo import MongoClient
from functools import wraps


def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func


# Set up the logger
#filename = 'log.log'
filename = None
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=filename)
logger = logging.getLogger(__name__)

# Loading configuration
try:
    config = yaml.safe_load(open("config.yml", "r", encoding="utf-8"))
except FileNotFoundError:
    logger.error("Fail to open config.yml")
    exit()
else:
    logger.info("Configuration loaded from config.yml")

# Connect to MongoDB
try:
    conn = MongoClient()
    logger.info("MongoDB connected!")
    db = conn.database
    chats_collection = db.booksbot
except:
    logger.error("Could not connect to MongoDB")
    
# Run telegram bot
try:
    updater = Updater(token=config['token'], use_context=True)
    updater.start_polling()
    dispatcher = updater.dispatcher
except Exception:
    logger.exception("Bot is NOT running")
    sys.exit()
else:
    logger.info("Bot is running")


class Chat():
    """
        Class for operate with telegram chats
        
    """
    def __init__(self, tg_chat_id):
        super(Chat, self).__init__()
        self.tg_chat_id = tg_chat_id
        self.state = {
            "status": "new",
            "tags": [],
            "books_sent_ids": [],
            "last_adv": datetime.now().timestamp(),
            "nickname": "",
        }
        
        # Create if new user
        chat_in_db = chats_collection.find_one({"_id": tg_chat_id})
        if chat_in_db is None:
            ??????
        
        
        if chat_in_db is None:
            chats_collection.insert_one({
                "_id": tg_chat_id,
                "state": self.state,
            })
        # Load from DB
        else:
            self.state = chat_in_db['state']
        

    def set_state(self, name, value):
        self.state[name] = value
        chats_collection.update_one({ "_id": self.tg_chat_id }, { "$set": {"state": self.state }})
    
    def add_item(self, name, item):
        self.state[name].append(item)
        chats_collection.update_one({ "_id": self.tg_chat_id }, { "$set": {"state": self.state }})

@send_typing_action
def ontext(update, context):
    """ Processing all patterns on text messages """
    # Ignore edited message
    if not update.message:
        logger.debug("Edited message ignored")
        return

    # Ignore old messages
    if (datetime.now(timezone.utc) - update.message.date).total_seconds() > 5:
        logger.debug("Old message ignored")
        return

    text = update.message.text
    tg_chat_id = update.message.from_user.id
    current_chat = load_chat(tg_chat_id)    
    logger.info("{}({}): {}".format(tg_chat_id, update.message.from_user.username, text)) 
    
    if (text == 'status') and (tg_chat_id in config['admins']):
        for tg_chat_id, chat in Chats.items():
            print(tg_chat_id, chat.state)
            return
    
    if (text == 'DROPDATABASE') and (tg_chat_id in config['admins']):
        for tg_chat_id, chat in Chats.items():
            chats_collection.delete_many({})
            updater.bot.send_message(chat.tg_chat_id, f"Done. /start", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            return
    
    if text == 'all' and (tg_chat_id in config['admins']):
        chat = current_chat
        for book in config['books']:
            title = book['name']
            description = book['description'].replace('\n', '\n\n')    
            updater.bot.send_message(chat.tg_chat_id, f"<b>{title}</b>\n {description}", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            if 'file' in book:
                updater.bot.send_document(chat.tg_chat_id, document=open(book['file'], 'rb'), caption="Файл с карточками")
        return
    
    if text == '/stat' and (tg_chat_id in config['admins']):
        stats = {}
        
        stats['total'] = Chats.__len__()
        stats['wait'] = chats_collection.count_documents({"state.status": "wait"})
        stats['new'] = chats_collection.count_documents({"state.status": "new"})
        stats['books'] = 0
        for chat in Chats.values():
            stats['books'] += len(chat.state['books_sent_ids'])
        reply_text = f"<b>Статистика бота</b>\n\n"
        reply_text += f"Всего чатов: {stats['total']}\n"
        reply_text += f"Не прошли отпрос: {stats['new']}\n"
        reply_text += f"Прошли опрос и получили рекомендацию: {stats['wait']}\n"
        reply_text += f"Всего книг отправлено: {stats['books']}\n"
        updater.bot.send_message(tg_chat_id, reply_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return
    
    if text.startswith('РАССЫЛКА') and (tg_chat_id in config['admins']):
        chat = current_chat
        title = "Черновик сообщения"
        spam = text.replace('РАССЫЛКА','')
        chat.set_state('spam', spam)
        
        keyboard = [
            [InlineKeyboardButton("Отправить ВСЕМ", callback_data='do_spam')],
            [InlineKeyboardButton("Отмена", callback_data='nothing')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        updater.bot.send_message(chat.tg_chat_id, f"<b>{title}</b>\n {spam}", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
        return

    # temporary solution
    if config['access_codes'].__len__() > 0:
        if text.startswith('/start'):
            access_string = text.split(' ')
            if access_string.__len__() == 2:
                if access_string[1] in config['access_codes']:
                    current_chat.set_state('access_code', access_string[1])
                    text = access_string[0]
                    print(text)
                else:
                    updater.bot.send_message(tg_chat_id, "Неверный код доступа")
                    return
            else:
                updater.bot.send_message(tg_chat_id, "Пустой код доступа")
                return

        if text.startswith('/restart'):
            if 'access_code' not in current_chat.state:
                updater.bot.send_message(tg_chat_id, "Пустой код доступа")
                return
            if current_chat.state['access_code'] not in config['access_codes']:
                updater.bot.send_message(tg_chat_id, "Неверный код доступа")
                return
        
    reply_text = config['default_replay']
    keyboard = []
    for reaction in config['reactions']:
        if reaction['comand'] == text:
            reply_text = reaction['replay']
            if 'buttons' in reaction:
                for button in reaction['buttons']:
                    keyboard.append([InlineKeyboardButton(button['button'], callback_data=button['callback'])])

    reply_markup = InlineKeyboardMarkup(keyboard)

    time.sleep(config['typing_timer'])
    update.message.reply_text(reply_text, reply_markup=reply_markup)
    logger.info(f"REPLY: {reply_text}")
    return True

@send_typing_action
def button(update: Update, context: CallbackContext):
    """Parses the CallbackQuery and updates the message text."""
    update.callback_query.answer()

    user_selected_oprion = ''
    for onerow in update.callback_query.message.reply_markup.inline_keyboard:
        for onekey in onerow:
            if onekey['callback_data'] == update.callback_query.data:
                user_selected_oprion = onekey['text']

    tg_chat_id = update.callback_query.message.chat.id
    tmp = update.callback_query.data.split("||")
    button = tmp[0]
    
    #todo fix user name
    logger.info("{}({}): {}".format(tg_chat_id, update.callback_query.message.from_user.username, button))
    current_chat = load_chat(tg_chat_id)

    try:
        data = tmp[1]
    except IndexError:
        data = None
        pass
    
    if button == 'do_spam' and (tg_chat_id in config['admins']):
        spam = current_chat.state['spam']
        ok = 0
        fail = 0
        for chat_id in Chats:
            try:
                updater.bot.send_message(chat_id, f"{spam}", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                ok += 1
            except:
                fail +=1
        updater.bot.send_message(current_chat.tg_chat_id, f"Удачно отправлено: {ok}\nОшибок: {fail}", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return
    
    if data is not None:
        for namevalue in data.split(','):
            try:
                tmp = namevalue.split(':')
                if tmp[0] == 'tag':
                    current_chat.add_item('tags', tmp[1])
                else:
                    current_chat.set_state(tmp[0], tmp[1])
                    
                # reset
                if namevalue == 'status:new':
                    current_chat.state['tags'] = []
                    current_chat.state['books_sent_ids'] = []
                
            except IndexError:
                print("Err", data)
                pass

    reply_text = 'Unknown callback'
    keyboard = []
    for callback in config['callbacks']:
        if(callback['name'] == button):
            reply_text= callback['text']
            if 'buttons' in callback:
                for button in callback['buttons']:
                    keyboard.append([InlineKeyboardButton(button['button'], callback_data=button['callback'])])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    time.sleep(config['typing_timer'])
    update.callback_query.message.reply_text(reply_text, reply_markup=reply_markup)
    logger.info(f"REPLY: {reply_text}")
    
    
    #update.callback_query.message.delete()
    update.callback_query.message.edit_text(update.callback_query.message.text + f"\n\n<b>{user_selected_oprion}</b>", reply_markup=None, parse_mode=ParseMode.HTML)
    
    print(current_chat.state)


def MainLoop():
    """ Checking statuses and timers """
    Timer(config['mainloop_timer'], MainLoop).start()
    
    for tg_chat_id, chat in Chats.items():
        # Processing 'wait' status
        if chat.state["status"] == 'wait':
            delta = datetime.now().timestamp() - chat.state['last_adv']
            if delta >= config['advice_timer']:
                print(tg_chat_id, "set status onemore")
                chat.set_state('status', 'onemore')
        
        if chat.state["status"] == 'new':
            delta = datetime.now().timestamp() - chat.state['last_adv']
            if delta >= config['re_invitation_timer']:
                keyboard = [
                    [InlineKeyboardButton("Начать", callback_data='Q1')],
                    [InlineKeyboardButton("Попозже", callback_data='wait||status:new')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                text = "Понимаем, что возможно вы сейчас заняты другими вопросами. Просто хотим напомнить, что готовы рекомендовать книгу для ребенка. Начнем?"
                updater.bot.send_message(chat.tg_chat_id, text, reply_markup=reply_markup)
                chat.set_state('last_adv', datetime.now().timestamp())
            
        # Processing 'advice' status
        if chat.state["status"] == 'advice':
            chat.set_state('status', 'wait')
            
            # Couting matches
            books = {}
            for book in config['books']:
                if book['id'] in chat.state['books_sent_ids']:
                    continue
                for book_tag in book['tags']:
                    if book_tag in chat.state['tags']:
                        if book['id'] not in books:
                            books[book['id']] = 1
                        else:
                            books[book['id']] += 1
            
            if len(books) > 0:
                books_sorted = sorted(books.items(), key=lambda books: books[1], reverse=True)
                for book in config['books']:
                    if book['id'] == books_sorted[0][0]:
                        chat.add_item('books_sent_ids', book['id'])
                        title = book['name']
                        description = book['description'].replace('\n', '\n\n')    
                        
                        updater.bot.send_chat_action(chat_id=chat.tg_chat_id, action=ChatAction.TYPING)
                        time.sleep(config['typing_timer'])
                        updater.bot.send_message(chat.tg_chat_id, f"<b>{title}</b>\n {description}", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                        if 'file' in book:
                            updater.bot.send_chat_action(chat_id=chat.tg_chat_id, action=ChatAction.TYPING)
                            time.sleep(config['typing_timer'])
                            updater.bot.send_document(chat.tg_chat_id, document=open(book['file'], 'rb'), caption="Файл с карточками")
                        keyboard = [[InlineKeyboardButton("Попробовать", callback_data='Q3')],]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        updater.bot.send_chat_action(chat_id=chat.tg_chat_id, action=ChatAction.TYPING)
                        time.sleep(config['typing_timer'])
                        updater.bot.send_message(chat.tg_chat_id, f"Попробовать еще раз?", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
                        chat.set_state('last_adv', datetime.now().timestamp())
            else:
                updater.bot.send_message(chat.tg_chat_id, "Нет новой рекомендации")
                keyboard = [[InlineKeyboardButton("Попробовать", callback_data='Q3')],]
                reply_markup = InlineKeyboardMarkup(keyboard)
                updater.bot.send_message(chat.tg_chat_id, f"Попробовать еще раз?", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
                pass

        # Processing 'advice' status
        if chat.state["status"] == 'onemore':
            chat.set_state('status', 'wait')
            reply_text = "Выбрать еще"
            keyboard = [
                [InlineKeyboardButton("Выбрать", callback_data='Q3')],
                [InlineKeyboardButton("Отмена", callback_data='nothing')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            time.sleep(config['typing_timer'])
            updater.bot.send_message(chat.tg_chat_id, f"{reply_text}", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
            logger.info(f"REPLY: {reply_text}")
            chat.set_state('last_adv', datetime.now().timestamp())
          

def load_chat(tg_chat_id):
    if tg_chat_id not in Chats:
        print("not in Chats")
        Chats[tg_chat_id] = Chat(tg_chat_id)
    
    return Chats[tg_chat_id]


def main():
    text_handler = MessageHandler(Filters.text, ontext)
    dispatcher.add_handler(text_handler)
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    
    # Load Chats from DB
    cursor = chats_collection.find()
    for chat in cursor:
        Chats[chat['_id']] = Chat(chat['_id'])

    logger.info("Starting mainloop")
    MainLoop()


if __name__ == '__main__':
    Chats = {}
    main()