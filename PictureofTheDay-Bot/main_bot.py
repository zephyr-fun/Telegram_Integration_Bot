# -*- coding: utf-8 -*-
# Python-telegram-bot libraries
import telegram
from telegram import ChatAction, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from functools import wraps

# Logging and requests libraries
import logging
import requests

# Import token from config file
import config

# Import time library
import time
from datetime import timedelta, datetime, date
from pytz import timezone

# Using US/Eastern time
est_timezone = timezone('US/Eastern')

# TinyDB 
from tinydb import TinyDB, Query
main_potd_db = TinyDB('main_potd_db.json')
old_potd_db = TinyDB('old_potd_db.json')
from tinydb.operations import increment

# Datetime Parser
from dateutil.parser import parse

# Date randomizer
from faker import Faker
fake = Faker()

# Import text summarizer function
from text_summarizer_function import summarize_text

# Importing the Updater object with token for updates from Telegram API
# Declaring the Dispatcher object to send information to user
# Creating the bot variable and adding our token
updater = Updater(token = config.token)
dispatcher = updater.dispatcher
bot = telegram.Bot(token = config.token)

# Logging module for debugging
logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level = logging.INFO)

# NASA API
nasa_api_key = config.api_key
nasa_url = f'https://api.nasa.gov/planetary/apod?api_key={nasa_api_key}'

# Reply Keyboard
reply_keyboard = [['/picture 🖼']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard = True)

# DateTime format to use everywhere
fmt = '%Y-%m-%d %H:%M:%S'
date_fmt = '%Y-%m-%d'

def check_api_data_and_send_info(bot, update, user_chat_id, media_type, title, image, explanation, randomize_date, is_old_picture):

    def send_information_to_user(bot, user_chat_id, title, image, explanation):
        bot.send_photo(chat_id = user_chat_id, photo = image)
        bot.send_message(chat_id = user_chat_id, text = f'<b>{title}</b>' + "\n \n" + summarize_text(explanation), parse_mode = 'HTML')

    if 'image' or 'video' in media_type:
        send_information_to_user(bot, user_chat_id, title, image, explanation)

        # Show command banner if the user is new
        if main_potd_db.search((Query()['chat_id'] == user_chat_id) & (Query()['command_banner_shown'] == False)) == []:
            bot.send_message(chat_id = user_chat_id, text = f'<b> NEW! </b> You can now access old pictures of the day! Type for example: <code> /old_picture {randomize_date} </code>', parse_mode = 'HTML')

        print(f"User {user_chat_id} and ID {str(update.message.from_user.username)} called the /picture command!")

    else:
        bot.send_message(chat_id = user_chat_id, text = "Sorry, I couldn't deliver the image / video! An error occured!")
        print(f"User {user_chat_id} and ID {str(update.message.from_user.username)} called the /picture command and an error occured!")


# Typing animation to show to user to imitate human interaction
def send_action(action):
    def decorator(func):
        @wraps(func)
        def command_func(*args, **kwargs):
            bot, update = args
            bot.send_chat_action(chat_id = update.effective_message.chat_id, action = action)
            return func(bot, update, **kwargs)
        return command_func
    return decorator

send_typing_action = send_action(ChatAction.TYPING)

# '/start' command
@send_typing_action
def start(bot, update):
    bot.send_message(chat_id = update.message.chat_id, text = "Hello! Thank you for starting me! Use the /picture command to see today's NASA Image of the Day!")

    print(datetime.now(est_timezone).strftime(fmt))
    print(f"User {update.message.chat_id} and ID {str(update.message.from_user.username)} started the bot!")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# '/picture' command
@send_typing_action
def pictureoftheday_message(bot, update):
    
    start_time = time.time()

    start_date = date(1995, 6, 16)
    end = (datetime.now(est_timezone) - timedelta(1)).strftime(date_fmt)
    end_date = date(int(end[0:4]), int(end[5:7]), int(end[8:10]))

    randomize_date = fake.date_between(start_date = start_date, end_date = end_date).strftime('%d %B %Y')

    nasa_data = requests.get(nasa_url).json()

    '''
    If user doesn't exist, go to the else loop and populate data into db

    If user_id EXISTs in the db, check the time and extract minute difference
    '''
    if main_potd_db.contains(Query()['chat_id'] == update.message.chat_id):

        user = Query()
        result = main_potd_db.search((user.chat_id == update.message.chat_id) & (user.time != str(0)))
        time_getter = [x['time'] for x in result]
        print(time_getter[0])

        old_time = datetime.strptime(str(time_getter[0]), fmt)
        current_time = datetime.strptime(str(datetime.now(est_timezone).strftime(fmt)), fmt)

        # Calculate how much time has passed since we served the image
        minutes_diff = (current_time - old_time).total_seconds() / 60.0
            
        # If more than 10 minutes have passed, they can reuse the command
        if int(minutes_diff) >= 0:
            main_potd_db.upsert({'time': str(datetime.now(est_timezone).strftime(fmt)), 'username': str(update.message.from_user.username), 'command_banner_shown': False}, Query()['chat_id'] == update.message.chat_id)
            main_potd_db.update(increment('count'), Query()['chat_id'] == update.message.chat_id)

            check_api_data_and_send_info(bot, update, update.message.chat_id, nasa_data['media_type'], nasa_data['title'], nasa_data['url'], nasa_data['explanation'], randomize_date = randomize_date, is_old_picture = False)
        
        else:
            bot.send_message(chat_id = update.message.chat_id, text = f"You're doing that too much. Please try again in {10 - int(minutes_diff)} minute(s)!")
            print(f"User {update.message.chat_id} and ID {str(update.message.from_user.username)} spammed the /picture command and hit a cooldown!")

    # A new user has invoked the picture command since the chat_id cannot be found in database
    else:
        main_potd_db.insert({'chat_id': update.message.chat_id, 'time': str(datetime.now(est_timezone).strftime(fmt)), 'username': update.message.from_user.username, 'count': 1, 'command_banner_shown': True})

        check_api_data_and_send_info(bot, update, update.message.chat_id, nasa_data['media_type'], nasa_data['title'], nasa_data['url'], nasa_data['explanation'], randomize_date = randomize_date, is_old_picture = False)

    print(f"{time.time() - start_time} seconds")
    
