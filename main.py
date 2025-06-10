import os
from datetime import datetime
from dotenv import load_dotenv
import requests
from google_sheet import get_birthdays_data
import calendar
from datetime import datetime, timedelta

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TOPIC_ID = os.getenv("TOPIC_ID")

MONTHS_RU = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}


def find_upcoming_birthdays(birthdays):
    today = datetime.today().date()
    upcoming = []

    for person in birthdays:
        raw_date = person.get('Дата', '')
        date_str = str(raw_date).strip().lower().replace('  ', ' ')
        # print(f"Обрабатываем дату: {repr(date_str)}")

        # Поддержка формата "дд.мм" и "дд месяц"
        if '.' in date_str:
            try:
                day, month = map(int, date_str.split('.'))
            except Exception:
                continue
        elif ' ' in date_str:
            try:
                day_part, month_part = date_str.split(' ', 1)
                day = int(day_part)
                month = MONTHS_RU.get(month_part.strip(), 0)
                if month == 0:
                    continue
            except Exception:
                continue
        else:
            continue

        try:
            bday_this_year = datetime(year=today.year, month=month, day=day).date()
        except ValueError:
            continue

        if bday_this_year < today:
            bday_this_year = bday_this_year.replace(year=today.year + 1)

        days_diff = (bday_this_year - today).days
        # print(f"  -> До дня рождения: {days_diff} дней")

        if days_diff in [0, 1, 2, 3]:
            upcoming.append({
                'name': person.get('Именниник', 'Без имени'),
                'days_left': days_diff
            })

    return upcoming



def build_message(delta, person):
    name = person['name']

    if delta == 3:
        return f"📢 Через 3 дня день рождения у {name}! Не забудьте подготовиться 🎉"
    elif delta == 2:
        return f"📢 Осталось 2 дня до дня рождения {name}! 🎊"
    elif delta == 1:
        return f"📢 Завтра день рождения у {name}! Готовим поздравления 🎁"
    elif delta == 0:
        return f"🎉 Сегодня день рождения у {name}! Поздравляем от всей души! 🎂"


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "message_thread_id": int(TOPIC_ID),
        "text": text,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print("❌ Ошибка отправки в Telegram:", response.text)


def main():
    birthdays = get_birthdays_data()

    print(f"🔎 Найдено {len(birthdays)} записей из таблицы")
    upcoming = find_upcoming_birthdays(birthdays)

    if not upcoming:
        print("✅ Сегодня напоминаний нет.")
        return

    for person in upcoming:
        delta = person['days_left']
        message = build_message(delta, person)
        print(f"📤 Отправка сообщения: {message}")
        send_telegram_message(message)


if __name__ == "__main__":
    main()
