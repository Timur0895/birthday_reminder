# -*- coding: utf-8 -*-
import os
import requests
import calendar
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

from google_sheet import get_birthdays_data  # твоя функция

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TOPIC_ID = os.getenv("TOPIC_ID")  # может быть None / "" — тогда шлём без темы

# для парсинга формата "дд месяц" (генитив)
MONTHS_RU = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}

# для заголовка дайджеста "в сентябре" (предложный падеж)
MONTHS_RU_PP = {
    1: "январе", 2: "феврале", 3: "марте", 4: "апреле",
    5: "мае", 6: "июне", 7: "июле", 8: "августе",
    9: "сентябре", 10: "октябре", 11: "ноябре", 12: "декабре",
}


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------

def _parse_birthday_to_md(date_str: str):
    """
    Принять строку из таблицы и вернуть (month, day) или None.
    Поддерживает:
      - "дд.мм"  (например, "09.27" или "9.07")
      - "дд месяц" (например, "27 сентября")
    Год игнорируется.
    """
    if not date_str:
        return None
    s = str(date_str).strip().lower().replace('  ', ' ')
    # "дд.мм"
    if '.' in s:
        try:
            day, month = map(int, s.split('.'))
            return (month, day)
        except Exception:
            return None
    # "дд месяц"
    if ' ' in s:
        try:
            day_part, month_part = s.split(' ', 1)
            day = int(day_part)
            month = MONTHS_RU.get(month_part.strip(), 0)
            if month:
                return (month, day)
        except Exception:
            return None
    return None


def _today() -> date:
    # если нужен другой TZ — можно заменить на pytz/zoneinfo
    return datetime.today().date()


def send_telegram_message(text: str):
    assert TELEGRAM_BOT_TOKEN, "TELEGRAM_BOT_TOKEN is empty"
    assert CHAT_ID, "CHAT_ID is empty"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    # безопасно: если темы нет, не отправляем message_thread_id
    if TOPIC_ID and str(TOPIC_ID).strip():
        try:
            payload["message_thread_id"] = int(TOPIC_ID)
        except Exception:
            pass

    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        print("❌ Ошибка отправки в Telegram:", r.text)


# ---------- ТВОИ ЕЖЕДНЕВНЫЕ НАПОМИНАНИЯ ----------

def find_upcoming_birthdays(birthdays):
    today = _today()
    upcoming = []

    for person in birthdays:
        raw_date = person.get('Дата', '')
        md = _parse_birthday_to_md(raw_date)
        if not md:
            continue
        month, day = md

        # цель — ближайшая дата рождения (в этом или следующем году)
        try:
            bday_this_year = date(year=today.year, month=month, day=day)
        except ValueError:
            continue

        if bday_this_year < today:
            bday_this_year = bday_this_year.replace(year=today.year + 1)

        days_diff = (bday_this_year - today).days
        if days_diff in (0, 1, 2, 3):
            upcoming.append({
                'name': person.get('Именниник', 'Без имени'),
                'days_left': days_diff
            })

    return upcoming


def build_message(delta, person):
    name = person['name']
    tag = '@' + '@timur0x01'  # можешь заменить/убрать

    if delta == 3:
        return f"📢 Через 3 дня день рождения у {name}! Не забудьте подготовиться 🎉\n{tag}"
    elif delta == 2:
        return f"📢 Осталось 2 дня до дня рождения {name}! 🎊\n{tag}"
    elif delta == 1:
        return f"📢 Завтра день рождения у {name}! Готовим поздравления 🎁\n{tag}"
    elif delta == 0:
        return f"📢 Сегодня день рождения у {name} 🎂\n{tag}"


# ---------- НОВОЕ: ЕЖЕМЕСЯЧНЫЙ ДАЙДЖЕСТ ----------

def birthdays_in_month(birthdays, target_month: int):
    """
    Вернуть список [{'name': str, 'day': int}] для заданного месяца.
    Сортируем по дню.
    """
    result = []
    for person in birthdays:
        raw_date = person.get('Дата', '')
        md = _parse_birthday_to_md(raw_date)
        if not md:
            continue
        month, day = md
        if month == target_month:
            result.append({
                'name': person.get('Именниник', 'Без имени'),
                'day': int(day),
            })
    result.sort(key=lambda x: x['day'])
    return result


def build_monthly_digest_message(month: int, items):
    title = f"🎂 Именинники в {MONTHS_RU_PP.get(month, '')}"
    if not items:
        return f"{title}\n\nВ этом месяце именинников нет."

    lines = [f"• {day:02d} числа — {name}" for (day, name) in [(it['day'], it['name']) for it in items]]
    body = "\n".join(lines)
    return f"{title}\n\n{body}\n\nНе забываем поздравить! 🥳"


MONTHS_RU_NOM = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

def send_monthly_digest_if_first_day(birthdays):
    """
    Без проверок даты: всегда формирует дайджест за текущий месяц,
    печатает его в логи и отправляет в Telegram.
    """
    today = _today()
    month_items = birthdays_in_month(birthdays, today.month)

    # печать в логи, чтобы сразу видеть в Actions
    print(f"🗓 Дайджест за месяц: {today.month:02d}.{today.year}")
    if not month_items:
        print("— В этом месяце именинников нет.")
    else:
        print("— Именинники:")
        for it in month_items:
            print(f"   • {it['day']:02d} — {it['name']}")

    # готовим и шлём сообщение в Telegram
    msg = build_monthly_digest_message(today.month, month_items)
    send_telegram_message(msg)
    print("📤 Отправлен ежемесячный дайджест:\n", msg)

    return msg  # на всякий случай возвращаем текст





# ---------- MAIN ----------

def main():
    birthdays = get_birthdays_data()
    print(f"🔵 Найдено {len(birthdays)} записей из таблицы")

    # всегда формируем дайджест за текущий месяц
    send_monthly_digest_if_first_day(birthdays)




if __name__ == "__main__":
    main()
