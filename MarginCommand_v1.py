# MarginCommand - Proprietary Software
# Copyright (c) 2026 Daniel Robinson
# All rights reserved.
# Unauthorized use, copying, modification, or distribution is prohibited.

import math
from datetime import datetime, time, timedelta

import numpy as np
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="MarginCommand", layout="wide")


# =========================
# CONFIG
# =========================

DAYPART_WINDOWS = {
    "Monday": {
        "Dinner": {"open": time(15, 0), "close": time(21, 0)},
    },
    "Tuesday": {
        "Dinner": {"open": time(15, 0), "close": time(21, 0)},
    },
    "Wednesday": {
        "Dinner": {"open": time(15, 0), "close": time(21, 0)},
    },
    "Thursday": {
        "Dinner": {"open": time(15, 0), "close": time(21, 0)},
    },
    "Friday": {
        "Dinner": {"open": time(15, 0), "close": time(22, 0)},
    },
    "Saturday": {
        "Lunch": {"open": time(12, 0), "close": time(15, 0)},
        "Dinner": {"open": time(15, 0), "close": time(22, 0)},
    },
    "Sunday": {
        "Lunch": {"open": time(12, 0), "close": time(15, 0)},
        "Dinner": {"open": time(15, 0), "close": time(21, 0)},
    },
}

SERVICE_FLOOR_BY_PHASE = {
    "OPEN": {"line_cooks": 4, "dishwashers": 1},
    "BUILD": {"line_cooks": 5, "dishwashers": 1},
    "PEAK": {"line_cooks": 5, "dishwashers": 2},
    "DECLINE": {"line_cooks": 4, "dishwashers": 2},
    "CLOSEOUT": {"line_cooks": 3, "dishwashers": 2},
}

DEFAULT_TARGET_BOH_PCT = 11.0
DEFAULT_TARGET_TOTAL_PCT = 16.0

BENCHMARK_SALES = {
    "Lunch": 7000,
    "Dinner": {
        "Monday": 9000,
        "Tuesday": 10000,
        "Wednesday": 11000,
        "Thursday": 13000,
        "Friday": 16000,
        "Saturday": 18000,
        "Sunday": 14000,
        "default": 12000,
    },
}


# ============================================================
# REAL AMORE SERVICE CURVES — built from R365 hourly sales data
# 2/18/2026 - 4/7/2026 | 8 buckets = 3PM 4PM 5PM 6PM 7PM 8PM 9PM 10PM
# Mon/Thu smoothed to remove large-party spike distortion
# ============================================================
CURVE_LIBRARY = {
    "Lunch": np.array([0.18, 0.42, 0.28, 0.12], dtype=float),
    "Dinner": {
        "Monday":    np.array([0.05, 0.09, 0.18, 0.24, 0.22, 0.16, 0.05, 0.01], dtype=float),
        "Tuesday":   np.array([0.08, 0.10, 0.20, 0.24, 0.20, 0.12, 0.05, 0.01], dtype=float),
        "Wednesday": np.array([0.07, 0.12, 0.26, 0.27, 0.19, 0.07, 0.02, 0.00], dtype=float),
        "Thursday":  np.array([0.06, 0.09, 0.18, 0.24, 0.22, 0.15, 0.05, 0.01], dtype=float),
        "Friday":    np.array([0.05, 0.11, 0.14, 0.14, 0.16, 0.18, 0.20, 0.02], dtype=float),
        "Saturday":  np.array([0.06, 0.14, 0.17, 0.20, 0.20, 0.15, 0.06, 0.02], dtype=float),
        "Sunday":    np.array([0.11, 0.16, 0.21, 0.21, 0.22, 0.06, 0.02, 0.01], dtype=float),
        "default":   np.array([0.06, 0.11, 0.19, 0.23, 0.21, 0.13, 0.06, 0.01], dtype=float),
    },
}

HH_NOTES = {
    "Monday": "Early week can look soft at first. Do not force a cut off one dead pocket.",
    "Tuesday": "Pace can build late. Watch trend, not one quiet stretch.",
    "Wednesday": "Midweek can feel soft before dinner settles in.",
    "Thursday": "Late reservations matter more than early noise.",
    "Friday": "Peak window is powerful. Decline reads matter more after the turn.",
    "Saturday": "Weekend demand can hold stronger later into the night.",
    "Sunday": "Sunday can look soft on paper, then tighten fast on the finish.",
}

