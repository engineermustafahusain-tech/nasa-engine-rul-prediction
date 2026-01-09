import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Predictive Maintenance Dashboard",
    layout="wide"
)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
@st.cache_data
def load_data():
    base_dir = os.path.dirname(__file__)
    return pd.read_csv(os.path.join(base_dir, "engine_maintenance_alerts.csv"))

df = load_data()

# --------------------------------------------------
# GLOBAL METRICS
# --------------------------------------------------
TOTAL_TRAINING_ENGINES = 125

avg_engine_life = (
    df.groupby("unit_number")["time_in_cycles"]
    .max()
    .mean()
)

# --------------------------------------------------
# CREATE LIFE PHASE (DATASET DOES NOT HAVE IT)
# --------------------------------------------------
engine_life = (
    df.groupby("unit_number")["time_in_cycles"]
    .max()
    .reset_index()
    .rename(columns={"time_in_cycles": "total_life"})
)

df = df.merge(engine_life, on="unit_number", how="left")

def assign_life_phase(row):
    if row["actual_RUL"] > row["total_life"] * 0.66:
        return "LOW"
    elif row["actual_RUL"] > 0:
        return "MEDIUM"
    else:
        return "END"

df["life_phase"] = df.apply(assign_life_phase, axis=1)

df["health_score"] = (df["actual_RUL"] / df["total_life"]) * 100

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🔧 Controls")

engine_id = st.sidebar.selectbox(
    "Select Engine",
    sorted(df["unit_number"].unique())
)

view_mode = st.sidebar.radio(
    "View Mode",
    ["Selected Engine", "All Engines"]
)

engine_df = df[df["unit_number"] == engine_id]
plot_df = engine_df if view_mode == "Selected Engine" else df

# --------------------------------------------------
# TITLE
# --------------------------------------------------
st.title("🚀 Predictive Maintenance Dashboard")
st.markdown("Lifecycle-aware engine monitoring using **actual RUL behavior**.")

# --------------------------------------------------
# FLEET OVERVIEW
# --------------------------------------------------
st.subheader("📊 Fleet Overview")

f1, f2 = st.columns(2)
f1.metric("🛠 Engines Used for Training", TOTAL_TRAINING_ENGINES)
f2.metric("📈 Average Engine Life (cycles)", f"{avg_engine_life:.0f}")

# --------------------------------------------------
# ENGINE KPI CARDS (CORE LOGIC — UNCHANGED)
# --------------------------------------------------
st.subheader(f"🔍 Engine {engine_id} – Lifecycle Summary")

low_cycle = engine_df[engine_df["life_phase"] == "LOW"]["time_in_cycles"].max()
medium_cycle = engine_df[engine_df["life_phase"] == "MEDIUM"]["time_in_cycles"].max()
total_life = engine_df["time_in_cycles"].max()
health = engine_df.iloc[-1]["health_score"]

c1, c2, c3, c4 = st.columns(4)

c1.metric("🟢 LOW phase ends", int(low_cycle))
c2.metric("🟡 MEDIUM phase ends", int(medium_cycle))
c3.metric("🔴 TOTAL life", int(total_life))
c4.metric("💓 Health Score", f"{health:.1f}%")

# --------------------------------------------------
# MAINTENANCE RECOMMENDATION
# --------------------------------------------------
st.subheader("🛠 Maintenance Recommendation")

if health > 60:
    st.success("Engine is healthy. Continue normal operation.")
elif health > 30:
    st.warning("Engine degrading. Plan maintenance soon.")
else:
    st.error("Critical condition! Immediate maintenance required.")

# --------------------------------------------------
# PHASE TIMELINE BAR
# --------------------------------------------------
st.subheader("⏱ Engine Lifecycle Timeline")

timeline_fig = go.Figure()

timeline_fig.add_trace(go.Bar(
    x=[low_cycle],
    y=["Lifecycle"],
    name="LOW",
    orientation="h",
    marker_color="green"
))

timeline_fig.add_trace(go.Bar(
    x=[medium_cycle - low_cycle],
    y=["Lifecycle"],
    name="MEDIUM",
    orientation="h",
    marker_color="orange"
))

timeline_fig.add_trace(go.Bar(
    x=[total_life - medium_cycle],
    y=["Lifecycle"],
    name="END",
    orientation="h",
    marker_color="red"
))

timeline_fig.update_layout(
    barmode="stack",
    xaxis_title="Time in Cycles",
    showlegend=True
)

st.plotly_chart(timeline_fig, use_container_width=True)

# --------------------------------------------------
# PREDICTED VS ACTUAL RUL
# --------------------------------------------------
st.subheader("📈 Predicted vs Actual RUL")

st.plotly_chart(
    px.scatter(
        plot_df,
        x="actual_RUL",
        y="predicted_RUL",
        color="life_phase",
        title=f"Predicted vs Actual RUL ({view_mode})"
    ),
    use_container_width=True
)

# --------------------------------------------------
# SENSOR ROC WITH PHASE LINES
# --------------------------------------------------
st.subheader("⚙️ Sensor 14 Degradation Trend")

roc_fig = px.line(
    plot_df.sort_values("time_in_cycles"),
    x="time_in_cycles",
    y="sensor_14_roc",
    color="unit_number" if view_mode == "All Engines" else None
)

if view_mode == "Selected Engine":
    roc_fig.add_vline(x=low_cycle, line_dash="dash", line_color="green")
    roc_fig.add_vline(x=medium_cycle, line_dash="dash", line_color="orange")

st.plotly_chart(roc_fig, use_container_width=True)

# --------------------------------------------------
# FLEET DISTRIBUTIONS
# --------------------------------------------------
st.subheader("📊 Fleet-Level Insights")

d1, d2 = st.columns(2)

d1.plotly_chart(
    px.histogram(
        df.groupby("unit_number")["total_life"].max().reset_index(),
        x="total_life",
        title="Engine Life Distribution"
    ),
    use_container_width=True
)

d2.plotly_chart(
    px.bar(
        df["life_phase"].value_counts().reset_index(),
        x="index",
        y="life_phase",
        title="Lifecycle Phase Distribution"
    ),
    use_container_width=True
)

# --------------------------------------------------
# ENGINE TABLE
# --------------------------------------------------
st.subheader("📋 Engine Data")

st.dataframe(
    engine_df[
        [
            "time_in_cycles",
            "actual_RUL",
            "predicted_RUL",
            "life_phase",
            "health_score",
            "sensor_14_roc",
            "sensor_2_roc"
        ]
    ],
    use_container_width=True
)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("---")
st.markdown(
    "**End-to-End Predictive Maintenance Dashboard**  \n"
    "Fleet view + Engine diagnostics + Lifecycle intelligence"
)
