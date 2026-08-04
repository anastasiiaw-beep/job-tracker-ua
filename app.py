import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# Настройки страницы
st.set_page_config(
    page_title="UA Job Analytics & Tracker", page_icon="📊", layout="wide"
)


# Подключение к БД
def get_connection():
    return sqlite3.connect("job_search_ua.db")


# Загрузка данных вакансий
# Загрузка данных вакансий
def load_data():
    conn = get_connection()
    cursor = conn.cursor()
    # Проверяем, существует ли таблица vacancies
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vacancies'"
    )
    if not cursor.fetchone():
        # Если таблицы нет, создаем её
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                location TEXT,
                salary_usd REAL,
                source TEXT,
                link TEXT
            )
        """)
        conn.commit()

    df = pd.read_sql_query("SELECT * FROM vacancies", conn)
    conn.close()
    return df

# Создание и проверка структуры таблицы откликов
def init_applications_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Проверяем, есть ли таблица applications и корректны ли колонки
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
    )
    table_exists = cursor.fetchone()

    if table_exists:
        cursor.execute("PRAGMA table_info(applications)")
        columns = [col[1] for col in cursor.fetchall()]
        if "vacancy_title" not in columns:
            cursor.execute("DROP TABLE applications")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vacancy_title TEXT,
            company TEXT,
            date_applied TEXT,
            status TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


init_applications_db()

# Заголовок
st.title("📊 UA Job Search & Analytics Dashboard")

# Переключатели-вкладки
tab1, tab2 = st.tabs(["🔍 Поиск и Аналитика", "📌 Мои Отклики"])

df = load_data()

# ==========================================
# ВКЛАДКА 1: ПОИСК И АНАЛИТИКА
# ==========================================
with tab1:
    if df.empty:
        st.warning(
            "База данных пока пуста. Запустите scraper.py для сбора данных."
        )
    else:
        # --- БОКОВАЯ ПАНЕЛЬ (ФИЛЬТРЫ) ---
        st.sidebar.header("🔍 Фильтры")

        sources = st.sidebar.multiselect(
            "Источник",
            options=df["source"].unique(),
            default=df["source"].unique(),
        )

        max_val = (
            int(df["salary_usd"].dropna().max())
            if not df["salary_usd"].dropna().empty
            else 3000
        )
        min_sal = st.sidebar.slider(
            "Минимальная ЗП ($)",
            min_value=0,
            max_value=max_val,
            value=0,
            step=100,
        )

        search_query = st.sidebar.text_input(
            "Поиск (должность / компания)", ""
        )

        # Применение фильтров
        filtered_df = df[df["source"].isin(sources)]

        if min_sal > 0:
            filtered_df = filtered_df[filtered_df["salary_usd"] >= min_sal]

        if search_query:
            filtered_df = filtered_df[
                filtered_df["title"].str.contains(
                    search_query, case=False, na=False
                )
                | filtered_df["company"].str.contains(
                    search_query, case=False, na=False
                )
            ]

        # --- МЕТРИКИ ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Всего вакансий", len(filtered_df))
        col2.metric(
            "С указанной ЗП", filtered_df["salary_usd"].notnull().sum()
        )

        avg_sal = filtered_df["salary_usd"].mean()
        max_sal = filtered_df["salary_usd"].max()
        col3.metric(
            "Средняя ЗП ($)",
            f"${avg_sal:.0f}" if pd.notnull(avg_sal) else "N/A",
        )
        col4.metric(
            "Макс. ЗП ($)",
            f"${max_sal:.0f}" if pd.notnull(max_sal) else "N/A",
        )

        st.markdown("---")

        # --- ГРАФИКИ ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Источники вакансий")
            fig_source = px.pie(
                filtered_df,
                names="source",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig_source, use_container_width=True)

        with c2:
            st.subheader("Распределение зарплат ($)")
            sal_data = filtered_df.dropna(subset=["salary_usd"])
            if not sal_data.empty:
                fig_sal = px.histogram(
                    sal_data,
                    x="salary_usd",
                    nbins=15,
                    color="source",
                    barmode="overlay",
                )
                st.plotly_chart(fig_sal, use_container_width=True)
            else:
                st.info("Нет данных по зарплатам для выбранных фильтров.")

        # --- ТАБЛИЦА ВАКАНСИЙ ---
        st.subheader("📋 Список вакансий")
        st.dataframe(
            filtered_df[
                ["title", "company", "location", "salary_usd", "source", "link"]
            ],
            column_config={
                "link": st.column_config.LinkColumn("Ссылка"),
                "salary_usd": st.column_config.NumberColumn(
                    "ЗП ($)", format="$%d"
                ),
                "title": "Должность",
                "company": "Компания",
                "location": "Локация",
                "source": "Источник",
            },
            use_container_width=True,
            hide_index=True,
        )

# ==========================================
# ВКЛАДКА 2: МОИ ОТКЛИКИ
# ==========================================
with tab2:
    st.subheader("➕ Добавить новый отклик")

    with st.form("add_app_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            v_title = st.text_input("Должность (например, Data Analyst)")
            v_company = st.text_input("Компания")
        with f_col2:
            v_date = st.date_input("Дата отклика")
            v_status = st.selectbox(
                "Статус",
                [
                    "Отправлено",
                    "Скрининг / HR",
                    "Тестовое",
                    "Интервью",
                    "Оффер",
                    "Отказ",
                ],
            )

        v_notes = st.text_area("Заметки (ссылка, контакты, с кем общались)")
        submit_btn = st.form_submit_button("Сохранить отклик")

        if submit_btn:
            if v_title and v_company:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO applications (vacancy_title, company, date_applied, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        v_title,
                        v_company,
                        str(v_date),
                        v_status,
                        v_notes,
                    ),
                )
                conn.commit()
                conn.close()
                st.success(f"Отклик в {v_company} успешно сохранен!")
                st.rerun()
            else:
                st.error("Пожалуйста, укажите должность и компанию.")

    st.markdown("---")
    st.subheader("📑 История моих откликов")

    conn = get_connection()
    apps_df = pd.read_sql_query(
        "SELECT vacancy_title AS 'Должность', company AS 'Компания', date_applied AS 'Дата', status AS 'Статус', notes AS 'Заметки' FROM applications ORDER BY id DESC",
        conn,
    )
    conn.close()

    if apps_df.empty:
        st.info("Вы пока не добавили ни одного отклика.")
    else:
        # Считаем количество по статусам
        status_counts = apps_df["Статус"].value_counts().reset_index()
        status_counts.columns = ["Статус", "Количество"]

        # Выводим воронку статусов
        st.subheader("📊 Воронка откликов")
        fig_status = px.bar(
            status_counts,
            x="Статус",
            y="Количество",
            color="Статус",
            text="Количество",
            title="Распределение по этапам",
        )
        st.plotly_chart(fig_status, use_container_width="stretch")

        # Выводим саму таблицу
        st.dataframe(apps_df, use_container_width="stretch", hide_index=True)