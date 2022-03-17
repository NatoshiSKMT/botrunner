#!/usr/bin/env python
"""This application provides the launch of a telegram bot"""
from lib2to3.pgen2 import token
import sys
import yaml
import os
import logging
import time
from datetime import datetime, timezone
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode, ChatAction
from threading import Timer
from pymongo import MongoClient

from botruner.bot import BotClass

# Set up main logger

FILE_NAME = None # 'botruner.log' - if you want to log to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=FILE_NAME,
    )
logger = logging.getLogger(__name__)

# Connect to MongoDB
try:
    conn = MongoClient()
    logger.info("MongoDB connected!")
    db = conn.database
except:
    logger.error("Could not connect to MongoDB")

def MainLoop():
    """ Checking statuses and timers """
    '''
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
    '''

def load_chat(tg_chat_id):
    '''
    if tg_chat_id not in Chats:
        print("not in Chats")
        Chats[tg_chat_id] = Chat(tg_chat_id)

    return Chats[tg_chat_id]
    '''

def main():
    """Start all configured bots."""
    # load configuation files from each bot subdirectory
    Bots = {}
    for bot_name in os.listdir(os.path.dirname('bots/')):
        # Loading configuration
        try:
            config = yaml.safe_load(open(f"bots/{bot_name}/config.yml", "r", encoding="utf-8"))
        except FileNotFoundError:
            logger.error(f"Fail to open bots/{bot_name}/config.yml")
            continue
        else:
            logger.info(f"Bot {bot_name}: Config loaded")
            Bots[bot_name] = BotClass(bot_name, config, db)

    '''
    logger.info("Starting mainloop")
    MainLoop()
    '''

if __name__ == '__main__':
    Bots = {}
    main()