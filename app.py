"""
Global Health Trends Dashboard
Run using: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Global Health Trends",
    page_icon="🌍",
    layout="wide"
)

DATA_FILE = Path(__file__).parent / "global_health_data.csv"

METRICS = [
    "Confirmed Cases",
    "Confirmed Deaths",
    "Fatality Rate"
]


@st.cache_data
def load_data(file_path):
    """Load the global health CSV dataset."""
    data = pd.read_csv(file_path)

    required = {"Date", "Country", "Confirmed", "Deaths"}

    if not required.issubset(data.columns):
        raise ValueError("Dataset is missing required columns.")

    data["Date"] = pd.to_datetime(data["Date"])
    return data


@st.cache_data
def clean_data(data):
    """Clean the dataset and calculate daily changes and fatality rate."""
    data = data.copy()

    data = data.dropna(
        subset=["Date", "Country", "Confirmed", "Deaths"]
    )

    data["Confirmed"] = pd.to_numeric(
        data["Confirmed"], errors="coerce"
    )

    data["Deaths"] = pd.to_numeric(
        data["Deaths"], errors="coerce"
    )

    data = data.dropna(
        subset=["Confirmed", "Deaths"]
    )

    data["Confirmed"] = data["Confirmed"].clip(lower=0)
    data["Deaths"] = data["Deaths"].clip(lower=0)

    data = (
        data.groupby(
            ["Date", "Country"],
            as_index=False
        )[["Confirmed", "Deaths"]]
        .sum()
        .sort_values(["Country", "Date"])
    )

    data["New Cases"] = (
        data.groupby("Country")["Confirmed"]
        .diff()
        .fillna(data["Confirmed"])
        .clip(lower=0)
    )

    data["New Deaths"] = (
        data.groupby("Country")["Deaths"]
        .diff()
        .fillna(data["Deaths"])
        .clip(lower=0)
    )

    data["Fatality Rate"] = (
        data["Deaths"] /
        data["Confirmed"].replace(0, float("nan")) * 100
    ).fillna(0)

    return data


def get_metric_column(metric):
    """Return the dataset column corresponding to the selected metric."""
    return {
        "Confirmed Cases": "Confirmed",
        "Confirmed Deaths": "Deaths",
        "Fatality Rate": "Fatality Rate"
    }[metric]


def plot_trends(data, metric):
    """Create an interactive line chart of the selected metric."""
    column = get_metric_column(metric)

    fig = px.line(
        data,
        x="Date",
        y=column,
        color="Country",
        title=f"{metric} Over Time",
        template="plotly_white"
    )

    fig.update_layout(
        hovermode="x unified",
        height=450
    )

    return fig


def build_summary(data, metric):
    """Create a descending summary of each country's latest value."""
    column = get_metric_column(metric)

    latest = (
        data.sort_values("Date")
        .groupby("Country")
        .tail(1)[["Country", "Date", column]]
        .sort_values(column, ascending=False)
    )

    return latest.rename(
        columns={
            "Date": "Latest Date",
            column: metric
        }
    )


def build_comparison(data, metric):
    """Calculate the seven-day average of new cases or deaths."""
    daily_column = (
        "New Deaths"
        if metric == "Confirmed Deaths"
        else "New Cases"
    )

    latest_date = data["Date"].max()
    start_date = latest_date - pd.Timedelta(days=6)

    recent = data[
        data["Date"].between(start_date, latest_date)
    ]

    result = (
        recent.groupby("Country", as_index=False)[daily_column]
        .mean()
        .rename(columns={daily_column: "7-Day Daily Average"})
        .sort_values("7-Day Daily Average", ascending=False)
    )

    return result


# ---------------- MAIN APPLICATION ----------------

st.title("🌍 Global Health Trends Dashboard")

st.write(
    "Explore global health indicators and compare "
    "trends across different countries."
)

# Load and clean data
try:
    if not DATA_FILE.exists():
        st.error(
            "Please place global_health_data.csv "
            "in the same folder as app.py."
        )
        st.stop()

    raw_data = load_data(str(DATA_FILE))
    data = clean_data(raw_data)

    if data.empty:
        st.error("No valid data found in the dataset.")
        st.stop()

except Exception as error:
    st.error(f"Error loading data: {error}")
    st.stop()


# Sidebar controls
st.sidebar.header("Dashboard Controls")

countries = sorted(data["Country"].unique())

selected_countries = st.sidebar.multiselect(
    "Select 1–5 Countries",
    countries,
    default=countries[:min(3, len(countries))],
    max_selections=5
)

metric = st.sidebar.radio(
    "Select Metric",
    METRICS
)

if not selected_countries:
    st.warning("Please select at least one country.")
    st.stop()


# Filter countries
filtered_data = data[
    data["Country"].isin(selected_countries)
].copy()


# Date range selector
st.subheader("📈 Trend Visualization")

minimum_date = filtered_data["Date"].min().date()
maximum_date = filtered_data["Date"].max().date()

date_range = st.slider(
    "Select Date Range",
    min_value=minimum_date,
    max_value=maximum_date,
    value=(minimum_date, maximum_date)
)

start_date = pd.Timestamp(date_range[0])
end_date = pd.Timestamp(date_range[1])

trend_data = filtered_data[
    filtered_data["Date"].between(start_date, end_date)
]

if trend_data.empty:
    st.warning("No data available for this date range.")
else:
    st.plotly_chart(
        plot_trends(trend_data, metric),
        use_container_width=True
    )


# Summary table
st.subheader("📋 Country Summary")

summary = build_summary(filtered_data, metric)

if metric == "Fatality Rate":
    st.dataframe(
        summary.style.format({metric: "{:.2f}%"}),
        use_container_width=True,
        hide_index=True
    )
else:
    st.dataframe(
        summary.style.format({metric: "{:,.0f}"}),
        use_container_width=True,
        hide_index=True
    )


# Comparative analysis
st.subheader("📊 Comparative Analysis")

comparison = build_comparison(filtered_data, metric)

fig = px.bar(
    comparison,
    x="Country",
    y="7-Day Daily Average",
    color="Country",
    title="Average Daily New Cases/Deaths (Last 7 Days)",
    template="plotly_white"
)

fig.update_layout(
    showlegend=False,
    height=400
)

st.plotly_chart(
    fig,
    use_container_width=True
)


st.caption(
    "Global Health Trends Dashboard | "
    "Data source: Supplied global health dataset"
)
