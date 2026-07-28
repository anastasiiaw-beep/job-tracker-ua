import sqlite3

DB_NAME = "job_search_ua.db"


def init_db():
    """Инициализация базы данных и создание таблиц."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица для сохраненных вакансий с сайтов
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            salary_usd REAL,
            link TEXT UNIQUE,
            source TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Таблица для учета личных откликов и статусов собеседований
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vacancy_id INTEGER,
            company_name TEXT NOT NULL,
            position TEXT NOT NULL,
            applied_date DATE,
            status TEXT DEFAULT 'Отклик отправлен',
            rejection_reason TEXT,
            notes TEXT,
            FOREIGN KEY (vacancy_id) REFERENCES vacancies (id)
        )
    """
    )

    conn.commit()
    conn.close()
    print("База данных успешно инициализирована!")


if __name__ == "__main__":
    init_db()