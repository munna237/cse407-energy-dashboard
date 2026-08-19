import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="GPU vs CPU Energy Dashboard", layout="wide", page_icon="⚡")

st.title("⚡ GPU vs CPU Energy Profiling Dashboard")
st.caption("CSE407 Green Computing — comparative energy profile of everyday AI workloads")

# ---------------------------------------------------------------------------
# Methodology panel — always visible, not filter-dependent
# ---------------------------------------------------------------------------
import json as _json

methodology_upload = st.sidebar.file_uploader("Upload methodology.json (optional)", type="json")
methodology = None
default_methodology_path = Path(__file__).parent / "data" / "methodology.json"
if methodology_upload is not None:
    methodology = _json.load(methodology_upload)
elif default_methodology_path.exists():
    methodology = _json.load(open(default_methodology_path))

with st.container(border=True):
    st.markdown("**📋 Methodology — dataset and model per task**")
    if methodology:
        m_cols = st.columns(len(methodology))
        for col, (task_name, meta) in zip(m_cols, methodology.items()):
            with col:
                st.markdown(f"**{task_name.replace('_', ' ').title()}**")
                st.markdown(f"Dataset: {meta.get('dataset', '—')}")
                st.markdown(f"Model: {meta.get('model', '—')}")
                st.markdown(f"Real samples available: {meta.get('n_real_samples', '—')}")
    else:
        st.markdown(
            "_Upload `methodology.json` (produced by the v3 notebook's dataset-loading cell) "
            "in the sidebar to display the exact dataset and model used for each task here._"
        )

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload results_summary.csv", type="csv")
default_path = Path(__file__).parent / "data" / "results_summary.csv"

if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.sidebar.success(f"Loaded {len(df)} rows from your upload")
elif default_path.exists():
    df = pd.read_csv(default_path)
    st.sidebar.info(f"Showing bundled dataset ({len(df)} rows). Upload a newer CSV to override it.")
else:
    st.warning("No data available yet. Upload a results_summary.csv from the notebook to get started.")
    st.stop()

required_cols = {"task", "device_type", "duration_s", "units_processed", "energy_kWh_codecarbon"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"This CSV is missing expected columns: {missing}. Make sure it's from the v2 (large-scale) notebook.")
    st.stop()

electricity_rate = st.sidebar.number_input(
    "Electricity rate (currency/kWh)", value=8.0, step=0.5,
    help="Replace with your actual DESCO/BPDB tariff before citing cost figures in your report.",
)
df["cost_estimate_live"] = df["energy_kWh_codecarbon"] * electricity_rate
df["throughput_units_per_s"] = df["units_processed"] / df["duration_s"]

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")
tasks = st.sidebar.multiselect("Tasks", sorted(df["task"].unique()), default=sorted(df["task"].unique()))
devices = st.sidebar.multiselect("Devices", sorted(df["device_type"].unique()), default=sorted(df["device_type"].unique()))
filtered = df[df["task"].isin(tasks) & df["device_type"].isin(devices)]

if filtered.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# CPU measurement caveat — shown automatically whenever CPU data is in view
# ---------------------------------------------------------------------------
if "cpu" in devices and (filtered["device_type"] == "cpu").any():
    with st.container(border=True):
        st.markdown(
            "⚠️ **CPU energy figures are not direct measurements.** This data was collected on "
            "Google Colab, where Intel RAPL is blocked and CodeCarbon could not match the reported "
            "CPU (`Intel(R) Xeon(R) CPU @ 2.20GHz` — a generic virtualized name) to any known TDP, "
            "so it fell back to a **generic constant**. This was confirmed empirically: the implied "
            "wattage is ~6.3 W ± 0.2 W across every CPU task regardless of workload intensity — it "
            "does not respond to actual computation. **Duration and throughput comparisons remain "
            "valid** (real wall-clock measurements); treat CPU energy and cost figures as illustrative "
            "only, not as measured results."
        )

# ---------------------------------------------------------------------------
# Top-line metrics
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total runs", len(filtered))
c2.metric("Tasks", filtered["task"].nunique())
c3.metric("Devices", filtered["device_type"].nunique())
c4.metric("Total energy logged (kWh)", f"{filtered['energy_kWh_codecarbon'].sum():.5f}")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
st.subheader("Throughput — units processed per second")
tp = filtered.groupby(["task", "device_type"])["throughput_units_per_s"].mean().reset_index()
st.plotly_chart(px.bar(tp, x="task", y="throughput_units_per_s", color="device_type",
                        barmode="group", labels={"throughput_units_per_s": "units/sec"}),
                 use_container_width=True)

st.subheader("Average run duration (seconds)")
dur = filtered.groupby(["task", "device_type"])["duration_s"].mean().reset_index()
st.plotly_chart(px.bar(dur, x="task", y="duration_s", color="device_type", barmode="group"),
                 use_container_width=True)

