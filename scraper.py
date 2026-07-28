import re
import sqlite3
import time
from bs4 import BeautifulSoup
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
}


def parse_work_ua(keyword):
    """Парсер для Work.ua"""
    formatted_keyword = keyword.replace(" ", "+")
    url = f"https://www.work.ua/jobs-{formatted_keyword}/"
    vacancies = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        job_cards = soup.find_all("div", class_=re.compile(r"job-link"))
        for card in job_cards:
            a_tag = card.find("a", href=re.compile(r"^/jobs/\d+/"))
            if not a_tag:
                continue

            title = a_tag.text.strip()
            link = "https://www.work.ua" + a_tag["href"]

            company = "Не указана"
            company_tag = card.find("span", class_="bold") or card.find("b")
            if company_tag and company_tag.text.strip() != title:
                company = company_tag.text.strip()

            location = "Украина"
            loc_tag = card.find("span", class_="text-indent")
            if loc_tag:
                location = loc_tag.text.strip()

            salary_usd = None
            for b_tag in card.find_all("b"):
                text = b_tag.text.replace("\xa0", "").replace(" ", "")
                if "грн" in text.lower() or "$" in text:
                    numbers = re.findall(r"\d+", text)
                    if numbers:
                        val = int(numbers[0])
                        salary_usd = (
                            round(val / 41) if "грн" in text.lower() else val
                        )
                        break

            vacancies.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary_usd": salary_usd,
                    "link": link,
                    "source": "Work.ua",
                }
            )
    except Exception as e:
        print(f"Ошибка Work.ua: {e}")

    return vacancies


def parse_djinni(keyword):
    """Парсер для Djinni.co"""
    formatted_keyword = keyword.replace(" ", "+")
    url = f"https://djinni.co/jobs/?primary_keyword={formatted_keyword}"
    vacancies = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        cards = soup.find_all("li", class_=re.compile(r"list-jobs__item"))
        for card in cards:
            title_tag = card.find("a", class_="job-list-item__link")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link = "https://djinni.co" + title_tag["href"]

            company_tag = card.find("a", class_="mr-2")
            company = company_tag.text.strip() if company_tag else "Djinni Company"

            salary_usd = None
            salary_tag = card.find("span", class_="public-salary-m")
            if salary_tag:
                numbers = re.findall(r"\d+", salary_tag.text.replace(" ", ""))
                if numbers:
                    salary_usd = int(numbers[-1])

            vacancies.append(
                {
                    "title": title,
                    "company": company,
                    "location": "Remote / Ukraine",
                    "salary_usd": salary_usd,
                    "link": link,
                    "source": "Djinni",
                }
            )
    except Exception as e:
        print(f"Ошибка Djinni: {e}")

    return vacancies

def save_vacancies_to_db(vacancies):
    """Сохранение в БД + отправка новых вакансий от $500 в Telegram"""
    conn = sqlite3.connect('job_search_ua.db')
    cursor = conn.cursor()
    added_count = 0
    
    for vac in vacancies:
        try:
            cursor.execute('''
                INSERT INTO vacancies (title, company, location, salary_usd, link, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (vac['title'], vac['company'], vac['location'], vac['salary_usd'], vac['link'], vac['source']))
            added_count += 1
            
            # Отправляем в Telegram ТОЛЬКО если ЗП указана и она >= $500
            if vac['salary_usd'] is not None and vac['salary_usd'] >= 500:
                send_telegram_notification(
                    vac['title'], 
                    vac['company'], 
                    vac['salary_usd'], 
                    vac['link'], 
                    vac['source']
                )
            
        except sqlite3.IntegrityError:
            # Если вакансия уже была в базе — пропускаем
            pass
            
    conn.commit()
    conn.close()
    return added_count


if __name__ == "__main__":
    keywords = ["python", "data analyst", "sql"]
    print("🚀 Собираем вакансии с Work.ua и Djinni...")

    for kw in keywords:
        print(f"\nИщем '{kw}'...")

        w_vacs = parse_work_ua(kw)
        w_added = save_vacancies_to_db(w_vacs)
        print(f"  • Work.ua: найдено {len(w_vacs)}, добавлено: {w_added}")

        d_vacs = parse_djinni(kw)
        d_added = save_vacancies_to_db(d_vacs)
        print(f"  • Djinni: найдено {len(d_vacs)}, добавлено: {d_added}")

        time.sleep(1)

    print("\n✅ Сбор успешно окончен!")