import streamlit as st
import pandas as pd
import altair as alt
from datetime import timedelta, datetime

# Set page config
st.set_page_config(page_title="Environmental Data Dashboard", layout="wide")

# Helper functions
@st.cache_data
def load_data():
    # Baca file CSV dan konversi timestamp UNIX milidetik ke datetime
    data = pd.read_csv("humidity.csv", sep=';')
    data['date'] = pd.to_datetime(data['date'], unit='ms')
    return data

def custom_quarter(date):
    month = date.month
    year = date.year
    if month in [2, 3, 4]:
        return pd.Period(year=year, quarter=1, freq='Q')
    elif month in [5, 6, 7]:
        return pd.Period(year=year, quarter=2, freq='Q')
    elif month in [8, 9, 10]:
        return pd.Period(year=year, quarter=3, freq='Q')
    else:  # month in [11, 12, 1]
        return pd.Period(year=year if month != 1 else year-1, quarter=4, freq='Q')

def aggregate_data(df, freq):
    if freq == 'Q':
        df = df.copy()
        df['CUSTOM_Q'] = df['date'].apply(custom_quarter)
        df_agg = df.groupby('CUSTOM_Q').mean()
        return df_agg
    else:
        return df.resample(freq, on='date').mean()

def get_weekly_data(df):
    return aggregate_data(df, 'W-MON')

def get_monthly_data(df):
    return aggregate_data(df, 'M')

def get_quarterly_data(df):
    return aggregate_data(df, 'Q')

def create_metric_chart(df, column, chart_type, height=150, time_frame='Daily'):
    chart_data = df[[column]].reset_index()
    chart_data.columns = ['date', 'value']

    if time_frame == 'Quarterly':
        chart_data['date'] = chart_data['date'].dt.to_period('Q').astype(str)
    
    y_min = chart_data['value'].min()
    y_max = chart_data['value'].max()

    if chart_type == 'Bar':
        chart = alt.Chart(chart_data).mark_bar().encode(
            x='date:T',
            y=alt.Y('value:Q', scale=alt.Scale(domain=[y_min, y_max])),
            tooltip=['date:T', 'value:Q']
        )
    elif chart_type == 'Area':
        chart = alt.Chart(chart_data).mark_area().encode(
            x='date:T',
            y=alt.Y('value:Q', scale=alt.Scale(domain=[y_min, y_max])),
            tooltip=['date:T', 'value:Q']
        )

    st.altair_chart(chart, use_container_width=True)

def calculate_delta(df, column):
    if len(df) < 2:
        return 0, 0
    current_value = df[column].iloc[-1]
    previous_value = df[column].iloc[-2]
    delta = current_value - previous_value
    delta_percent = (delta / previous_value) * 100 if previous_value != 0 else 0
    return delta, delta_percent

# Load data
df = load_data()

# Set up input widgets
with st.sidebar:
    st.title("EDA Dashboard")
    st.header("⚙️ Settings")
    
    max_date = df['date'].max().date()
    min_date = df['date'].min().date()
    default_start_date = max(min_date, max_date - timedelta(days=365))  # Ensure within range
    default_end_date = max_date
    
    start_date = st.date_input("Start date", default_start_date, min_value=min_date, max_value=max_date)
    end_date = st.date_input("End date", default_end_date, min_value=min_date, max_value=max_date)
    
    time_frame = st.selectbox("Select time frame", ("Daily", "Weekly", "Monthly", "Quarterly"))
    chart_selection = st.selectbox("Select a chart type", ("Bar", "Area"))

# Prepare data based on selected time frame
if time_frame == 'Daily':
    df_display = df.set_index('date')
elif time_frame == 'Weekly':
    df_display = get_weekly_data(df)
elif time_frame == 'Monthly':
    df_display = get_monthly_data(df)
elif time_frame == 'Quarterly':
    df_display = get_quarterly_data(df)

# Display Key Metrics
st.subheader("All-Time Statistics")

metrics = [
    ("Average Temperature (°C)", "temperature"),
    ("Average Humidity (%)", "humidity"),
    ("Average Heat Index", "heat_index"),
    ("Average pH Level", "pH")
]

cols = st.columns(4)
for col, (title, column) in zip(cols, metrics):
    avg_value = df[column].mean()
    delta, delta_percent = calculate_delta(df_display, column)
    with col:
        st.metric(title, f"{avg_value:.2f}", f"{delta:+.2f} ({delta_percent:+.2f}%)")
        create_metric_chart(df_display, column, chart_selection, time_frame=time_frame)

st.subheader("Selected Duration")

mask = (df_display.index >= pd.Timestamp(start_date)) & (df_display.index <= pd.Timestamp(end_date))
df_filtered = df_display.loc[mask]

cols = st.columns(4)
for col, (title, column) in zip(cols, metrics):
    avg_value = df_filtered[column].mean()
    delta, delta_percent = calculate_delta(df_filtered, column)
    with col:
        st.metric(title, f"{avg_value:.2f}", f"{delta:+.2f} ({delta_percent:+.2f}%)")
        create_metric_chart(df_filtered, column, chart_selection, time_frame=time_frame)

# DataFrame display
with st.expander('See DataFrame (Selected time frame)'):
    st.dataframe(df_filtered)