SCENARIOS = {
    "Custom": None,
    "Saturday Peak Strong": {
        "day_name": "Saturday",
        "shift": "Dinner",
        "hour12": 6,
        "minute": 15,
        "am_pm": "PM",
        "sales_so_far": 14200.0,
        "average_check": 47.0,
        "covers_so_far": 210.0,
        "total_reservations_today": 330.0,
        "boh_labor_so_far": 1560.0,
        "prep_labor": 430.0,
        "foh_labor_so_far": 950.0,
        "line_cooks": 6,
        "dishwashers": 2,
        "dining_room_feel": 4,
    },
    "Saturday Peak Soft": {
        "day_name": "Saturday",
        "shift": "Dinner",
        "hour12": 6,
        "minute": 15,
        "am_pm": "PM",
        "sales_so_far": 11600.0,
        "average_check": 44.0,
        "covers_so_far": 180.0,
        "total_reservations_today": 330.0,
        "boh_labor_so_far": 1580.0,
        "prep_labor": 430.0,
        "foh_labor_so_far": 900.0,
        "line_cooks": 6,
        "dishwashers": 2,
        "dining_room_feel": 2,
    },
    "Friday Decline Tight": {
        "day_name": "Friday",
        "shift": "Dinner",
        "hour12": 8,
        "minute": 30,
        "am_pm": "PM",
        "sales_so_far": 17650.0,
        "average_check": 49.0,
        "covers_so_far": 255.0,
        "total_reservations_today": 320.0,
        "boh_labor_so_far": 1985.0,
        "prep_labor": 515.0,
        "foh_labor_so_far": 1180.0,
        "line_cooks": 6,
        "dishwashers": 2,
        "dining_room_feel": 3,
    },
    "Sunday Closeout": {
        "day_name": "Sunday",
        "shift": "Dinner",
        "hour12": 9,
        "minute": 20,
        "am_pm": "PM",
        "sales_so_far": 18820.0,
        "average_check": 46.0,
        "covers_so_far": 272.0,
        "total_reservations_today": 285.0,
        "boh_labor_so_far": 2120.0,
        "prep_labor": 480.0,
        "foh_labor_so_far": 1035.0,
        "line_cooks": 5,
        "dishwashers": 2,
        "dining_room_feel": 2,
    },
    "Early Shift Small Sample": {
        "day_name": "Wednesday",
        "shift": "Dinner",
        "hour12": 4,
        "minute": 5,
        "am_pm": "PM",
        "sales_so_far": 610.0,
        "average_check": 42.0,
        "covers_so_far": 11.0,
        "total_reservations_today": 155.0,
        "boh_labor_so_far": 540.0,
        "prep_labor": 310.0,
        "foh_labor_so_far": 210.0,
        "line_cooks": 5,
        "dishwashers": 1,
        "dining_room_feel": 3,
    },
}


