import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("Дашборд по зарплатам и грейдам")

# ======================
# Загрузка данных
# ======================
url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRVFMWoztqX5lhPukYYAQJXQscRA8WFpHXvPSQQUCghrrG_xnNL06BEaZYGQ1Qb0C_17wayXTwVBvZL/pub?output=tsv"
df = pd.read_csv(url, sep="\t")
df.columns = df.columns.str.strip()

# ======================
# Обработка NaN и "Не указан"
# ======================
numeric_cols = ["Премия (сумма)", "Длительность рабочего дня", "Опыт (в сфере)", "Опыт (в компании)"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = df[col].replace("Не указан", 0)
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ======================
# Боковая панель с фильтрами
# ======================
st.sidebar.header("Фильтры")

# Мультиселект только по базовым вариантам
def filter_multiselect(label, column):
    options_all = df[column].dropna().unique()
    base_options = sorted(set(
        opt.strip()
        for o in options_all
        for opt in str(o).split(',')
        if pd.notna(opt)
    ))

    col1, col2 = st.sidebar.columns([4,1])
    with col1:
        selected = st.multiselect(label, base_options, default=[], key=label)  # по умолчанию сброшен
    with col2:
        if st.button("Все", key=f"{label}_all"):
            selected = base_options
    return selected, base_options

# Фильтры
sphere_selected, sphere_options = filter_multiselect("Сфера", "Сфера")
company_selected, company_options = filter_multiselect("Название компании", "Название компании")
position_selected, position_options = filter_multiselect("Должность", "Должность")
grade_selected, grade_options = filter_multiselect("Грейд", "Грейд")
bonus_freq_selected, bonus_freq_options = filter_multiselect("Премия (частотность)", "Премия (частотность)")
work_format_selected, work_format_options = filter_multiselect("Формат работы", "Формат работы")
where_work_selected, where_work_options = filter_multiselect("Откуда можно работать", "Откуда можно работать")

# Слайдеры с кнопками "Сбросить"
def filter_slider(label, column):
    min_default = float(df[column].min())
    max_default = float(df[column].max())
    col1, col2 = st.sidebar.columns([4,1])
    with col1:
        selected_min, selected_max = st.slider(
            label,
            min_default,
            max_default,
            (min_default, max_default),
            key=label
        )
    with col2:
        if st.button("Сброс", key=f"{label}_reset"):
            selected_min, selected_max = min_default, max_default
    return selected_min, selected_max

salary_min, salary_max = filter_slider("Зарплата (в руб)", "Зарплата (в руб)")
bonus_min, bonus_max = filter_slider("Премия (сумма)", "Премия (сумма)")
exp_sphere_min, exp_sphere_max = filter_slider("Опыт (в сфере)", "Опыт (в сфере)")
exp_company_min, exp_company_max = filter_slider("Опыт (в компании)", "Опыт (в компании)")
duration_min, duration_max = filter_slider("Длительность рабочего дня", "Длительность рабочего дня")

# Радио по дате
date_filter = st.sidebar.radio("Дата публикации", ["Все", "За последние 30 дней", "За последние 6 месяцев", "За последний год"])

# ======================
# Применение фильтров
# ======================
filtered_df = df[
    (df["Сфера"].apply(lambda x: any(opt in str(x) for opt in sphere_selected)) if sphere_selected else True) &
    (df["Название компании"].apply(lambda x: any(opt in str(x) for opt in company_selected)) if company_selected else True) &
    (df["Должность"].apply(lambda x: any(opt in str(x) for opt in position_selected)) if position_selected else True) &
    (df["Грейд"].isin(grade_selected) if grade_selected else True) &
    (df["Премия (частотность)"].apply(lambda x: any(opt in str(x) for opt in bonus_freq_selected)) if bonus_freq_selected else True) &
    (df["Формат работы"].apply(lambda x: any(opt in str(x) for opt in work_format_selected)) if work_format_selected else True) &
    (df["Откуда можно работать"].apply(lambda x: any(opt in str(x) for opt in where_work_selected)) if where_work_selected else True) &
    df["Зарплата (в руб)"].between(salary_min, salary_max) &
    df["Премия (сумма)"].between(bonus_min, bonus_max) &
    df["Опыт (в сфере)"].between(exp_sphere_min, exp_sphere_max) &
    df["Опыт (в компании)"].between(exp_company_min, exp_company_max) &
    df["Длительность рабочего дня"].between(duration_min, duration_max)
]

if date_filter != "Все":
    days = {"За последние 30 дней": 30, "За последние 6 месяцев": 183, "За последний год": 365}[date_filter]
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_df["Дата публикации"] = pd.to_datetime(filtered_df["Дата публикации"], errors="coerce")
    filtered_df = filtered_df[filtered_df["Дата публикации"] >= cutoff_date]

# ======================
# Визуализация: зарплаты по грейдам (линии от min до max + медиана)
# ======================
st.header("Уровень зарплат по грейдам")

grade_order = ["Chief", "Lead", "Senior", "Middle+", "Middle"]

grade_salary = filtered_df.groupby("Грейд")["Зарплата (в руб)"].agg(["min", "median", "max"]).reset_index()
grade_salary["Грейд"] = pd.Categorical(grade_salary["Грейд"], categories=grade_order, ordered=True)
grade_salary = grade_salary.sort_values("Грейд", ascending=True)

fig = go.Figure()

for _, row in grade_salary.iterrows():
    fig.add_trace(go.Scatter(
        x=[row["min"], row["max"]],
        y=[row["Грейд"], row["Грейд"]],
        mode="lines",
        line=dict(color="lightgrey", width=6),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=[row["median"]],
        y=[row["Грейд"]],
        mode="markers",
        marker=dict(color="white", size=10),
        name="Медиана" if _ == 0 else None,
        showlegend=(_ == 0)
    ))

fig.update_layout(
    xaxis_title="Зарплата (в руб)",
    yaxis_title="Грейд",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    height=400 + len(grade_salary)*20
)

fig.update_xaxes(showgrid=True, gridcolor='grey', zerolinecolor='grey')
fig.update_yaxes(showgrid=False, categoryorder="array", categoryarray=grade_order[::-1])

st.plotly_chart(fig, use_container_width=True)

# ======================
# Визуализация: зарплаты по компаниям и премиям (слева и справа)
# ======================
st.header("Уровень зарплат и премий по компаниям")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Зарплаты")
    company_salary = filtered_df.groupby("Название компании")["Зарплата (в руб)"].agg(["min", "median", "max"]).reset_index()
    company_salary = company_salary.sort_values("median", ascending=True)

    fig_comp = go.Figure()
    for _, row in company_salary.iterrows():
        if row["min"] == row["max"]:
            # только точка, если одно значение
            fig_comp.add_trace(go.Scatter(
                x=[row["median"]],
                y=[row["Название компании"]],
                mode="markers",
                marker=dict(color="white", size=10),
                showlegend=False
            ))
        else:
            # линия от min до max + медиана
            fig_comp.add_trace(go.Scatter(
                x=[row["min"], row["max"]],
                y=[row["Название компании"], row["Название компании"]],
                mode="lines",
                line=dict(color="lightgrey", width=6),
                showlegend=False
            ))
            fig_comp.add_trace(go.Scatter(
                x=[row["median"]],
                y=[row["Название компании"]],
                mode="markers",
                marker=dict(color="white", size=10),
                showlegend=False
            ))

    fig_comp.update_layout(
        xaxis_title="Зарплата (в руб)",
        yaxis_title="Компания",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=400 + len(company_salary)*20
    )
    fig_comp.update_xaxes(showgrid=True, gridcolor='grey', zerolinecolor='grey')
    fig_comp.update_yaxes(showgrid=False)
    st.plotly_chart(fig_comp, use_container_width=True)

with col2:
    st.subheader("Премии (суммарно)")
    bonus_df = filtered_df[filtered_df["Премия (сумма)"] > 0]
    company_bonus = bonus_df.groupby("Название компании")["Премия (сумма)"].agg(["min", "median", "max"]).reset_index()
    company_bonus = company_bonus.sort_values("median", ascending=True)

    fig_bonus = go.Figure()
    for _, row in company_bonus.iterrows():
        if row["min"] == row["max"]:
            fig_bonus.add_trace(go.Scatter(
                x=[row["median"]],
                y=[row["Название компании"]],
                mode="markers",
                marker=dict(color="white", size=10),
                showlegend=False
            ))
        else:
            fig_bonus.add_trace(go.Scatter(
                x=[row["min"], row["max"]],
                y=[row["Название компании"], row["Название компании"]],
                mode="lines",
                line=dict(color="lightgrey", width=6),
                showlegend=False
            ))
            fig_bonus.add_trace(go.Scatter(
                x=[row["median"]],
                y=[row["Название компании"]],
                mode="markers",
                marker=dict(color="white", size=10),
                showlegend=False
            ))

    fig_bonus.update_layout(
        xaxis_title="Премия (сумма)",
        yaxis_title="Компания",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=400 + len(company_bonus)*20
    )
    fig_bonus.update_xaxes(showgrid=True, gridcolor='grey', zerolinecolor='grey')
    fig_bonus.update_yaxes(showgrid=False)
    st.plotly_chart(fig_bonus, use_container_width=True)

# ======================
# Визуализация: зарплаты по когортам опыта в сфере и по сферам (слева и справа)
# ======================
st.header("Уровень зарплат по стажу и по сферам")
col3, col4 = st.columns(2)

with col3:
    st.subheader("По стажу / в годах")

    def cohort(years):
        if years <= 3:
            return "0-3 года"
        elif 4 <= years <= 5:
            return "4-5 лет"
        elif 6 <= years <= 10:
            return "6-10 лет"
        else:
            return "11 лет и более"

    filtered_df["Когорта опыта"] = filtered_df["Опыт (в сфере)"].apply(cohort)
    cohort_salary = filtered_df.groupby("Когорта опыта")["Зарплата (в руб)"].agg(["min", "median", "max"]).reset_index()
    order_cohort = ["0-3 года", "4-5 лет", "6-10 лет", "11 лет и более"]
    cohort_salary["Когорта опыта"] = pd.Categorical(cohort_salary["Когорта опыта"], categories=order_cohort, ordered=True)
    cohort_salary = cohort_salary.sort_values("Когорта опыта")

    fig_cohort = go.Figure()
    for _, row in cohort_salary.iterrows():
        fig_cohort.add_trace(go.Scatter(
            x=[row["min"], row["max"]],
            y=[row["Когорта опыта"], row["Когорта опыта"]],
            mode="lines",
            line=dict(color="lightgrey", width=6),
            showlegend=False
        ))
        fig_cohort.add_trace(go.Scatter(
            x=[row["median"]],
            y=[row["Когорта опыта"]],
            mode="markers",
            marker=dict(color="white", size=10),
            showlegend=False
        ))

    fig_cohort.update_layout(
        xaxis_title="Зарплата (в руб)",
        yaxis_title="Когорта опыта",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=400 + len(cohort_salary)*20
    )
    fig_cohort.update_xaxes(showgrid=True, gridcolor='grey', zerolinecolor='grey')
    fig_cohort.update_yaxes(showgrid=False)
    st.plotly_chart(fig_cohort, use_container_width=True)

with col4:
    st.subheader("По сферам / -tech")
    sphere_salary = filtered_df.groupby("Сфера")["Зарплата (в руб)"].agg(["min", "median", "max"]).reset_index()
    sphere_salary = sphere_salary.sort_values("median", ascending=True)

    fig_sphere = go.Figure()
    for _, row in sphere_salary.iterrows():
        fig_sphere.add_trace(go.Scatter(
            x=[row["min"], row["max"]],
            y=[row["Сфера"], row["Сфера"]],
            mode="lines",
            line=dict(color="lightgrey", width=6),
            showlegend=False
        ))
        fig_sphere.add_trace(go.Scatter(
            x=[row["median"]],
            y=[row["Сфера"]],
            mode="markers",
            marker=dict(color="white", size=10),
            showlegend=False
        ))

    fig_sphere.update_layout(
        xaxis_title="Зарплата (в руб)",
        yaxis_title="Сфера",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=400 + len(sphere_salary)*20
    )
    fig_sphere.update_xaxes(showgrid=True, gridcolor='grey', zerolinecolor='grey')
    fig_sphere.update_yaxes(showgrid=False)
    st.plotly_chart(fig_sphere, use_container_width=True)

# ======================
# Итоговая таблица
# ======================
st.header("Таблица данных после фильтрации")
st.dataframe(filtered_df, use_container_width=True)
