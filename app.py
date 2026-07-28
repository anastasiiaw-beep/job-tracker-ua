import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Дашборд поиска работы", page_icon="📊", layout="wide"
)


def load_vacancies():
    conn = sqlite3.connect("job_search_ua.db")
    df = pd.read_sql_query("SELECT * FROM vacancies", conn)
    conn.close()
    return df


def load_applications():
    conn = sqlite3.connect("job_search_ua.db")
    df = pd.read_sql_query("SELECT * FROM applications", conn)
    conn.close()
    return df


def add_application(vacancy_id, company, position, status, notes):
    conn = sqlite3.connect("job_search_ua.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO applications (vacancy_id, company_name, position, status, notes)
        VALUES (?, ?, ?, ?, ?)
    """,
        (vacancy_id, company, position, status, notes),
    )
    conn.commit()
    conn.close()


st.title("💼 Панель поиска работы & Аналитика")

df_vacancies = load_vacancies()
df_apps = load_applications()

tab1, tab2, tab3 = st.tabs(
    ["🔍 Поиск вакансий", "📋 Мои отклики", "📊 Аналитика рынка"]
)

with tab1:
    st.sidebar.header("Фильтры")

    if not df_vacancies.empty:
        search_query = st.sidebar.text_input("Поиск по названию:", "")
        sources = df_vacancies["source"].unique().tolist()
        selected_sources = st.sidebar.multiselect(
            "Источник:", sources, default=sources
        )

        filtered_df = df_vacancies[
            (df_vacancies["source"].isin(selected_sources))
            & (
                df_vacancies["title"]
                .str.lower()
                .str.contains(search_query.lower())
            )
        ]

        c1, c2, c3 = st.columns(3)
        c1.metric("Найдено вакансий", len(filtered_df))
        avg_sal = filtered_df["salary_usd"].dropna().mean()
        c2.metric(
            "Средняя ЗП (USD)",
            f"${avg_sal:.0f}" if pd.notna(avg_sal) else "N/A",
        )
        c3.metric("Всего откликов", len(df_apps))

        st.subheader("Список вакансий")
        st.dataframe(
            filtered_df[
                ["id", "title", "company", "location", "salary_usd", "source", "link"]
            ],
            use_container_width=True,
        )

        st.divider()
        st.subheader("➕ Отметить отклик")
        with st.form("add_app_form"):
            selected_vac_id = st.selectbox(
                "Выберите вакансию:",
                filtered_df["id"].tolist(),
                format_func=lambda x: f"#{x} - {filtered_df[filtered_df['id'] == x]['title'].values[0]} ({filtered_df[filtered_df['id'] == x]['company'].values[0]})",
            )
            status = st.selectbox(
                "Статус:",
                [
                    "Отклик отправлен",
                    "Собеседование",
                    "Тестовое задание",
                    "Оффер",
                    "Отказ",
                ],
            )
            notes = st.text_area("Заметки:")
            submit = st.form_submit_button("Сохранить отклик")

            if submit:
                vac_row = filtered_df[filtered_df["id"] == selected_vac_id].iloc[0]
                add_application(
                    selected_vac_id,
                    vac_row["company"],
                    vac_row["title"],
                    status,
                    notes,
                )
                st.success("Отклик сохранен!")
                st.rerun()

with tab3:
    st.subheader("📊 Аналитика вакансий")
    if not df_vacancies.empty:
        col_left, col_right = st.columns(2)

        with col_left:
            st.write("**Количество вакансий по источникам**")
            source_counts = df_vacancies["source"].value_counts()
            st.bar_chart(source_counts)

        with col_right:
            st.write("**Распределение указанных зарплат (USD)**")
            salaries = df_vacancies["salary_usd"].dropna()
            if not salaries.empty:
                st.line_chart(salaries)
            else:
                st.info("В базе пока мало данных с явным указанием ЗП.")