import vk_api
import time
import logging
from vk_api.longpoll import VkLongPoll, VkEventType
from urllib.parse import urlparse

TOKEN = "token"

logging.basicConfig(level=logging.DEBUG, filename="bot.log")

# Авторизация бота
vk_session = vk_api.VkApi(
    api_version='5.131',
    token=TOKEN
)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)


# Функция для обработки ссылок
def process_link(link, chat_id, user_id, message_id):
    parsed = urlparse(link)
    # Проверяем, что ссылка валидна
    if parsed.netloc or ('.' in link and len(link.split('.')[-1]) >= 2):
        # Получаем время вступления пользователя в беседу
        response = vk.messages.getConversationMembers(peer_id=int(2E9) + chat_id)
        join_date = None
        for member in response['items']:
            if member['member_id'] == user_id:
                join_date = member['join_date']
                break
        if join_date is None:
            return  # Пользователь не найден в беседе
        # Сравниваем время вступления с текущим временем
        current_time = int(time.time())
        if current_time - join_date < 3600:  # 3600 секунд в одном часе
            vk.messages.delete(
                delete_for_all=1,
                message_ids=message_id
            )
            vk.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )


def main():
    for event in longpoll.listen():
        # Обрабатываем только события новых и отредактированных сообщений в беседах
        if (event.type == VkEventType.MESSAGE_NEW or event.type == VkEventType.MESSAGE_EDIT) and event.from_chat:
            # Получаем текст сообщения, идентификатор беседы, пользователя и сообщения
            message = event.message
            chat_id = event.chat_id
            user_id = event.user_id
            message_id = event.message_id
            # Разбиваем сообщение на слова
            words = message.split()
            # Перебираем слова в сообщении
            for word in words:
                process_link(word, chat_id, user_id, message_id)


if __name__ == "__main__":
    main()
