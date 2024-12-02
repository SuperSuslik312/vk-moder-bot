import vk_api
import time
import logging
from vk_api.longpoll import VkLongPoll, VkEventType
from urllib.parse import urlparse
from logging.handlers import RotatingFileHandler

TOKEN = "token"
TIME = 3600  # 3600 секунд = 1 час

# Логи
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler(
    filename='bot.log', mode='a', maxBytes=5*1024*1024, backupCount=1, encoding=None, delay=False
)
log_handler.setFormatter(formatter)
log_handler.setLevel(logging.DEBUG)
log = logging.getLogger('root')
log.setLevel(logging.DEBUG)
log.addHandler(log_handler)

# Авторизация бота
vk_session = vk_api.VkApi(
    api_version='5.131',
    token=TOKEN
)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# Проверка времени нахождения пользователя в беседе
def is_new_user(chat_id, user_id):
    try:
        response = vk.messages.getConversationMembers(peer_id=int(2E9) + chat_id)
        for member in response['items']:
            if member['member_id'] == user_id:
                join_date = member.get('join_date')
                if join_date:
                    current_time = int(time.time())
                    return current_time - join_date < TIME  # True, если меньше часа
        log.warning(f"Пользователь {user_id} не найден в списке участников.")
    except Exception as e:
        log.error(f"Ошибка при проверке времени нахождения в беседе: {e}")
    return False

# Проверка админских прав
def is_admin(chat_id, user_id):
    try:
        response = vk.messages.getConversationMembers(peer_id=int(2E9) + chat_id)
        for member in response['items']:
            if member['member_id'] == user_id and 'is_admin' in member and member['is_admin']:
                return True
    except Exception as e:
        log.error(f"Ошибка при проверке админских прав: {e}")
    return False

# Проверка текста на ссылку
def process_link(text, chat_id, user_id, message_id):
    try:
        parsed = urlparse(text)
        # Проверяем, что текст выглядит как ссылка
        if parsed.netloc or ('.' in text and len(text.split('.')[-1]) >= 2):
            vk.account.setOnline()
            # Удаляем сообщение и кикаем пользователя
            vk.messages.delete(
                delete_for_all=1,
                message_ids=message_id
            )
            vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )
            log.info(f"Пользователь {user_id} удалён за отправку ссылки: {text}")
    except Exception as e:
        log.error(f"Ошибка при обработке ссылки: {e}")

# Основной цикл обработки событий
def main():
    try:
        for event in longpoll.listen():
            # Обрабатываем только новые и отредактированные сообщения в беседах
            if (event.type == VkEventType.MESSAGE_NEW or event.type == VkEventType.MESSAGE_EDIT) and event.from_chat:
                chat_id = event.chat_id
                user_id = event.user_id
                message_id = event.message_id
                message = event.message

                # Проверяем, новый ли пользователь
                if is_new_user(chat_id, user_id):
                    # Проверяем текст сообщения
                    words = message.split()
                    for word in words:
                        process_link(word, chat_id, user_id, message_id)

                    # Проверяем вложения
                    if event.attachments.get('attach1_type'):
                        attachment_type = event.attachments['attach1_type']
                        if attachment_type == 'link':
                            link = event.attachments['attach1_url']
                            log.info(f"Обнаружена ссылка во вложении: {link}")
                            vk.account.setOnline()
                            vk.messages.delete(
                                delete_for_all=1,
                                message_ids=message_id
                            )
                            vk.messages.removeChatUser(
                                chat_id=chat_id,
                                user_id=user_id
                            )
                            log.info(f"Пользователь {user_id} удалён за ссылку во вложении.")

                # Обработка команды !расстрел
                if message.startswith('!расстрел'):
                    if is_admin(chat_id, user_id):
                        vk.account.setOnline()
                        mentioned_user_id = event.extra_values.get('mentions', [])[0] if event.extra_values.get('mentions') else None
                        if mentioned_user_id:
                            gif_id = "doc674276092_678385113"
                            vk.messages.send(
                                chat_id=chat_id,
                                message=f"@id{mentioned_user_id}\nЗа неповиновение представителю власти вы приговариваетесь к высшей мере наказания — расстрелу!",
                                attachment=gif_id,
                                random_id=0
                            )
                            vk.messages.removeChatUser(
                                chat_id=chat_id,
                                user_id=mentioned_user_id
                            )
                        else:
                            vk.messages.send(
                                chat_id=chat_id,
                                message="Команда должна быть ответом на сообщение пользователя, которого нужно расстрелять.",
                                random_id=0
                            )
    except Exception as e:
        log.error(f"Ошибка в главном цикле: {e}")

if __name__ == "__main__":
    main()