pictureoftheday_message_handler = CommandHandler('picture', pictureoftheday_message)
dispatcher.add_handler(pictureoftheday_message_handler)

@send_typing_action
def old_picture(bot, update, args):
    if args:
        user_input = "-".join(args)
        parsed_user_input = parse(user_input)
        user_input_string = str(parsed_user_input) 

        year = user_input_string[0:4]
        month = user_input_string[5:7]
        day = user_input_string[8:10]

        start_date = date(1995, 6, 16)

        entered_date = date(int(year), int(month), int(day))

        end = (datetime.now(est_timezone) - timedelta(1)).strftime(date_fmt)
        end_date = date(int(end[0:4]), int(end[5:7]), int(end[8:10]))

        old_pictures_url = f'https://api.nasa.gov/planetary/apod?api_key={config.api_key}&date={year}-{month}-{day}'
        old_picture_data = requests.get(old_pictures_url).json()

        if start_date <= entered_date <= end_date:

            if old_potd_db.contains(Query()['chat_id'] == update.message.chat_id):

                old_picture_user = Query()
                result = old_potd_db.search((old_picture_user.chat_id == update.message.chat_id) & (old_picture_user.time != str(0)))
                time_getter = [sub['time'] for sub in result]
                print(time_getter[0])

                old_time = datetime.strptime(str(time_getter[0]), fmt)
                current_time = datetime.strptime(str(datetime.now(est_timezone).strftime(fmt)), fmt)

                # Calculate how much time has passed since we served the image
                minutes_diff = (current_time - old_time).total_seconds() / 60.0

                if int(minutes_diff) >= 0:
                    old_potd_db.upsert({'time': str(datetime.now(est_timezone).strftime(fmt)), 'username': str(update.message.from_user.username)}, Query()['chat_id'] == update.message.chat_id)
                    old_potd_db.update(increment('count'), Query()['chat_id'] == update.message.chat_id)

                    check_api_data_and_send_info(bot, update, update.message.chat_id, old_picture_data['media_type'], old_picture_data['title'], old_picture_data['url'], old_picture_data['explanation'], randomize_date = 100, is_old_picture = True)

                else:
                    bot.send_message(chat_id = update.message.chat_id, text = f"You're doing that too much. Please try again in {2 - int(minutes_diff)} minute(s)!")
                    print(f"User {update.message.chat_id} and ID {str(update.message.from_user.username)} spammed the /old_picture command and hit a cooldown!")

            else:
                old_potd_db.insert({'chat_id': update.message.chat_id, 'time': str(datetime.now(est_timezone).strftime(fmt)), 'username': update.message.from_user.username, 'count': 1})

                check_api_data_and_send_info(bot, update, update.message.chat_id, old_picture_data['media_type'], old_picture_data['title'], old_picture_data['url'], old_picture_data['explanation'], randomize_date = 100, is_old_picture = True)
            
        else:
            bot.send_message(chat_id = update.message.chat_id, text = f"Only dates between 16 June 1995 and {(datetime.now(est_timezone) - timedelta(1)).strftime('%d %B %Y')} are supported. Please try again!")
    else:
        start_date = date(1995, 6, 16)
        end = (datetime.now(est_timezone) - timedelta(1)).strftime(date_fmt)
        end_date = date(int(end[0:4]), int(end[5:7]), int(end[8:10]))
        randomize_date = fake.date_between(start_date = start_date, end_date = end_date).strftime('%d %B %Y')
        
        bot.send_message(chat_id = update.message.chat_id, text = f"Please enter a date after the command! For example: <code>/old_picture {randomize_date} </code>", parse_mode = 'HTML')

old_picture_handler = CommandHandler('old_picture', old_picture, pass_args = True)
dispatcher.add_handler(old_picture_handler)

# Unknown command for error handling
@send_typing_action
def unknown(bot, update):
    bot.send_message(chat_id = update.message.chat_id, text = "Sorry, I didn't understand that command! Please type /picture! or /old_picture")

    print(datetime.now(est_timezone))
    print(f"User {update.message.chat_id} and ID {str(update.message.from_user.username)} called an unknown command!")

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

# Module to start getting data
print("Bot started!")
updater.start_polling()
updater.idle()