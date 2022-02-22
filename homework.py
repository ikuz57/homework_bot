from dotenv import load_dotenv
from sys import stdout
import time
import telegram.ext
import requests
import logging
import os

from exceptions import ApiError, NotListError, StatusKeyError, TokenError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
# Настроили общий логгер
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Настроили локальный логер на вывод в stdout
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')
handler = logging.StreamHandler(stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение."""
    # тут сделал обработку ошибок, т.к. в main у меня в
    # блоке обработки ошибок вызывается эта функция и тут
    # проще все это сделать.
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        message = f'Бот не смог отправить сообщение: {error}'
        logger.error(message)
    else:
        logger.info(f'Бот отправил сообщение: {message}.')


def get_api_answer(current_timestamp):
    """.
    Получает ответ api, если сервер недоступен,
    то выводится ошибка с кодом ответа сервера.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    # Так у нас же get_api_answer() из мейн вызывается, там и будет
    # вызвано исключение, отправлено сообщение в телеграмм и
    # сделана запись в логи
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    # а вот и то что вызовет исключение если сервер вышлет что то
    # отличное от 200го ответа
    if response.status_code != 200:
        raise ApiError(
            f'Эндпоинт {ENDPOINT} '
            f'недоступен. Код ответа API: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """.
    Проверка ответа api на корректность,
    ожидаем список.
    """
    # Через get не хочет, все тесты перестают работать)
    if type(response['homeworks']) is not list:
        raise NotListError(
            'некорректный ответ API. "Homeworks" должен быть списком'
        )
    return response['homeworks']


def parse_status(homework):
    """Вытаскиваем из ответа api нужную нам информацию."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise StatusKeyError(
            'недокументированный статус домашней работы, '
            'обнаруженный в ответе API'
        )
    else:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """.
    Проверяет доступность переменных окружения,
    которые необходимы для работы программы.
    """
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logger.info('Проверка токенов. Успех!')
    else:
        logger.critical(
            'Проверка токенов. '
            'Ошибка: отсутствие обязательных переменных '
            'окружения во время запуска бота!'
        )
        raise TokenError

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status_cache = ''
    error_cache = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            logger.info('Получение ответа от сервера. Успех!')
            homeworks = check_response(response)

            if len(homeworks) == 0:
                status = 'Нет работ на проверке.'
            else:
                homework = homeworks[0]
                status = parse_status(homework)

            if status != status_cache:
                send_message(bot, status)
                status_cache = status
            else:
                logger.debug('В ответе отсутствуют новые статусы.')
            # Обновили timestamp перед слипом
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            # что бы не слать одни и те же оишбки в телеграмм
            # мы запомним последнюю и если будет новая ошибка,
            # то только тогда отправим сообщение
            if error_cache != message:
                send_message(bot, message)
                error_cache = message
            logger.error(message)
        time.sleep(RETRY_TIME)
        logger.info('Повторная проверка.')


if __name__ == '__main__':
    main()