# =========================
# STYLES
# =========================

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(0,90,170,0.20), transparent 30%),
            linear-gradient(180deg, #020817 0%, #030b1c 100%);
        color: #f8fafc;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1.0rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4, h5, h6, p, div, span, label {
        color: #f8fafc !important;
    }

    .sp-card {
        background: rgba(8, 15, 32, 0.90);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
        margin-bottom: 12px;
    }

    .hero {
        border-radius: 20px;
        padding: 20px 22px;
        margin-bottom: 12px;
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 10px 24px rgba(0,0,0,0.20);
    }

    .hero-green { background: linear-gradient(135deg, #22c55e 0%, #65e64a 100%); color: #04120b !important; }
    .hero-orange { background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); color: white !important; }
    .hero-red { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white !important; }
    .hero-blue { background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%); color: white !important; }

    .hero-title {
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 6px;
        letter-spacing: 0.02em;
    }

    .hero-sub {
        font-size: 0.92rem;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .hero-text {
        font-size: 0.88rem;
        line-height: 1.45;
    }

    .metric-card {
        background: rgba(9, 18, 38, 0.90);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 14px 16px;
        min-height: 126px;
        margin-bottom: 10px;
    }

    .metric-label {
        font-size: 0.70rem;
        font-weight: 800;
        text-transform: uppercase;
        color: #cbd5e1 !important;
        letter-spacing: 0.04em;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 6px;
        line-height: 1.1;
    }

    .metric-copy {
        font-size: 0.82rem;
        color: #cbd5e1 !important;
        line-height: 1.35;
    }

    .plan-box {
        background: rgba(8, 15, 32, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 12px;
    }

    .mini-visual {
        background: rgba(9, 18, 38, 0.90);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }

    .mini-label {
        font-size: 0.74rem;
        font-weight: 800;
        text-transform: uppercase;
        color: #cbd5e1 !important;
        letter-spacing: 0.04em;
        margin-bottom: 10px;
    }

    .bar-wrap {
        width: 100%;
        height: 14px;
        background: rgba(148,163,184,0.18);
        border-radius: 999px;
        overflow: hidden;
        margin-top: 8px;
    }

    .bar-fill-green {
        height: 100%;
        background: linear-gradient(90deg, #22c55e, #84cc16);
        border-radius: 999px;
    }

    .bar-fill-yellow {
        height: 100%;
        background: linear-gradient(90deg, #facc15, #f59e0b);
        border-radius: 999px;
    }

    .bar-fill-red {
        height: 100%;
        background: linear-gradient(90deg, #fb7185, #ef4444);
        border-radius: 999px;
    }

    .blue-box {
        background: rgba(56, 189, 248, 0.14);
        border: 1px solid rgba(56, 189, 248, 0.28);
        border-radius: 14px;
        padding: 14px 16px;
        margin-top: 12px;
        margin-bottom: 12px;
    }

    .blue-title {
        font-weight: 800;
        margin-bottom: 4px;
        color: #bae6fd !important;
        font-size: 0.85rem;
    }

    .blue-copy {
        color: #dbeafe !important;
        font-size: 0.84rem;
        line-height: 1.45;
    }

    .subtle {
        color: #cbd5e1 !important;
        font-size: 0.85rem;
        line-height: 1.4;
    }

    .tight {
        margin-top: 0.15rem;
        margin-bottom: 0.15rem;
    }

    div[data-testid="stExpander"] {
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 14px;
        background: rgba(8, 15, 32, 0.76);
    }

    div[data-testid="stForm"] {
        background: rgba(8, 15, 32, 0.76);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 8px 12px 14px 12px;
    }

    .small-note {
        font-size: 0.76rem;
        color: #94a3b8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# HELPERS
# =========================

def money(value: float) -> str:
    return f"${value:,.0f}" if abs(value) >= 100 else f"${value:,.2f}"


def money_hr(value: float) -> str:
    return f"${value:,.0f}/hr" if abs(value) >= 100 else f"${value:,.2f}/hr"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def combine_today(t: time) -> datetime:
    now = datetime.now()
    return datetime(now.year, now.month, now.day, t.hour, t.minute)


def hours_between(start_t: time, end_t: time) -> float:
    start_dt = combine_today(start_t)
    end_dt = combine_today(end_t)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return (end_dt - start_dt).total_seconds() / 3600


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def current_test_time(hour12: int, minute: int, am_pm: str) -> time:
    hour = hour12 % 12
    if am_pm.upper() == "PM":
        hour += 12
    return time(hour, minute)


def available_shifts_for_day(day_name: str) -> list[str]:
    return list(DAYPART_WINDOWS[day_name].keys())


def get_hours(day_name: str, shift: str) -> tuple[time, time]:
    return DAYPART_WINDOWS[day_name][shift]["open"], DAYPART_WINDOWS[day_name][shift]["close"]


def get_curve_for_shift(shift: str, hours_open: float, day_name: str = "default") -> np.ndarray:
    if shift == "Lunch":
        base = CURVE_LIBRARY["Lunch"]
    else:
        # Use day-specific real Amore curve, fall back to default
        dinner_curves = CURVE_LIBRARY["Dinner"]
        base = dinner_curves.get(day_name, dinner_curves["default"])

    # 15-minute internal buckets for smoother pacing math
    target_len = max(4, int(math.ceil(hours_open * 4)))

    x_old = np.linspace(0, 1, len(base))
    x_new = np.linspace(0, 1, target_len)

    # Interpolate the house curve to finer resolution
    curve = np.interp(x_new, x_old, base)
    curve = np.maximum(curve, 0.001)

    # Summation-style local smoothing on incremental weights
    smoothed = curve.copy()
    for i in range(len(curve)):
        left = curve[i - 1] if i > 0 else curve[i]
        center = curve[i]
        right = curve[i + 1] if i < len(curve) - 1 else curve[i]
        smoothed[i] = (left + 2 * center + right) / 4

    # Re-normalize so the full shift still sums to 1.0
    smoothed = np.maximum(smoothed, 0.001)
    smoothed = smoothed / smoothed.sum()
    return smoothed


def expected_curve_progress(curve: np.ndarray, hours_open: float, hours_open_so_far: float) -> float:
    if hours_open <= 0:
        return 1.0
    if hours_open_so_far <= 0:
        return 0.0
    if hours_open_so_far >= hours_open:
        return 1.0

    bucket_size = hours_open / len(curve)
    progress = 0.0

    for i, weight in enumerate(curve):
        bucket_start = i * bucket_size
        bucket_end = (i + 1) * bucket_size

        if hours_open_so_far >= bucket_end:
            progress += weight
        elif hours_open_so_far > bucket_start:
            partial = (hours_open_so_far - bucket_start) / bucket_size
            progress += weight * partial
            break
        else:
            break

    return clamp(progress, 0.0, 1.0)


def progress_to_phase(progress: float, is_closed: bool) -> str:
    if is_closed:
        return "CLOSEOUT"
    if progress < 0.12:
        return "OPEN"
    if progress < 0.35:
        return "BUILD"
    if progress < 0.62:
        return "PEAK"
    return "DECLINE"


def floor_by_phase(phase: str) -> dict:
    return SERVICE_FLOOR_BY_PHASE.get(phase, SERVICE_FLOOR_BY_PHASE["DECLINE"])


def build_sales_vectors(
    hours_open: float,
    curve: np.ndarray,
    actual_sales_so_far: float,
    projected_final_sales: float,
    elapsed_hours: float,
    benchmark_final_sales: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns four CUMULATIVE sales vectors — one point per bucket boundary.

    - benchmark_cumulative: fixed benchmark line using the same service curve
    - expected_cumulative:  adaptive expected line using projected_final_sales
    - actual_cumulative:    anchored to actual sales at current elapsed time
    - projected_cumulative: continues from current actual point to projected final sales
    """
    bucket_count = len(curve)
    if bucket_count == 0 or hours_open == 0:
        empty = np.zeros(2)
        return empty, empty, empty, empty

    bucket_size_hrs = hours_open / bucket_count

    cum_curve = np.concatenate([[0.0], np.cumsum(curve)])  # length bucket_count+1
    benchmark_cumulative = cum_curve * benchmark_final_sales
    expected_cumulative = cum_curve * projected_final_sales

    completed_buckets = int(clamp(math.floor(elapsed_hours / bucket_size_hrs), 0, bucket_count))
    partial_ratio = clamp(
        (elapsed_hours - completed_buckets * bucket_size_hrs) / bucket_size_hrs
        if bucket_size_hrs > 0 else 0,
        0,
        1,
    )

    cum_curve_at_now = (
        cum_curve[completed_buckets]
        + (cum_curve[min(completed_buckets + 1, bucket_count)] - cum_curve[completed_buckets])
        * partial_ratio
    )
    cum_curve_at_now = max(cum_curve_at_now, 0.001)

    actual_cumulative = np.full(bucket_count + 1, np.nan)
    actual_cumulative[0] = 0.0
    for i in range(1, completed_buckets + 1):
        actual_cumulative[i] = actual_sales_so_far * (cum_curve[i] / cum_curve_at_now)
    if completed_buckets < bucket_count:
        actual_cumulative[completed_buckets] = actual_sales_so_far
    else:
        actual_cumulative[bucket_count] = actual_sales_so_far

    projected_cumulative = np.full(bucket_count + 1, np.nan)
    projected_cumulative[completed_buckets] = actual_sales_so_far
    remaining_sales = max(projected_final_sales - actual_sales_so_far, 0.0)
    remaining_curve_total = cum_curve[bucket_count] - cum_curve[completed_buckets]
    for i in range(completed_buckets + 1, bucket_count + 1):
        frac = (cum_curve[i] - cum_curve[completed_buckets]) / max(remaining_curve_total, 0.001)
        projected_cumulative[i] = actual_sales_so_far + remaining_sales * frac

    return benchmark_cumulative, expected_cumulative, actual_cumulative, projected_cumulative


def build_service_chart(model: dict, open_t: time) -> go.Figure:
    hours_open = model["hours_open"]
    elapsed_hours = model["hours_open_so_far"]

    benchmark_cum = model["benchmark_hourly"]
    expected_cum = model["expected_hourly"]
    actual_cum = model["actual_line"]
    proj_cum = model["projected_hourly"]

    bucket_count = len(expected_cum) - 1
    total_minutes_open = int(round(hours_open * 60))
    bucket_size_minutes = total_minutes_open / bucket_count if bucket_count > 0 else 1.0
    open_minutes = open_t.hour * 60 + open_t.minute

    def fmt_clock(total_minutes: int) -> str:
        h = (total_minutes // 60) % 24
        m = total_minutes % 60
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d}{suffix}" if m else f"{h12}{suffix}"

    # True time-based x-axis in minutes from open
    x_boundary = [i * bucket_size_minutes for i in range(bucket_count + 1)]

    tick_minutes = list(range(0, total_minutes_open + 1, 30))
    if tick_minutes[-1] != total_minutes_open:
        tick_minutes.append(total_minutes_open)
    tickvals = tick_minutes
    ticktext = [fmt_clock(open_minutes + mins) for mins in tick_minutes]

    marker_x = elapsed_hours * 60
    marker_x = clamp(marker_x, 0, total_minutes_open)
    marker_label = fmt_clock(open_minutes + int(round(marker_x)))

    actual_x = []
    actual_y = []
    completed_minutes = int(marker_x // bucket_size_minutes) if bucket_size_minutes > 0 else 0

    for i, val in enumerate(actual_cum):
        if np.isnan(val):
            continue
        x_val = i * bucket_size_minutes
        if x_val <= completed_minutes * bucket_size_minutes:
            actual_x.append(x_val)
            actual_y.append(val)

    actual_sales_now = model["sales_so_far"]
    if not actual_x or actual_x[-1] < marker_x:
        actual_x.append(marker_x)
        actual_y.append(actual_sales_now)

    proj_x = []
    proj_y = []
    for i, val in enumerate(proj_cum):
        if np.isnan(val):
            continue
        proj_x.append(i * bucket_size_minutes)
        proj_y.append(val)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x_boundary,
            y=benchmark_cum,
            mode="lines",
            name="Benchmark",
            line=dict(color="#f59e0b", width=2, dash="dot"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x_boundary,
            y=expected_cum,
            mode="lines",
            name="Dynamic Expected",
            line=dict(color="rgba(255,255,255,0.70)", width=3, dash="dot"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=actual_x,
            y=actual_y,
            mode="lines",
            name="Actual Pace",
            line=dict(color="#67e8f9", width=4),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=proj_x,
            y=proj_y,
            mode="lines",
            name="Projected Pace",
            line=dict(color="#4ade80", width=3, dash="dash"),
        )
    )

    fig.add_vline(
        x=marker_x,
        line_width=2,
        line_dash="dash",
        line_color="rgba(255,255,255,0.8)",
        annotation_text=f"Now ({marker_label})",
        annotation_position="top",
        annotation_font_color="rgba(255,255,255,0.8)",
        annotation_font_size=11,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        height=360,
        margin=dict(l=10, r=10, t=35, b=40),
        xaxis=dict(
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            title=None,
            tickfont=dict(size=12, color="rgba(255,255,255,0.75)"),
            range=[0, total_minutes_open],
        ),
        yaxis=dict(
            title="Cumulative Sales ($)",
            tickformat="$,.0f",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )

    return fig


def build_closeout_chart(model: dict) -> go.Figure:
    closeout_window = max(model["closeout_room_hours"], 1.0)
    x = np.linspace(model["hours_open"], model["hours_open"] + closeout_window, 20)
    locked_sales = np.full_like(x, model["sales_so_far"])
    closeout_burn = (x - model["hours_open"]) * model["boh_burn_per_hour"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=locked_sales,
            mode="lines",
            name="Locked Sales",
            line=dict(color="#67e8f9", width=4),
            yaxis="y",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=closeout_burn,
            mode="lines",
            name="Closeout Burn",
            line=dict(color="#fb923c", width=4),
            fill="tozeroy",
            yaxis="y2",
        )
    )

    fig.add_vline(
        x=model["hours_open"] + model["closeout_elapsed"],
        line_width=2,
        line_dash="dash",
        line_color="rgba(255,255,255,0.8)",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        height=360,
        margin=dict(l=10, r=10, t=35, b=10),
        xaxis_title="Service Hours + Closeout",
        yaxis=dict(title="Sales"),
        yaxis2=dict(title="Labor $", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )

    return fig


# =========================
# MODEL
# =========================

def build_projection_model(
    day_name: str,
    shift: str,
    test_t: time,
    sales_so_far: float,
    average_check: float,
    covers_so_far: float,
    total_reservations_today: float,
    boh_labor_so_far: float,
    prep_labor: float,
    foh_labor_so_far: float,
    line_cooks: int,
    dishwashers: int,
    dining_room_feel: int,
    target_boh_pct: float = DEFAULT_TARGET_BOH_PCT,
    target_total_pct: float = DEFAULT_TARGET_TOTAL_PCT,
) -> dict:
    open_t, close_t = get_hours(day_name, shift)
    open_dt = combine_today(open_t)
    close_dt = combine_today(close_t)
    test_dt = combine_today(test_t)

    if close_dt <= open_dt:
        close_dt += timedelta(days=1)

    if test_dt < open_dt:
        test_dt += timedelta(days=1) if test_dt.hour < open_t.hour else timedelta(0)

    hours_open = hours_between(open_t, close_t)

    is_closed = test_dt >= close_dt
    hours_open_so_far = clamp((test_dt - open_dt).total_seconds() / 3600, 0, hours_open)
    hours_remaining = max(hours_open - hours_open_so_far, 0)
    closeout_elapsed = max((test_dt - close_dt).total_seconds() / 3600, 0) if is_closed else 0
    progress = 1.0 if hours_open <= 0 else clamp(hours_open_so_far / hours_open, 0, 1)

    phase = progress_to_phase(progress, is_closed)
    floor_now = floor_by_phase(phase)

    curve = get_curve_for_shift(shift, hours_open, day_name)
    curve_progress = expected_curve_progress(curve, hours_open, hours_open_so_far)

    if not is_closed:
        pace_projection = sales_so_far / max(curve_progress, 0.05)
        cover_based_projection = max(covers_so_far, 1) * max(average_check, 1)

        reservation_projection = sales_so_far
        if total_reservations_today > 0:
            reservation_projection = total_reservations_today * max(average_check, 1)

        dining_room_adjust = {1: 0.94, 2: 0.98, 3: 1.00, 4: 1.04, 5: 1.08}.get(dining_room_feel, 1.0)

        projected_final_sales = (
            0.58 * pace_projection
            + 0.18 * reservation_projection
            + 0.16 * cover_based_projection
            + 0.08 * max(sales_so_far, 1)
        ) * dining_room_adjust

        minimum_sales_from_current = sales_so_far * 1.03
        minimum_sales_from_hours_left = sales_so_far + (hours_remaining * max(average_check * 3.5, 140))

        projected_final_sales = max(
            projected_final_sales,
            minimum_sales_from_current,
            minimum_sales_from_hours_left,
        )

        projected_final_sales = min(projected_final_sales, max(sales_so_far * 3.0, sales_so_far + 1500))
    else:
        projected_final_sales = sales_so_far

    projected_final_sales = max(projected_final_sales, sales_so_far)
    expected_sales_so_far = projected_final_sales * curve_progress if not is_closed else sales_so_far

    target_boh_dollars = projected_final_sales * (target_boh_pct / 100)
    target_total_labor_dollars = projected_final_sales * (target_total_pct / 100)

    current_boh_pct = 100 * boh_labor_so_far / max(sales_so_far, 1)
    projected_boh_pct = 100 * boh_labor_so_far / max(projected_final_sales, 1)
    projected_total_labor_pct = 100 * (boh_labor_so_far + foh_labor_so_far) / max(projected_final_sales, 1)

    boh_room_left = target_boh_dollars - boh_labor_so_far

    live_boh_burn = max(18 * line_cooks + 16 * dishwashers, 0)
    boh_burn_per_hour = live_boh_burn

    allowed_boh_burn = max(
        0.0,
        boh_room_left / max(hours_remaining if not is_closed else 1.0, 0.25),
    )

    burn_gap = boh_burn_per_hour - allowed_boh_burn
    cost_waiting_15 = max(burn_gap, 0) * 0.25

    remaining_sales_room = max(projected_final_sales - sales_so_far, 0)
    recovery_ratio = remaining_sales_room / max(boh_room_left, 1) if boh_room_left > 0 else 0

    actual_sales_pace = sales_so_far / max(hours_open_so_far if hours_open_so_far > 0 else 0.25, 0.25)
    expected_sales_pace = (
        max(projected_final_sales - sales_so_far, 0) / max(hours_remaining if hours_remaining > 0 else 0.25, 0.25)
        if not is_closed else 0
    )
    pace_difference = actual_sales_pace - expected_sales_pace

    if burn_gap <= 0:
        hours_until_tight = max(hours_remaining if not is_closed else 0, 0)
    else:
        hours_until_tight = max(boh_room_left, 0) / max(burn_gap, 1)

    closeout_floor = SERVICE_FLOOR_BY_PHASE["CLOSEOUT"]
    closeout_window_hours = 2.0
    closeout_room_hours = max(boh_room_left / max(boh_burn_per_hour, 1), 0) if is_closed else hours_until_tight

    in_transition = (
        (phase == "DECLINE")
        and (hours_remaining <= 2.25)
        and (pace_difference >= 0 or actual_sales_pace >= expected_sales_pace * 0.90)
    )

    small_sample_protection = covers_so_far < 15 or sales_so_far < 800
    early_phase_protection = phase in {"OPEN", "BUILD", "PEAK"} and progress <= 0.40

    above_floor_line = max(line_cooks - floor_now["line_cooks"], 0)
    above_floor_dish = max(dishwashers - floor_now["dishwashers"], 0)

    if is_closed:
        if line_cooks > closeout_floor["line_cooks"]:
            suggested_next_cut = "Cut 1 float cook now"
        elif dishwashers > closeout_floor["dishwashers"]:
            suggested_next_cut = "Hold dish. Tighten a cook first"
        else:
            suggested_next_cut = "At floor. Finish clean and get out"
    else:
        if above_floor_line > 0:
            suggested_next_cut = "Cut 1 float cook now"
        elif above_floor_dish > 0:
            suggested_next_cut = "Trim 1 dish if closeout timing allows"
        else:
            suggested_next_cut = "At floor. Protect execution"

    # Soft night flag: actual sales pace is trailing expected by more than 15%
    # AND we are past early open. This makes the engine more aggressive on
    # slow nights where burn gap alone might not trigger a cut.
    is_soft_night = (
        not is_closed
        and progress > 0.20
        and not small_sample_protection
        and actual_sales_pace < expected_sales_pace * 0.85
        and (above_floor_line + above_floor_dish) > 0
    )

    # Declining momentum flag: pace is below expected AND room is shrinking fast
    declining_momentum = (
        not is_closed
        and pace_difference < -150
        and boh_room_left < target_boh_dollars * 0.25
        and (above_floor_line + above_floor_dish) > 0
    )

    if is_closed: