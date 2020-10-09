from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters
from telegram import ChatAction, ReplyKeyboardMarkup
from functools import wraps
import logging
import urllib.request
import gzip
import json
import feedparser, html2text, json, datetime
from loguru import logger

mark_up = ReplyKeyboardMarkup(keyboard=[['/help'],['/weather'],['/picture'],['/hi']], one_time_keyboard=False)

def get_weather_data(city_name):
    url_byCityName = 'http://wthrcdn.etouch.cn/weather_mini?city='+urllib.parse.quote(city_name)
    weather_data = urllib.request.urlopen(url_byCityName).read()
    #读取网页数据
    weather_data = gzip.decompress(weather_data).decode('utf-8')
    #解压网页数据
    weather_dict = json.loads(weather_data)
    #将json数据转换为dict数据
    return weather_dict

def show_weather(weather_data):
    weather_dict = weather_data
    #将json数据转换为dict数据
    if weather_dict.get('desc') == 'invilad-citykey':
        weather_text = '啊真的有这个城市吗？\n官方说法：天气中心未收录你所在城市'
    elif weather_dict.get('desc') =='OK':
        forecast = weather_dict.get('data').get('forecast')
        weather_text = '城市：' + weather_dict.get('data').get('city') + '\n' + '温度：' + weather_dict.get('data').get('wendu') + '℃ ' + '\n' + '感冒：' + weather_dict.get('data').get('ganmao') + '\n' + '风向：' + forecast[0].get('fengxiang') + '\n' + '高温：' + forecast[0].get('high') + '\n' + '低温：' + forecast[0].get('low') + '\n' + '天气：' + forecast[0].get('type') + '\n' + '日期：' + forecast[0].get('date')
    return weather_text    
       
    #     print('*******************************')
    #     four_day_forecast =input('是否要显示未来四天天气，是/否：')
    #     if four_day_forecast == '是' or 'Y' or 'y':
    #         for i in range(1,5):
    #             print('日期：',forecast[i].get('date'))
    #             print('风向：',forecast[i].get('fengxiang'))
    #             print('风级：',forecast[i].get('fengli'))
    #             print('高温：',forecast[i].get('high'))
    #             print('低温：',forecast[i].get('low'))
    #             print('天气：',forecast[i].get('type'))
    #             print('--------------------------')
    # print('***********************************')

def start(update,context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="好久不见。")
start_handler = CommandHandler('start',start)


def help(update,context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="你猜怎么用？", reply_markup=mark_up)
help_handler = CommandHandler('help',help)


def weather(update,context):
    weather_data = show_weather(get_weather_data(context.args[0]))
    logging.info(type(context.args))
    logging.info(context.args[0])
    context.bot.send_message(chat_id=update.effective_chat.id, text=weather_data)
weather_handler = CommandHandler('weather',weather)





def date_title(file_name: str, object_name: str, date_title: str):
    """
    Set the date/title of latest post from a source.
    :param file_name: The name of the file to open.
    :param object_name: The name of the object to replace.
    :param date_title: The date/title to replace the existing object with.
    """
    try:
        with open(file_name, "r+") as data_file:
            # Load json structure into memory.
            feeds = json.load(data_file)
            for name, data in feeds.items():
                if (name) == (object_name):
                    # Replace value of date/title with date_title
                    data["date_title"] = date_title
                    # Go to the top of feeds.json file.
                    data_file.seek(0)
                    # Dump the new json structure to the file.
                    json.dump(feeds, data_file, indent=2)
                    data_file.truncate()
    except IOError:
        logger.debug("date_title: Failed to open requested file.")


def feed_to_md(name: str, feed_data: dict):
    """
    Converts an RSS feed into markdown text.
    :param name: The name of the RSS feed. eg: hacker_news.
    :param feed_data: The data of the feed. eg: url and post_date from feeds.json.
    :rtype: A dict object containing data about the top feed item.
    """
    # Parse RSS feed.
    d = feedparser.parse(feed_data["url"])
    # Target the first post.
    # 改写一下判断，订阅不成功
    first_post = d["entries"][0]
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.ignore_links = True
    summary = first_post["summary"]
    summary = h.handle(summary)
    result = {
        "title": first_post["title"],
        "summary": summary,
        "url": first_post["link"],
        # "post_date": first_post["published"],
    }
    return result


def file_reader(path: str, mode: str):
    """
    Loads JSON data from the file path specified.
    :param path: The path to the target file to open.
    :param mode: The mode to open the target file in.
    :rtype: JSON data from the specified file.
    """
    try:
        with open(path, mode) as target_file:
            data = json.load(target_file)
            return data
    except IOError:
        logger.debug(f"Failed to open the file: {path}")


def check_feeds(context):
    """
    Checks RSS feeds from feeds.json for a new post.
    :param context: The telegram CallbackContext class object.
    """
    logger.debug("Checking if feeds have updated...")
    feeds = file_reader("feeds.json", "r")
    for name, feed_data in feeds.items():
        logger.debug(f"Checking if feed: {name} requires updating...")
        result = feed_to_md(name, feed_data)
        # Checking if title is the same as title in feeds.json file.
        # If the same; do nothing.
        if (feed_data["date_title"]) == (result["title"]):
            logger.debug(f"Feed: {name} does not require any updates.")
            continue
        elif (feed_data["date_title"]) != (result["title"]):
            logger.debug(
                f"Feed: {name} requires updating! Running date_title for feeds.json."
            )
            date_title("feeds.json", name, result["title"])
            # Set RSS message.
            rss_msg = f"[{result['title']}]({result['url']})"
            context.bot.send_message(chat_id="710577478", text=rss_msg, parse_mode="Markdown")
    logger.debug("Sleeping for 12 hours...")


def error(update, context):
    """
    Log errors which occur.
    :param update: The telegram Update class object which caused the error.
    :param context: The telegram CallbackContext class object.
    """
    logger.debug(f"Update: {update} caused the error: {context.error}")


if __name__ == "__main__":
    __version__ = "20.09.19"
    __name__ = "telegram_assistant"
    
    # Init logging.
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
    logger.add(
        "bot_{time}.log",
        format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        rotation="300 MB",
    )
    # Setup Updater for bot.
    updater = Updater(token = '1287844941:AAGEqYC6ahcMfv_z2r6n4tAQsg0i3drM5VE',use_context = True)
    # Get the dispatcher to register handlers.
    dispatcher = updater.dispatcher
    # log all errors.
    dispatcher.add_error_handler(error)
    # handler for /start command
    dispatcher.add_handler(start_handler)
    # handler for /help command
    dispatcher.add_handler(help_handler)
    # handler for /weather command
    dispatcher.add_handler(weather_handler)
    # Run Job every 30 mins.
    job_queues = updater.job_queue
    job_thirty_min = job_queues.run_repeating(check_feeds, interval=43200, first=0)
    # Begin running the bot.
    updater.start_polling()