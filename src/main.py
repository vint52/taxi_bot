import asyncio
from datetime import datetime

from taxi import Taxi
import os
import redis
import time
import pytz

import json
import logging

from aiogram import Bot, Dispatcher, executor, types

UPDATE_PERIOD = int(os.getenv('TXI_UPDATE_PERIOD', '25'))
API_TOKEN = os.getenv('TG_TOKEN')
logging.basicConfig(level=logging.INFO, filename=os.getenv('TG_LOG'))
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
ADMIN_USER_ID = os.getenv('TG_ADMIN_ID')

r = redis.StrictRedis(host=os.getenv('RDS_HOST'), password=os.getenv('RDS_PASSWORD'), charset="utf-8",
                      decode_responses=True,
                      port=6379,
                      db=0)


def make_message():
    balance = r.get('balance')
    trips = r.zrange('trips', -3, -1)
    str_trips = ''
    for str_trip in trips:
        trip = json.loads(str_trip)
        str_trips = '-------\nВремя: {0}\nПассажир: {1} ({2})\nОт: {3}\nДо: {4}\nРасстояние: {5}\nОжидание: {6}\n' \
                    'Стоимость: {7} р.\n'.format(
            datetime.fromtimestamp(int(trip['time'])).strftime('%d.%m.%Y %H:%M'),
            trip['name'], trip['phone'], trip['from'], trip['to'],
            trip['distance'], trip['waiting'], trip['price']) + str_trips

    return "Баланс: {0}р.\n\nПрошлые поездки:\n{1}".format(balance, str_trips)


def is_admin(user_id):
    return int(user_id) == int(ADMIN_USER_ID)


def get_keyboard(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Проверить баланс"]

    if is_admin(user_id):
        buttons = ["Логи", "Пользователи", "Проверить баланс"]

    keyboard.add(*buttons)
    return keyboard


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    logging.info('START! - {0} ({1})'.format(message.from_user.username, message.from_user.id))
    r.sadd('users', message.from_user['id'])
    keyboard = get_keyboard(message.from_user.id)
    await message.answer("Добро пожаловать в бот для отслеживания поездок", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Логи")
async def show_logs(message: types.Message):
    logging.info('Show logs {0} ({1})'.format(message.from_user.username, message.from_user.id))
    keyboard = get_keyboard(message.from_user.id)
    if os.getenv('TG_LOG', '') != '':
        f = open(os.getenv('TG_LOG'), "r")
        logs = ''.join(f.readlines()[-20:])
        f.close()
        await message.answer(logs, reply_markup=keyboard)
    else:
        await message.answer("Логи отключены", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Пользователи")
async def show_users(message: types.Message):
    logging.info('Show users {0} ({1})'.format(message.from_user.username, message.from_user.id))
    keyboard = get_keyboard(message.from_user.id)

    users = r.smembers('users')
    if users is not None:
        usr_msg = ''
        for usr in users:
            usr_msg = usr_msg + '\n' + usr

        await message.answer(usr_msg, reply_markup=keyboard)
        return
    await message.answer("Нет пользователей", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Проверить баланс")
async def show_balance(message: types.Message):
    r.sadd('users', message.from_user['id'])
    logging.info('Проверить баланс - {0} ({1})'.format(message.from_user.username, message.from_user.id))
    keyboard = get_keyboard(message.from_user.id)
    msg = make_message()

    if is_admin(message.from_user.id):
        ts = int(r.get('timestamp'))
        last_time = datetime.fromtimestamp(ts, pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y %H:%M')
        msg = msg + '\nLast update: {0}'.format(last_time)

    await message.answer(msg, reply_markup=keyboard)


@dp.message_handler()
async def unknown_command(message: types.Message):
    logging.info(
        'Unknown command "{0}" {1}({2})'.format(message.text, message.from_user.username, message.from_user.id))
    keyboard = get_keyboard(message.from_user.id)
    await message.reply("Команда не найдена", reply_markup=keyboard)


async def send_all():
    msg = make_message()
    users = r.smembers('users')
    for usr in users:
        logging.info('send to user {0}'.format(usr))
        await dp.bot.send_message(usr, msg)


async def update_data():
    taxi = Taxi(os.getenv('TXI_USERNAME'), os.getenv('TXI_PASSWORD'))
    result = taxi.get_profile_info()
    old_balance = r.get('balance')
    send_flag = False
    if old_balance is None or int(old_balance) != int(result['balance']):
        logging.info('update balance {0}'.format(result['balance']))
        r.set('balance', result['balance'])
        send_flag = True

    trips = r.zrange('trips', -1, -1)
    if len(result['trips']) > 0 and (
            trips is None or len(trips) == 0 or json.loads(trips[0])['time'] != result['trips'][-1]['time']):
        logging.info('update trips')
        for item in result['trips']:
            r.zadd('trips', {json.dumps(item, ensure_ascii=False): item['time']})
        send_flag = True

    r.set('timestamp', int(time.time()))
    if send_flag:
        await send_all()


async def scheduler():
    while True:
        await update_data()
        await asyncio.sleep(UPDATE_PERIOD)


async def on_startup(_):
    asyncio.create_task(scheduler())


def main():
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


if __name__ == '__main__':
    main()