st.subheader("Energy per unit (kWh) — GPU measured (NVML), CPU estimated (see caveat above)")
if "energy_per_unit_kWh" in filtered.columns:
    epu = filtered.groupby(["task", "device_type"])["energy_per_unit_kWh"].mean().reset_index()
    st.plotly_chart(px.bar(epu, x="task", y="energy_per_unit_kWh", color="device_type",
                            barmode="group", log_y=True),
                     use_container_width=True)
else:
    st.info("This CSV doesn't have an `energy_per_unit_kWh` column (looks like v1 data).")

gpu_df = filtered[filtered["device_type"] == "gpu"]
if not gpu_df.empty and "avg_gpu_watts" in gpu_df.columns:
    st.subheader("GPU average power draw (watts) — real NVML measurement")
    watts = gpu_df.groupby("task")["avg_gpu_watts"].mean().reset_index()
    st.plotly_chart(px.bar(watts, x="task", y="avg_gpu_watts"), use_container_width=True)

st.subheader("Projected cost per 1000 runs")
cost_tbl = filtered.groupby(["task", "device_type"])["cost_estimate_live"].mean().reset_index()
cost_tbl["cost_per_1000_runs"] = cost_tbl["cost_estimate_live"] * 1000
st.dataframe(cost_tbl, use_container_width=True)

with st.expander("Raw results table"):
    st.dataframe(filtered, use_container_width=True)

# ---------------------------------------------------------------------------
# Raw power/utilization curves — GPU (3 tasks), CPU (3 tasks), and combined
# ---------------------------------------------------------------------------
import re as _re

st.sidebar.header("Raw power curves")
st.sidebar.caption("Six bundled example curves (one per task/device) load automatically below. "
                    "Upload your own raw_logs/*_power.csv files here to add or override any of them.")
uploaded_curves = st.sidebar.file_uploader(
    "Upload raw_logs/*_power.csv file(s)", type="csv", accept_multiple_files=True, key="raw_curves"
)

_CURVE_NAME_RE = _re.compile(r"(gpu|cpu)_(image_processing|text_generation|chatbot)")

def _load_curve_bundle():
    curves = {}
    bundled_dir = Path(__file__).parent / "data" / "power_curves"
    if bundled_dir.exists():
        for f in sorted(bundled_dir.glob("*.csv")):
            m = _CURVE_NAME_RE.match(f.stem)
            if m:
                curves[m.groups()] = pd.read_csv(f)
    if uploaded_curves:
        for uf in uploaded_curves:
            m = _CURVE_NAME_RE.match(Path(uf.name).stem)
            if m:
                curves[m.groups()] = pd.read_csv(uf)  # uploads override bundled defaults with the same name
    return curves

curve_bundle = _load_curve_bundle()

st.subheader("Raw power / utilization curves")
if curve_bundle:
    parts = []
    for (device, task), cdf in curve_bundle.items():
        cdf = cdf.copy()
        cdf["device_type"] = device
        cdf["task"] = task.replace("_", " ").title()
        parts.append(cdf)
    all_curves = pd.concat(parts, ignore_index=True)

    gpu_curves = all_curves[all_curves["device_type"] == "gpu"]
    cpu_curves = all_curves[all_curves["device_type"] == "cpu"]

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**GPU — all three tasks (watts, NVML measured)**")
        if not gpu_curves.empty:
            fig_gpu = px.line(gpu_curves, x="t_s", y="value", color="task",
                               labels={"t_s": "seconds into run", "value": "watts"})
            st.plotly_chart(fig_gpu, use_container_width=True)
        else:
            st.caption("No GPU curves loaded.")
    with col_b:
        st.markdown("**CPU — all three tasks (% utilization proxy — see caveat above)**")
        if not cpu_curves.empty:
            fig_cpu = px.line(cpu_curves, x="t_s", y="value", color="task",
                               labels={"t_s": "seconds into run", "value": "% utilization"})
            st.plotly_chart(fig_cpu, use_container_width=True)
        else:
            st.caption("No CPU curves loaded.")

    st.markdown("**Overall — GPU (watts) and CPU (% utilization) together, all six task/device curves**")
    st.caption("GPU and CPU rows use independent y-axis scales since they're different units (watts vs. % utilization) — see the two charts above for each on its own scale.")
    all_curves["device_label"] = all_curves["device_type"].str.upper()
    fig_overall = px.line(
        all_curves, x="t_s", y="value", color="task", facet_row="device_label",
        labels={"t_s": "seconds into run", "value": "watts or % util"},
        height=550,
    )
    fig_overall.update_yaxes(matches=None)
    st.plotly_chart(fig_overall, use_container_width=True)
else:
    st.info("No power curves available. Upload raw_logs/*_power.csv files in the sidebar to see them here.")

st.divider()
st.caption(
    "Built for CSE407 Green Computing — GPU vs CPU energy profiling of everyday AI workloads "
    "(image processing, text generation, chatbot) on Google Colab."
)
