#!/usr/bin/env python
"""Bot class for botrunner."""
import logging
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode, ChatAction
from lib2to3.pgen2 import token
import sys
import time
from datetime import datetime, timezone

from helpers import send_typing_action
from chat import ChatClass

class BotClass():
    """Class for operate with telegram bots"""
    def __init__(self, bot_name, config, db):
        self.bot_name = bot_name
        self.config = config
        self.config_modified = None
        self.chats = {}
        
        # Set up the logger for bot
        FILE_NAME = None
        if 'logtofile' in config and config['logtofile']:
            FILE_NAME = f"bots/{bot_name}.log"
      
        logging.basicConfig(
            level=10,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=FILE_NAME,
        )
        self.logger = logging.getLogger(__name__)

        # Check bot is not disabled
        if 'disabled' in config and config['disabled']:
            self.logger.debug(f"Bot {bot_name} is disabled")
            return
    
        # Run telegram bot
        try:
            self.updater = Updater(token=self.config['token'], use_context=True)
            self.updater.start_polling()
        except Exception:
            self.logger.error(f"Bot {bot_name} is NOT running")
            return
        else:
            self.logger.info(f"Bot {bot_name} started")
    
        self.text_handler = MessageHandler(Filters.text, self.ontext)
        self.updater.dispatcher.add_handler(self.text_handler)
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.button))
    
        # Select MongoDB
        self.chats_collection = db[bot_name]
        
        print(self.updater.bot.get_me())

        # Set up chats
        # Load Chats from DB
        cursor = self.chats_collection.find()
        for chat in cursor:
            self.chats[chat['_id']] = ChatClass(chat['_id'], self.chats_collection)
    
    def cron_jobs(self):
        """Cron jobs for bot"""
        logging.debug(f"Cron {self.bot_name} jobs started")
        
        """ Checking statuses and timers """
        # TODO: move this to bot scenario config
        for tg_chat_id, chat in self.chats.items():
            # Processing 'wait' status
            if chat.state["status"] == 'wait':
                delta = datetime.now().timestamp() - chat.state['last_adv']
                if delta >= self.config['advice_timer']:
                    print(tg_chat_id, "set status onemore")
                    chat.set_state('status', 'onemore')
            
            if chat.state["status"] == 'new':
                delta = datetime.now().timestamp() - chat.state['last_adv']
                if delta >= self.config['re_invitation_timer']:
                    keyboard = [
                        [InlineKeyboardButton("Начать", callback_data='Q1')],
                        [InlineKeyboardButton("Попозже", callback_data='wait||status:new')],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    text = "Понимаем, что возможно вы сейчас заняты другими вопросами. Просто хотим напомнить, что готовы рекомендовать книгу для ребенка. Начнем?"
                    self.updater.bot.send_message(chat.tg_chat_id, text, reply_markup=reply_markup)
                    chat.set_state('last_adv', datetime.now().timestamp())
                
            # Processing 'advice' status
            if chat.state["status"] == 'advice':
                chat.set_state('status', 'wait')
                
                # Couting matches
                books = {}
                for book in self.config['books']:
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
                    for book in self.config['books']:
                        if book['id'] == books_sorted[0][0]:
                            chat.add_item('books_sent_ids', book['id'])
                            title = book['name']
                            description = book['description'].replace('\n', '\n\n')    
                            
                            self.updater.bot.send_chat_action(chat_id=chat.tg_chat_id, action=ChatAction.TYPING)
                            time.sleep(self.config['typing_timer'])
                            self.updater.bot.send_message(chat.tg_chat_id, f"<b>{title}</b>\n {description}", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                            if 'file' in book:
                                self.updater.bot.send_chat_action(chat_id=chat.tg_chat_id, action=ChatAction.TYPING)
                                time.sleep(self.config['typing_timer'])
                                self.updater.bot.send_document(chat.tg_chat_id, document=open(book['file'], 'rb'), caption="Файл с карточками")
                            keyboard = [[InlineKeyboardButton("Попробовать", callback_data='Q3')],]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            self.updater.bot.send_chat_action(chat_id=chat.tg_chat_id, action=ChatAction.TYPING)
                            time.sleep(self.config['typing_timer'])
                            self.updater.bot.send_message(chat.tg_chat_id, f"Попробовать еще раз?", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
                            chat.set_state('last_adv', datetime.now().timestamp())
                else:
                    self.updater.bot.send_message(chat.tg_chat_id, "Нет новой рекомендации")
                    keyboard = [[InlineKeyboardButton("Попробовать", callback_data='Q3')],]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    self.updater.bot.send_message(chat.tg_chat_id, f"Попробовать еще раз?", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
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
                time.sleep(self.config['typing_timer'])
                self.updater.bot.send_message(chat.tg_chat_id, f"{reply_text}", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
                self.logger.info(f"REPLY: {reply_text}")
                chat.set_state('last_adv', datetime.now().timestamp())   
    
    def load_chat(tg_chat_id):
        '''
        if tg_chat_id not in Chats:
            print("not in Chats")
            Chats[tg_chat_id] = Chat(tg_chat_id)

        return Chats[tg_chat_id]
        '''
    
    def stop(self):
        self.updater.stop()
        self.updater.is_idle = False
        self.logger.info(f"Bot {self.bot_name} stopped")
    
    def event(self, event):
        self.logger.info(event)
    
    @send_typing_action
    def ontext(update, context):
        """ Processing all patterns on text messages """
        '''
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
        '''
        return True
        
    @send_typing_action
    def button(update: Update, context: CallbackContext):
        """Parses the CallbackQuery and updates the message text."""
        '''
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
        '''
