import asyncio
from datetime import datetime
from typing import Union

import aioschedule as aioschedule
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from holidays_ru import check_holiday

from src import database, logger

with open("token.txt", "r", encoding="utf-8") as f:
    token = f.read()

bot = Bot(token=token)
dp = Dispatcher()


def get_setting(name: str) -> Union[str, bool, int]:
    return database.settings.find_one({"name": name})["value"]


async def send_error(message: types.Message, text: str, delete_message: bool = True, **kwargs: dict) -> None:
    error = await message.answer(text, reply_to_message_id=message.message_id, **kwargs)
    await asyncio.sleep(5)

    if delete_message:
        await message.delete()

    await error.delete()


@dp.message(Command("id"))
async def get_id(message: types.Message) -> None:
    logger.info(f"Chat id: {message.chat.id}")
    logger.info(f"Chat title: {message.chat.title}")
    logger.info(f"Chat type: {message.chat.type}")
    await message.delete()


@dp.message(Command("start"))
async def start(message: types.Message) -> None:
    logger.info(f"Command {message.text} from user {message.from_user.username} ({message.from_user.id}) in chat {message.chat.title} ({message.chat.id})")

    try:
        if get_setting("group_id") != message.chat.id:
            return await send_error(message, text=f"Команда {message.text} недоступна для этого чата")

        if get_setting("is_running"):
            return await send_error(message, text="Бот уже запущен")

        database.settings.update_one({"name": "is_running"}, {"$set": {"value": True}})
        return await send_error(message, text="Бот успешно запущен")
    except Exception as error:
        logger.info(f"Raised exception {error} during handle {message.text} command")


@dp.message(Command("stop"))
async def stop(message: types.Message) -> None:
    logger.info(f"Command {message.text} from user {message.from_user.username} ({message.from_user.id}) in chat {message.chat.title} ({message.chat.id})")

    try:
        if get_setting("group_id") != message.chat.id:
            return await send_error(message, text=f"Команда {message.text} недоступна для этого чата")

        if not get_setting("is_running"):
            return await send_error(message, text="Бот уже приостановлен")

        database.settings.update_one({"name": "is_running"}, {"$set": {"value": False}})
        return await send_error(message, text="Бот успешно приостановлен")
    except Exception as error:
        logger.info(f"Raised exception {error} during handle {message.text} command")


@dp.message(Command("add"))
async def add_user(message: types.Message) -> None:
    logger.info(f"Command {message.text} from user {message.from_user.username} ({message.from_user.id}) in chat {message.chat.title} ({message.chat.id})")

    try:
        if get_setting("group_id") != message.chat.id:
            return await send_error(message, text=f"Команда {message.text} недоступна для этого чата")

        username = message.from_user.username
        if database.users.find_one({"username": username}) is not None:
            return await send_error(message, text=f"Пользователь @{username} уже добавлен в список")

        database.users.insert_one({"username": username})
        await send_error(message, f"Пользователь @{username} успешно добавлен в список")
    except Exception as error:
        logger.info(f"Raised exception {error} during handle {message.text} command")


@dp.message(Command("remove"))
async def remove_user(message: types.Message) -> None:
    logger.info(f"Command {message.text} from user {message.from_user.username} ({message.from_user.id}) in chat {message.chat.title} ({message.chat.id})")

    try:
        if get_setting("group_id") != message.chat.id:
            return await send_error(message, text=f"Команда {message.text} недоступна для этого чата")

        username = message.from_user.username
        if database.users.find_one({"username": username}) is None:
            return await send_error(message, text=f"Пользователь @{username} уже отсутствует в списке")

        database.users.delete_one({"username": username})
        await send_error(message, f"Пользователь @{username} успешно удалён из списка")
    except Exception as error:
        logger.info(f"Raised exception {error} during handle {message.text} command")


@dp.message(Command("info"))
async def info(message: types.Message) -> None:
    logger.info(f"Command {message.text} from user {message.from_user.username} ({message.from_user.id}) in chat {message.chat.title} ({message.chat.id})")

    try:
        if get_setting("group_id") != message.chat.id:
            return await send_error(message, text=f"Команда {message.text} недоступна для этого чата")

        is_running = get_setting("is_running")
        standup_time = get_setting("standup_time")
        users_count = database.users.count_documents({})

        lines = [
            f'<b>Статус</b>: {"бот запущен" if is_running else "бот приостановлен"}',
            f"<b>Время стендапа</b>: {standup_time}",
            f"<b>Количество вызываемых участников</b>: {users_count}"
        ]

        await send_error(message, text="\n".join(lines), parse_mode="HTML")
    except Exception as error:
        logger.info(f"Raised exception {error} during handle {message.text} command")


async def scheduled_send_standup() -> None:
    if not get_setting("is_running"):
        logger.info("Standup bot is not running")
        return

    if check_holiday(datetime.now().date()):
        logger.info("Today is holiday")
        return

    group_id = get_setting("group_id")
    usernames = [f'@{user["username"]}' for user in database.users.find({})]

    if not usernames:
        logger.info("There are no users for send standup")
        return

    text = f'#стендап\n{" ".join(usernames)}'
    await bot.send_message(chat_id=group_id, text=text, parse_mode="HTML")


async def scheduler() -> None:
    standup_time = get_setting("standup_time")
    logger.info(f"Schedule standup for {standup_time}")

    aioschedule.every().day.at(standup_time).do(scheduled_send_standup)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def run_scheduler() -> None:
    asyncio.create_task(scheduler())


async def main() -> None:
    database.connect()

    loop = asyncio.get_event_loop()
    loop.create_task(run_scheduler())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
