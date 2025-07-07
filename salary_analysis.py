from telethon import TelegramClient
import pandas as pd
import re
import requests
from datetime import datetime

# 🔑 Авторизация
api_id = 27488438
api_hash = '9d32823e417a75e3b75ad6f64d34f886'
channel_username = 'salary_pm'  # без @

client = TelegramClient('session_salary_pm', api_id, api_hash)

# 💱 Получение курса ЦБ РФ
def get_cbr_currency_rate(currency):
    today = datetime.now().strftime('%d/%m/%Y')
    url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={today}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    pattern = r'<CharCode>' + currency + r'</CharCode>.*?<Value>([\d,]+)</Value>'
    match = re.search(pattern, response.text, re.DOTALL)
    if match:
        rate = float(match.group(1).replace(',', '.'))
        return rate
    else:
        return None

async def main():
    await client.start()
    all_posts = []

    # Получаем курсы валют заранее
    eur_rate = get_cbr_currency_rate('EUR')
    usd_rate = get_cbr_currency_rate('USD')

    async for message in client.iter_messages(channel_username, reverse=True):
        if not message.text:
            continue
        text = message.text

        # Грейд, должность, компания
        header_match = re.search(r'⚡️\s*(\w+)\s+([A-Za-zА-Яа-яЁё\s]+?)\s+в\s+([A-Za-zA-Яа-яЁё\s]+)', text)
        grade = header_match.group(1).strip() if header_match else 'Не указан'
        position = header_match.group(2).strip() if header_match else 'Не указан'
        company = header_match.group(3).strip() if header_match else 'Не указан'

        # Зарплата
        salary_match = re.search(r'Зарплата:\s*([\d\s]+)\s*(€|\$|₽)?', text)
        salary_rub = 'Не указан'
        salary_base = None
        currency = None
        if salary_match:
            salary_str = salary_match.group(1).replace(' ', '').strip()
            currency = salary_match.group(2)
            if salary_str != '':
                salary_amount = int(salary_str)
                salary_base = salary_amount
                if currency == '€' and eur_rate:
                    salary_rub = round(salary_amount * eur_rate / 1000) * 1000
                elif currency == '$' and usd_rate:
                    salary_rub = round(salary_amount * usd_rate / 1000) * 1000
                else:
                    salary_rub = salary_amount

        # Премия
        premia_match = re.search(r'Премия:\s*(.+?)(\||\n)', text)
        premia_freq = 'Не указан'
        premia_sum = 'Не указан'
        if premia_match:
            premia_freq = premia_match.group(1).strip().capitalize()
            premia_sum_match = re.search(r'\|\s*([^\n]+)', text)
            if premia_sum_match:
                premia_text = premia_sum_match.group(1).strip()
                percent_match = re.search(r'(\d+)% от зп', premia_text)
                if percent_match and salary_base:
                    premia_value = int(percent_match.group(1)) * salary_base / 100
                    premia_sum = round(premia_value * (eur_rate if currency == '€' else usd_rate if currency == '$' else 1) / 1000) * 1000
                else:
                    premia_sum_val = re.search(r'([\d\s]+)\s*(€|\$|₽)?', premia_text)
                    if premia_sum_val:
                        premia_str = premia_sum_val.group(1).replace(' ', '').strip()
                        if premia_str != '':
                            premia_amount = int(premia_str)
                            premia_currency = premia_sum_val.group(2)
                            if premia_currency == '€' and eur_rate:
                                premia_sum = round(premia_amount * eur_rate / 1000) * 1000
                            elif premia_currency == '$' and usd_rate:
                                premia_sum = round(premia_amount * usd_rate / 1000) * 1000
                            else:
                                premia_sum = premia_amount
                        else:
                            premia_sum = 'Не указан'
                    else:
                        premia_sum = 'Не указан'

        # Опыт
        exp_match = re.search(r'Опыт:\s*(.+)', text)
        exp_sfera = 'Не указан'
        exp_company = 'Не указан'
        if exp_match:
            exp_text = exp_match.group(1)
            sfera_match = re.search(r'(\d+)\s+лет в сфере', exp_text)
            company_match = re.search(r'(\d+)\s+лет в компании', exp_text)
            month_sfera_match = re.search(r'(\d+)\s+мес', exp_text)
            if sfera_match:
                exp_sfera = sfera_match.group(1)
            elif month_sfera_match:
                exp_sfera = 'Менее 1 года'
            if company_match:
                exp_company = company_match.group(1)

        # Бонусы
        bonuses_match = re.search(r'Бонусы:\s*(.+?)(Формат работы|Что нравится|Что не нравится|\Z)', text, re.DOTALL)
        bonuses = bonuses_match.group(1).strip().replace('\n', ', ') if bonuses_match else 'Не указан'

        # Формат работы, откуда, длительность
        format_match = re.search(r'Формат работы:\s*(.+?)\s*\((.+?)\)\s*\|\s*(\d+)[-–](\d+)', text)
        format_work = format_match.group(1).strip() if format_match else 'Не указан'
        where_work = format_match.group(2).strip().capitalize() if format_match else 'Не указан'
        duration = format_match.group(4).strip() if format_match else 'Не указан'

        # Что нравится
        like_match = re.search(r'Что нравится в компании\?\s*(.+?)(Что не нравится|\Z)', text, re.DOTALL)
        like = like_match.group(1).strip().replace('\n', ' ') if like_match else 'Не указан'

        # Что не нравится
        dislike_match = re.search(r'Что не нравится\?\s*(.+?)(Комментарий|\[|#|\Z)', text, re.DOTALL)
        dislike = dislike_match.group(1).strip().replace('\n', ' ') if dislike_match else 'Не указан'

        # Дата публикации
        date_published = message.date.strftime('%d.%m.%Y')

        # Ссылка
        link = f"https://t.me/{channel_username}/{message.id}"

        # Добавление в таблицу
        all_posts.append({
            'Название компании': company,
            'Должность': position,
            'Грейд': grade,
            'Зарплата (в руб)': salary_rub,
            'Премия (частотность)': premia_freq,
            'Премия (сумма)': premia_sum,
            'Опыт (в сфере)': exp_sfera,
            'Опыт (в компании)': exp_company,
            'Бонусы': bonuses,
            'Формат работы': format_work,
            'Откуда можно работать': where_work,
            'Длительность рабочего дня': duration,
            'Что нравится': like,
            'Что не нравится': dislike,
            'Дата публикации': date_published,
            'Ссылка на публикацию': link
        })

    # Экспорт
    df = pd.DataFrame(all_posts)
    df.to_excel('Salary_Analysis_All.xlsx', index=False)
    print("✅ Готово. Данные сохранены в Salary_Analysis_All.xlsx")

with client:
    client.loop.run_until_complete(main())
