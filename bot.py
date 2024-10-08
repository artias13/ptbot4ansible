from typing import List, Union
import logging
import subprocess
import paramiko
import psycopg2
from psycopg2 import Error, connect
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import os
import re
from dotenv import load_dotenv

RM_HOST = os.getenv('RM_HOST')
RM_PORT = os.getenv('RM_PORT')
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')
TOKEN = os.getenv('TOKEN')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')

GET_APT_LIST_STATE = 0
SAVE_PHONE_NUMBER_STATE = 1
SAVE_EMAIL_ADDRESS_STATE = 2
LOG_FILE_PATH = "/var/log/postgresql/postgresql.log"

# Подключаем логирование
logging.basicConfig(filename='bot.log', level=logging.INFO, format=' %(asctime)s - %(levelname)s - %(message)s', encoding="utf-8")
logging.info('Бот запущен')

logger = logging.getLogger(__name__)


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')

def helpCommand(update: Update, context):
    """Отправляет сообщение с информацией об использовании бота."""
    update.message.reply_text('Вот список доступных команд:\n'
                             '/start - начать диалог\n'
                             '/help - показать эту справку\n'
                             '/find_phone_number - найти телефонные номера\n'
                             '/find_email - найти email адреса\n'
                             '/verify_password - проверить сложность пароля\n'
                             '/get_release - о релизе\n'
                             '/get_uname - об архитектуры\n'
                             '/get_uptime - о времени работы\n'
                             '/get_df - состояние файловой системы\n'
                             '/get_free - состояние оперативной памяти\n'
                             '/get_mpstat - производительность системы\n'
                             '/get_w - работающие пользователи\n'
                             '/get_auths - последние 10 входов\n'
                             '/get_critical - последние 5 критических событий\n'
                             '/get_ps - запущенные в системе процессы\n'
                             '/get_ss - используемые порты\n'
                             '/get_apt_list (packagename) - информация об установленных(ом) пакетах(ете)\n'
                             '/get_services - информация о запущенных сервисах\n'
                             '/get_repl_logs - логи репликации\n'
                             '/get_emails - информация о почтовых ящиках\n'
                             '/get_phone_numbers - информация о телефонных номерах\n'
                             )

def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    return 'findPhoneNumbers'

