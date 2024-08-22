import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
import uuid
import django
from chat.models import User, ActiveChat
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anonymbot.settings')
django.setup()

API_TOKEN = 'YOUR_TOKEN'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# In-memory storage for message tracking
message_to_user = {}


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
        try:
            referrer = User.objects.get(referral_link=referral_code)
        except User.DoesNotExist:
            await message.reply("Invalid referral link.")
            return

        user, created = User.objects.get_or_create(telegram_id=user_id)

        # End existing chat sessions for both users
        ActiveChat.objects.filter(user=user).delete()
        ActiveChat.objects.filter(referrer=user).delete()

        # Create new active chat session
        ActiveChat.objects.create(referrer=referrer, user=user)
        await message.reply("You can now chat with the holder of this referral.")
        await bot.send_message(referrer.telegram_id, "Someone has started chatting with you anonymously.")
        return

    await message.reply("Welcome! Use /get_link to get your referral link.")


@dp.message_handler(commands=['get_link'])
async def get_link(message: types.Message):
    user_id = message.from_user.id
    user, created = User.objects.get_or_create(telegram_id=user_id)

    if created or not user.referral_link:
        user.referral_link = str(uuid.uuid4())
        user.save()

    referral_link = f"https://t.me/newanonymmmbot?start={user.referral_link}"
    await message.reply(f"Here is your referral link: {referral_link}")


@dp.message_handler(lambda message: message.from_user.id in [ac.user.telegram_id for ac in ActiveChat.objects.all()])
async def handle_anonymous_message(message: types.Message):
    user_id = message.from_user.id
    try:
        user = User.objects.get(telegram_id=user_id)
        active_chat = ActiveChat.objects.get(user=user)
        referrer = active_chat.referrer
        msg = await bot.send_message(referrer.telegram_id, f"Anonymous message: {message.text}")
        # Map the message_id to the user_id for tracking replies
        message_to_user[msg.message_id] = user_id
        await message.reply("Your anonymous message has been sent.")
    except (User.DoesNotExist, ActiveChat.DoesNotExist):
        await message.reply("You are not in an active chat.")


@dp.message_handler(lambda message: message.reply_to_message)
async def handle_reply(message: types.Message):
    reply_to_message_id = message.reply_to_message.message_id
    if reply_to_message_id in message_to_user:
        recipient_id = message_to_user[reply_to_message_id]
        await bot.send_message(recipient_id, f"Reply: {message.text}")
    else:
        await message.reply("You cannot reply to this message.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