def findPhoneNumbers (update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    user_input = update.message.text 

    logger.info(f'Создается Regex')
    phoneNumRegex = re.compile(r'(\+7|\b8)(-|\s)?(\(\d{3}\)|\d{3})(-|\s)?(\d{3})(-|\s)?(\d{2})(-|\s)?(\d{2})') 

    logger.info(f'Ищем номера в тексте')
    phoneNumberList = phoneNumRegex.findall(user_input) 

    # Обрабатываем случай, когда номеров телефонов нет
    if not phoneNumberList: 
        logger.error(f'Номера не найдены')
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    # Создаем список который будем передавать для записи в бд
    joinedPhoneNumberList = []
    # Преобразуем каждый кортеж из phoneNumberList в строку и добавляем в joinedPhoneNumberList
    for item in phoneNumberList:
        phone_number = ''.join(item)
        joinedPhoneNumberList.append(phone_number)

    # Создаем строку, которую будем выводить юзеру
    foundPhoneNumbers = '' 
    for i in range(len(phoneNumberList)):
        phoneNumber = ''.join(phoneNumberList[i])
        foundPhoneNumbers += f'{i+1}. {phoneNumber}\n' # Записываем очередной номер

    logger.info(f'Найдены номера:\n{foundPhoneNumbers}')
    # Отправляем сообщение пользователю
    update.message.reply_text(foundPhoneNumbers) 
    
    # Сохраняем найденные номера телефонов в контекст
    context.user_data['saved_phones'] = joinedPhoneNumberList

    # Завершаем работу обработчика диалога
    update.message.reply_text("Хотите ли вы сохранить эти номера в базе данных? (yes/no)")
    return SAVE_PHONE_NUMBER_STATE

def findEmailsCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска email адресов: ')
    return 'findEmails'

def findEmails(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    user_input = update.message.text 

    logger.info('Создаем regex для поиска email')
    emailRegex = re.compile(r"([a-zA-Z0-9_.]+@[a-zA-Z0-9-]+.[a-z-.]+)")

    logger.info(f'Ищем email в тексте:\n{user_input}')
    emailList = emailRegex.findall(user_input)
    
    # Обрабатываем случай, когда emailов нет
    if not emailList:
        logger.error(f'Адреса email не найдены в тексте:\n{emailList}')
        update.message.reply_text('Email адреса не найдены')
        return ConversationHandler.END

    # Создаем строку, в которую будем записывать email адреса
    foundEmails = '' 
    for i in range(len(emailList)):
        emailAddress = ''.join(emailList[i])
        foundEmails += f'{i+1}. {emailAddress}\n' # Записываем очередной email

    logger.info(f'Найдены адреса:\n{foundEmails}')
    # Отправляем сообщение пользователю
    update.message.reply_text(foundEmails) 

    # Сохраняем найденные email адреса в контекст
    context.user_data['saved_emails'] = emailList

    # Завершаем работу обработчика диалога
    update.message.reply_text("Хотите ли вы сохранить эти email адреса в базе данных? (yes/no)")
    return SAVE_EMAIL_ADDRESS_STATE


def savePhoneNumber(update: Update, context):
    logger.info(f"Пользователь {update.message.from_user.username} выбрал сохранить номер телефона")
    
    try:
        saved_phones = context.user_data.get('saved_phones', [])
        if not saved_phones:
            raise ValueError("No phones found in context")

        # Цепочка INSERT запросов
        insert_queries = []
        for phone in saved_phones:
            insert_query = f"INSERT INTO phone_numbers (phone_number) VALUES ('{phone}')"
            insert_queries.append(insert_query)
        
        # Чейним и выполняем одним вызовом
        execute_query(';'.join(insert_queries), 'insert')
        logger.info(f"{len(saved_phones)} телефонных номеров успешно сохранены в базе данных")
        update.message.reply_text(f"{len(saved_phones)} телефонных номеров успешно сохранены в базе данных")
    except Exception as error:
        logger.error(f"Ошибка при сохранении телефонного номера: {error}")
        update.message.reply_text("Ошибка при сохранении телефонного номера в базу данных")
    
    return ConversationHandler.END

def saveEmailAddress(update: Update, context):
    logger.info(f"Пользователь {update.message.from_user.username} выбрал сохранить email адрес")
    
    try:
        saved_emails = context.user_data.get('saved_emails', [])
        if not saved_emails:
            raise ValueError("No emails found in context")

        # Цепочка INSERT запросов
        insert_queries = []
        for email in saved_emails:
            insert_query = f"INSERT INTO email_addresses (email_address) VALUES ('{email}')"
            insert_queries.append(insert_query)
        
        # Чейним и выполняем одним вызовом
        execute_query(';'.join(insert_queries), 'insert')
        logger.info(f"{len(saved_emails)} email адресов успешно сохранены в базе данных")
        update.message.reply_text(f"{len(saved_emails)} email адресов успешно сохранены в базе данных")
    except Exception as error:
        logger.error(f"Ошибка при сохранении email адреса: {error}")
        update.message.reply_text("Ошибка при сохранении email адреса в базу данных")
    
    return ConversationHandler.END

def declineSaving(update: Update, context):
    logger.info(f"Пользователь {update.message.from_user.username} отменил сохранение")
    update.message.reply_text("Сохранение отменено")
    return ConversationHandler.END


def checkPasswordCommand(update: Update, context):
    update.message.reply_text('Введите ваш пароль для проверки: ')
    return 'checkPassword'

def checkPassword(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    user_password = update.message.text 

    if not user_password:
        logger.error(f'Пустая строка:\n{user_password}')
        update.message.reply_text('Передана пустая строка')
        return # Завершаем выполнение функции

    logger.info('Создаем паттерн для проверки пароля')
    pattern = r'^(?=.*[A-Z])(?=.*[!@#$%^&*()])(?=.*[0-9])(?=.*[a-z]).{8}$'

    if re.match(pattern, user_password):
        logger.info(f'Пароль пользователя {update.message.from_user.username} сложный!')
        update.message.reply_text(f"{user_password} - Пароль сложный") 
        return ConversationHandler.END 
    else:
        logger.info(f'Пароль пользователя {update.message.from_user.username} простой!')
        update.message.reply_text(f"{user_password} - Пароль простой") 
        return ConversationHandler.END 

def connectToHost(command):
    """Подключение к хосту и выполнение команды."""
    try:
        logger.info(f'Выполняется подключение к ${RM_HOST}')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
        
        logger.info(f'Выполняется команда ${command}')
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read() + stderr.read()
        error = stderr.read()
        
        if error:
            logger.error(f'Ошибка при выполнении команды: {error}')
            return None

        logger.info(f'Подключение закрывается')
        client.close()
        return str(output).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    
    except Exception as e:
        logger.error(f'Ошибка при подключении к хосту: {str(e)}')
        return None

def execute_query(query: str, query_type: str, params: Union[List, tuple] = None):
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE
        )
        
        cursor = connection.cursor()
        
        # Исполнить несколько запросов если они соединены ;
        if ';' in query:
            cursor.execute(query)
        else:
            cursor.execute(query, params)
        
        logger.info(f"Query executed: {query}")
        
        if query_type == 'insert':
            connection.commit()
            logger.info("Выполнен INSERT")
        elif query_type == 'select':
            result = cursor.fetchall()
            logger.info(f"SELECT вернул {len(result)} записей")
            return result
        
        return None
    
    except (Exception, Error) as error:
        logger.error(f"Ошибка выполнения запроса: {error}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            logger.info("Подключение закрыто")


def getRelease(update: Update, context):
    """3.1.1 О релизе - /get_release"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "lsb_release -a"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о релизе')

def getUname(update: Update, context):
    """3.1.1 Об архитектуре - /get_uname"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "uname -a"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о системе')

def getUptime(update: Update, context):
    """3.1.1 О времени работы - /get_uptime"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "uptime"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о времени работы')

def getDf(update: Update, context):
    """3.1.1 О состоянии файловой системы - /get_df"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "df -h"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о состоянии файловой системы')

def getFree(update: Update, context):
    """3.1.1 О состоянии оперативной памяти - /get_free"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "free -h"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о состоянии оперативной памяти')

def getMpstat(update: Update, context):
    """3.1.1 О производительности системы - /get_mpstat"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "mpstat"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о производительности системы')

def getW(update: Update, context):
    """3.1.1 О работающих в системе пользователях - /get_w"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "w"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о работающих в системе пользователях')

def getAuths(update: Update, context):
    """3.1.1 О последних 10 входах - /get_auths"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "last -n 10"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о последних 10 входах')

def getCritical(update: Update, context):
    """3.1.1 О последних 5 критических событий - /get_critical"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "echo {} | sudo -S grep -i 'critical' /var/log/syslog | tail -n 5".format(RM_PASSWORD)
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о последних 5 критических событий')

def getPs(update: Update, context):
    """3.1.1 О запущенных процессах в системе - /get_ps"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "ps -f"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о запущенных процессах в системе')
def getSs(update: Update, context):
    """3.1.1 Об используемых портах в системе - /get_ss"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "ss -tulnp"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию об используемых портах в системе')

def getAptList(update: Update, context):
    """Обработка команды /get_apt_list"""
    logger.info(f'Пользователь {update.effective_user.username} ввел команду /get_apt_list')
    
    reply_text = "Какую информацию вы хотите получить об установленных пакетах?\n\n" \
                 "/all - Вывести список всех установленных пакетов\n" \
                 "/search <название> - Поиск информации о конкретном пакете"
    
    update.message.reply_text(reply_text)
    
    return GET_APT_LIST_STATE

def showAllPackages(update: Update, context):
    """Вывод списка всех установленных пакетов"""
    logger.info("Пользователь выбрал вывод списка всех пакетов")
    
    command = "dpkg --list | grep '^ii'"
    result = connectToHost(command)
    
    if result:
        # Разделяем результат на части до 4096 символов
        parts = [result[i:i+4096] for i in range(0, len(result), 4096)]
        
        for part in parts:
            update.message.reply_text(part)
    else:
        update.message.reply_text('Не удалось получить список пакетов')
    
    return ConversationHandler.END

def searchPackage(update: Update, context):
    """Поиск информации о конкретном пакете"""
    logger.info("Пользователь выбрал поиск информации о пакете")
    
    query = update.message.text.split()[1].lower()
    command = f"apt show {query}"
    result = connectToHost(command)
    
    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось найти информацию об этом пакете')
    
    return ConversationHandler.END

def getServices(update: Update, context):
    """3.1.1 О запущенных сервисах в системе - /get_services"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "systemctl list-units --type=service --state=running --no-pager"
    result = connectToHost(command)
    
    if result:
        # Разделяем результат на части до 4096 символов
        parts = [result[i:i+4096] for i in range(0, len(result), 4096)]
        
        for part in parts:
            update.message.reply_text(part)
    else:
        update.message.reply_text('Не удалось получить информацию о запущенных сервисах в системе')

def getReplLogs(update: Update, context):
    """3.1.1 Получить логи репликации - /get_repl_logs"""
    
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    command = "cat /var/log/postgresql/postgresql.log | grep repl | tail -n 15"
    result = connectToHost(command)
    
    if result:
        # Разделяем результат на части до 4096 символов
        parts = [result[i:i+4096] for i in range(0, len(result), 4096)]
        
        for part in parts:
            update.message.reply_text(part)
    else:
        update.message.reply_text('Не удалось получить логи репликации')
    """
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    try:
        # Выполнение команды для получения логов
        result = subprocess.run(
            ["bash", "-c", f"cat {LOG_FILE_PATH} | grep repl | tail -n 15"],
            capture_output=True,
            text=True
        )
        logs = result.stdout
        if logs:
            update.message.reply_text(f"Последние репликационные логи:\n{logs}")
        else:
            update.message.reply_text("Репликационные логи не найдены.")
    except Exception as e:
        update.message.reply_text(f"Ошибка при получении логов: {str(e)}")
    """

def getEmails(update: Update, context):
    """3.1.1 О хранимых в базе email адресах - /get_emails"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')

    try:
        emails = execute_query(query="SELECT * FROM email_addresses;", query_type="select")
        for email in emails:
            update.message.reply_text(email)
        logger.info("Команда успешно выполнена")
    except Exception as error:
        logger.error(f"Ошибка при получении email адресов: {error}")
        update.message.reply_text('Не удалось получить информацию о хранимых в базе email адресах')

def getPhoneNumbers(update: Update, context):
    """3.1.1 О хранимых в базе телефонных номерах - /get_phone_numbers"""
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    
    try:
        phone_numbers = execute_query(query="SELECT * FROM phone_numbers;", query_type="select")
        for phone_number in phone_numbers:
            update.message.reply_text(phone_number)
        logger.info("Команда успешно выполнена")
    except Exception as error:
        logger.error(f"Ошибка при получении телефонных номеров: {error}")
        update.message.reply_text('Не удалось получить информацию о хранимых в базе телефонных номеров')

def checkPasswordCommand(update: Update, context):
    update.message.reply_text('Введите ваш пароль для проверки: ')
    return 'checkPassword'

def checkPassword(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    user_password = update.message.text 

    if not user_password:
        logger.info(f'Пустая строка:\n{user_password}')
        update.message.reply_text('Передана пустая строка')
        return # Завершаем выполнение функции

    logger.info('Создаем паттерн для проверки пароля')
    pattern = r'^(?=.*[A-Z])(?=.*[!@#$%^&*()])(?=.*[0-9])(?=.*[a-z]).{8}$'

    if re.match(pattern, user_password):
        logger.info(f'Пароль пользователя {update.message.from_user.username} сложный!')
        update.message.reply_text(f"{user_password} - Пароль сложный") 
        return ConversationHandler.END 
    else:
        logger.info(f'Пароль пользователя {update.message.from_user.username} простой!')
        update.message.reply_text(f"{user_password} - Пароль простой") 
        return ConversationHandler.END 
    
def echo(update: Update, context):
    update.message.reply_text(update.message.text)


def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            SAVE_PHONE_NUMBER_STATE: [MessageHandler(Filters.regex(r'^yes$'), savePhoneNumber),
                                    MessageHandler(Filters.regex(r'^no$'), declineSaving)],
        },
        fallbacks=[]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailsCommand)],
        states={
            'findEmails': [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            SAVE_EMAIL_ADDRESS_STATE: [MessageHandler(Filters.regex(r'^yes$'), saveEmailAddress),
                                    MessageHandler(Filters.regex(r'^no$'), declineSaving)],
        },
        fallbacks=[]
    )

    # Обработчик диалога проверки пароля
    convHandlerCheckPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', checkPasswordCommand)],
        states={
            'checkPassword': [MessageHandler(Filters.text & ~Filters.command, checkPassword)],

        },
        fallbacks=[]
    )

    convHandlerGetRelease = ConversationHandler(
        entry_points=[CommandHandler('get_release', getRelease)],
        states={
            'getRelease': [MessageHandler(Filters.text & ~Filters.command, getRelease)]
        },
        fallbacks=[]
    )

    convHandlerGetUname = ConversationHandler(
        entry_points=[CommandHandler('get_uname', getUname)],
        states={
            'getUname': [MessageHandler(Filters.text & ~Filters.command, getUname)]
        },
        fallbacks=[]
    )

    convHandlerGetUptime = ConversationHandler(
        entry_points=[CommandHandler('get_uptime', getUptime)],
        states={
            'getUptime': [MessageHandler(Filters.text & ~Filters.command, getUptime)]
        },
        fallbacks=[]
    )

    convHandlerGetDf = ConversationHandler(
        entry_points=[CommandHandler('get_df', getDf)],
        states={
            'getDf': [MessageHandler(Filters.text & ~Filters.command, getDf)]
        },
        fallbacks=[]
    )

    convHandlerGetFree = ConversationHandler(
        entry_points=[CommandHandler('get_free', getFree)],
        states={
            'getFree': [MessageHandler(Filters.text & ~Filters.command, getFree)]
        },
        fallbacks=[]
    )

    convHandlerGetMpstat = ConversationHandler(
        entry_points=[CommandHandler('get_mpstat', getMpstat)],
        states={
            'getMpstat': [MessageHandler(Filters.text & ~Filters.command, getMpstat)]
        },
        fallbacks=[]
    )

    convHandlerGetW = ConversationHandler(
        entry_points=[CommandHandler('get_w', getW)],
        states={
            'getW': [MessageHandler(Filters.text & ~Filters.command, getW)]
        },
        fallbacks=[]
    )

    convHandlerGetAuths = ConversationHandler(
        entry_points=[CommandHandler('get_auths', getAuths)],
        states={
            'getAuths': [MessageHandler(Filters.text & ~Filters.command, getAuths)]
        },
        fallbacks=[]
    )

    convHandlerGetCritical = ConversationHandler(
        entry_points=[CommandHandler('get_critical', getCritical)],
        states={
            'getCritical': [MessageHandler(Filters.text & ~Filters.command, getCritical)]
        },
        fallbacks=[]
    )

    convHandlerGetPs = ConversationHandler(
        entry_points=[CommandHandler('get_ps', getPs)],
        states={
            'getPs': [MessageHandler(Filters.text & ~Filters.command, getPs)]
        },
        fallbacks=[]
    )

    convHandlerGetSs = ConversationHandler(
        entry_points=[CommandHandler('get_ss', getSs)],
        states={
            'getSs': [MessageHandler(Filters.text & ~Filters.command, getSs)]
        },
        fallbacks=[]
    )

    conv_handler_get_apt_list = ConversationHandler(
    entry_points=[CommandHandler('get_apt_list', getAptList)],
    states={
        GET_APT_LIST_STATE: [
            MessageHandler(Filters.regex(r'^/all$'), showAllPackages),
            MessageHandler(Filters.regex(r'^/search\s+(.+)$'), searchPackage)
        ]
    },
    fallbacks=[]
    )

    convHandlerGetServices = ConversationHandler(
        entry_points=[CommandHandler('get_services', getServices)],
        states={
            'getServices': [MessageHandler(Filters.text & ~Filters.command, getServices)]
        },
        fallbacks=[]
    )

    convHandlerGetReplLogs = ConversationHandler(
        entry_points=[CommandHandler('get_repl_logs', getReplLogs)],
        states={
            'getReplLogs': [MessageHandler(Filters.text & ~Filters.command, getReplLogs)]
        },
        fallbacks=[]
    )

    convHandlerGetEmails = ConversationHandler(
        entry_points=[CommandHandler('get_emails', getEmails)],
        states={
            'getEmails': [MessageHandler(Filters.text & ~Filters.command, getEmails)]
        },
        fallbacks=[]
    )

    convHandlerGetPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('get_phone_numbers', getPhoneNumbers)],
        states={
            'getPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, getPhoneNumbers)]
        },
        fallbacks=[]
    )

	# Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmails)
    dp.add_handler(convHandlerCheckPassword)
    dp.add_handler(convHandlerGetRelease)
    dp.add_handler(convHandlerGetUname)
    dp.add_handler(convHandlerGetUptime)
    dp.add_handler(convHandlerGetDf)
    dp.add_handler(convHandlerGetFree)
    dp.add_handler(convHandlerGetMpstat)
    dp.add_handler(convHandlerGetW)
    dp.add_handler(convHandlerGetAuths)
    dp.add_handler(convHandlerGetCritical)
    dp.add_handler(convHandlerGetPs)
    dp.add_handler(convHandlerGetSs)
    dp.add_handler(conv_handler_get_apt_list)
    dp.add_handler(convHandlerGetServices)
    dp.add_handler(convHandlerGetReplLogs)
    dp.add_handler(convHandlerGetEmails)
    dp.add_handler(convHandlerGetPhoneNumbers)

	# Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
		
	# Запускаем бота
    updater.start_polling(timeout=60)

	# Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
