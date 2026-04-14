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

    header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0rem;
    }

    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0rem;
        position: fixed;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 4.75rem;
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns three CUMULATIVE sales vectors — one point per bucket boundary.

    Y axis = total dollars accumulated from open to that point in the shift.
    The slope of the actual line at the 'Now' marker = current sales pace ($/hr),
    matching the pace callout exactly.

    - expected_cumulative:  cumulative sales the curve predicts at each bucket boundary
    - actual_cumulative:    synthetic cumulative curve anchored to actual_sales_so_far at
                            elapsed_hours, shaped by the demand curve so the slope at
                            'now' equals the actual_pace_per_hr
    - projected_cumulative: continues from actual_sales_so_far to projected_final_sales
                            following the remaining curve shape

    All three start at $0 at open and are plotted at bucket boundaries (n+1 points
    for n buckets) so the chart reads as a smooth rising curve.
    """
    bucket_count = len(curve)
    if bucket_count == 0 or hours_open == 0:
        empty = np.zeros(2)
        return empty, empty, empty

    bucket_size_hrs = hours_open / bucket_count

    # Build cumulative expected: sum curve weights up to each bucket boundary
    # Points: 0 at open, then cumulative at end of each bucket
    cum_curve = np.concatenate([[0.0], np.cumsum(curve)])  # length bucket_count+1
    expected_cumulative = cum_curve * projected_final_sales

    # Current position
    completed_buckets = int(clamp(math.floor(elapsed_hours / bucket_size_hrs), 0, bucket_count))
    partial_ratio = clamp(
        (elapsed_hours - completed_buckets * bucket_size_hrs) / bucket_size_hrs
        if bucket_size_hrs > 0 else 0, 0, 1
    )
    actual_pace_per_hr = actual_sales_so_far / max(elapsed_hours, 0.25)

    # Build actual cumulative using a simple linear interpolation anchored to
    # two hard facts: $0 at open and actual_sales_so_far at elapsed_hours.
    # We shape the curve using the demand curve weights so it rises naturally,
    # but the terminal value is ALWAYS exactly actual_sales_so_far.
    #
    # For each completed whole bucket boundary i, the cumulative actual is:
    #   actual[i] = actual_sales_so_far * (cum_curve[i] / cum_curve_at_now)
    # where cum_curve_at_now is the interpolated curve value at elapsed_hours.
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
    # Terminal point: always exactly actual_sales_so_far at marker position
    # This ensures the line ends AT the actual number, not an approximation
    if completed_buckets < bucket_count:
        actual_cumulative[completed_buckets] = actual_sales_so_far
    else:
        actual_cumulative[bucket_count] = actual_sales_so_far

    # Build projected cumulative: starts at actual_sales_so_far at 'now',
    # follows remaining curve shape to projected_final_sales
    projected_cumulative = np.full(bucket_count + 1, np.nan)
    projected_cumulative[completed_buckets] = actual_sales_so_far
    remaining_sales = max(projected_final_sales - actual_sales_so_far, 0.0)
    remaining_curve_total = cum_curve[bucket_count] - cum_curve[completed_buckets]
    for i in range(completed_buckets + 1, bucket_count + 1):
        frac = (cum_curve[i] - cum_curve[completed_buckets]) / max(remaining_curve_total, 0.001)
        projected_cumulative[i] = actual_sales_so_far + remaining_sales * frac

    return expected_cumulative, actual_cumulative, projected_cumulative


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

    x_boundary = [i * bucket_size_minutes for i in range(bucket_count + 1)]

    tick_minutes = list(range(0, total_minutes_open + 1, 30))
    if tick_minutes[-1] != total_minutes_open:
        tick_minutes.append(total_minutes_open)
    tickvals = tick_minutes
    ticktext = [fmt_clock(open_minutes + mins) for mins in tick_minutes]

    marker_x = clamp(elapsed_hours * 60, 0, total_minutes_open)
    marker_label = fmt_clock(open_minutes + int(round(marker_x)))

    actual_x = []
    actual_y = []
    completed_bucket_index = int(marker_x // bucket_size_minutes) if bucket_size_minutes > 0 else 0

    for i, val in enumerate(actual_cum):
        if np.isnan(val):
            continue
        x_val = i * bucket_size_minutes
        if i <= completed_bucket_index:
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
        if burn_gap > 35 and above_floor_line + above_floor_dish > 0:
            decision = "TIGHTEN CLOSEOUT"
        else:
            decision = "CLOSE WITH CONTROL"
    else:
        if small_sample_protection:
            decision = "HOLD STEADY"
        elif early_phase_protection and burn_gap > 25:
            decision = "PREP TO CUT"
        elif burn_gap > 55 and hours_until_tight < 1.0 and (above_floor_line + above_floor_dish) > 0:
            decision = "CUT NOW"
        elif is_soft_night and burn_gap > 0:
            # Soft night: pace is trailing and we have room to cut — escalate
            decision = "CUT NOW" if burn_gap > 30 else "PREP TO CUT"
        elif declining_momentum:
            # Room is almost gone and pace is soft — protect the finish
            decision = "CUT NOW" if hours_until_tight < 0.5 else "PREP TO CUT"
        elif burn_gap > 15 and (above_floor_line + above_floor_dish) > 0:
            decision = "PREP TO CUT"
        else:
            decision = "HOLD STEADY"

    if decision == "HOLD STEADY":
        hero_class = "hero-green"
        hero_sub = "Current staffing still fits the moment."
        if phase == "PEAK":
            what_matters = "You are in the strongest demand window. Labor decisions matter most here"
        elif phase == "DECLINE":
            what_matters = "Peak has passed. Sales are still coming in, but the slope is weakening"
        else:
            what_matters = "The room is still building. Pace matters more than isolated tickets"
    elif decision == "PREP TO CUT":
        hero_class = "hero-orange"
        hero_sub = "Room is tightening. Start lining up the next move without hurting execution."
        what_matters = "Decline phase. Start identifying the next cut while protecting service"
    elif decision == "CUT NOW":
        hero_class = "hero-red"
        hero_sub = "Remaining revenue no longer supports current staffing."
        what_matters = "Make the next reduction now to protect the finish"
    elif decision == "TIGHTEN CLOSEOUT":
        hero_class = "hero-orange"
        hero_sub = "Final sales are locked. You are above closeout floor and still burning unnecessary labor."
        what_matters = "Revenue is done. Tighten one closeout position now"
    else:
        hero_class = "hero-blue"
        hero_sub = "Final sales are locked. Finish clean and get the team out inside target."
        what_matters = "Revenue is done. Close with purpose and keep the team moving"

    if is_closed:
        why_now = (
            f"Sales are locked. Current BOH burn is {money_hr(boh_burn_per_hour)}. "
            f"Remaining BOH room is {money(boh_room_left)}. Closeout floor is "
            f"{closeout_floor['line_cooks']} cooks and {closeout_floor['dishwashers']} dish."
        )
    else:
        why_now = (
            f"Actual pace is {'ahead of' if pace_difference >= 0 else 'behind'} expected by "
            f"{money_hr(abs(pace_difference))}. Current BOH burn is {money_hr(boh_burn_per_hour)} "
            f"vs allowed burn {money_hr(allowed_boh_burn)}. Remaining BOH room is {money(boh_room_left)}. "
            f"Floor is {floor_now['line_cooks']} cooks and {floor_now['dishwashers']} dish."
        )

    if is_closed:
        recovery_label = "None"
        recovery_copy = "No remaining revenue is left to recover labor. Closeout is now pure control."
        recovery_fill = 0
        recovery_bar = "bar-fill-red"
    else:
        if boh_room_left <= 0:
            recovery_label = "No room left"
            recovery_copy = "Current labor has already used the room left before missing target."
            recovery_fill = 100
            recovery_bar = "bar-fill-red"
        elif recovery_ratio >= 8:
            recovery_label = "Plenty left"
            recovery_copy = "There is still enough revenue left to support current staffing if execution is strong."
            recovery_fill = 72
            recovery_bar = "bar-fill-green"
        elif recovery_ratio >= 3:
            recovery_label = "Some left"
            recovery_copy = "There is still recoverable revenue left, but the room is getting smaller."
            recovery_fill = 48
            recovery_bar = "bar-fill-yellow"
        else:
            recovery_label = "Very little left"
            recovery_copy = "Remaining sales are getting harder to usefully recover against labor."
            recovery_fill = 24
            recovery_bar = "bar-fill-red"

    if projected_boh_pct <= target_boh_pct * 0.82:
        pressure_label = "Comfortable"
        pressure_copy = "Labor still has enough room for this point in the shift."
        pressure_fill = 30
        pressure_bar = "bar-fill-green"
    elif projected_boh_pct <= target_boh_pct:
        pressure_label = "Manageable"
        pressure_copy = "The finish is still inside target, but not loose."
        pressure_fill = 56
        pressure_bar = "bar-fill-yellow"
    else:
        pressure_label = "Tight"
        pressure_copy = "Current labor is above the supported level from here."
        pressure_fill = 84
        pressure_bar = "bar-fill-red"

    if is_closed:
        momentum_label = "Locked"
        momentum_copy = "Revenue is over for this shift."
        momentum_fill = 100
        momentum_bar = "bar-fill-green"
    else:
        if pace_difference >= 250:
            momentum_label = "Holding"
            momentum_copy = "Sales are still coming in well for this phase."
            momentum_fill = 72
            momentum_bar = "bar-fill-green"
        elif pace_difference >= -150:
            momentum_label = "Soft"
            momentum_copy = "Pace is near normal for this phase."
            momentum_fill = 48
            momentum_bar = "bar-fill-yellow"
        else:
            momentum_label = "Soft"
            momentum_copy = "Pace is trailing normal pace."
            momentum_fill = 24
            momentum_bar = "bar-fill-red"

    if is_closed:
        state_copy = (
            f"Closeout minimum right now is {closeout_floor['line_cooks']} cooks and "
            f"{closeout_floor['dishwashers']} dish. Time since close is {int(closeout_elapsed * 60)} min."
        )
    else:
        state_copy = (
            f"Minimum floor right now is {floor_now['line_cooks']} cooks and "
            f"{floor_now['dishwashers']} dish."
        )

    recheck_minutes = 15 if decision in {"CUT NOW", "TIGHTEN CLOSEOUT"} else 20 if decision == "PREP TO CUT" else 15
    next_check = (test_dt + timedelta(minutes=recheck_minutes)).strftime("%I:%M %p").lstrip("0")

    # =========================
    # EXECUTION GUIDANCE
    # =========================

    # Hard deadline time for CUT NOW actions
    cut_deadline = (test_dt + timedelta(minutes=10)).strftime("%I:%M %p").lstrip("0")

    # Per-minute cost of inaction
    cost_per_minute = max(burn_gap, 0) / 60

    # Projected overage at close if no action taken
    projected_overage_at_close = max(burn_gap, 0) * max(hours_remaining if not is_closed else 1.0, 0)

    # Build execution command — the single directive a manager acts on
    if decision == "CUT NOW":
        exec_role = "Line Cook (Float)" if above_floor_line > 0 else "Dishwasher"
        exec_command = f"CUT NOW — {exec_role}"
        exec_saves = f"Saves {money(cost_waiting_15)} in the next 15 min"
        exec_urgency = f"Every minute you wait costs {money(cost_per_minute)}/min"
        exec_deadline = f"Do this before {cut_deadline}"
        exec_color = "#ef4444"
        exec_border = "#dc2626"
    elif decision == "TIGHTEN CLOSEOUT":
        exec_role = "Line Cook (Float)" if line_cooks > closeout_floor["line_cooks"] else "Dishwasher"
        exec_command = f"TIGHTEN NOW — {exec_role}"
        exec_saves = f"Saves {money(cost_waiting_15)} before close"
        exec_urgency = f"Revenue is locked. Every minute costs {money(cost_per_minute)}/min"
        exec_deadline = f"Do this before {cut_deadline}"
        exec_color = "#f59e0b"
        exec_border = "#d97706"
    elif decision == "PREP TO CUT":
        exec_role = "Line Cook (Float)" if above_floor_line > 0 else "Dishwasher"
        exec_command = f"IDENTIFY NEXT CUT — {exec_role}"
        exec_saves = f"Potential savings if acted at next window: {money(cost_waiting_15 * 2)}"
        exec_urgency = f"Room is tightening. Burn gap is {money_hr(burn_gap)} over supported level"
        exec_deadline = f"Recheck at {next_check}"
        exec_color = "#f59e0b"
        exec_border = "#d97706"
    else:
        exec_command = "HOLD CURRENT STAFFING"
        exec_saves = "Labor is within supported range"
        exec_urgency = f"Projected BOH finish: {pct(projected_boh_pct)} vs target {pct(target_boh_pct)}"
        exec_deadline = f"Recheck at {next_check}"
        exec_color = "#22c55e"
        exec_border = "#16a34a"

    # Build cut sequence for the rest of the shift
    cut_sequence = []
    if not is_closed and hours_remaining > 0:
        # Scenario: sales hold as projected
        remaining_boh_room_hold = target_boh_dollars - boh_labor_so_far
        affordable_hrs_hold = remaining_boh_room_hold / max(boh_burn_per_hour, 1)
        if affordable_hrs_hold >= hours_remaining:
            cut_sequence.append(("If sales hold", "No further cuts needed — finish at current staffing", "green"))
        else:
            cut_sequence.append(("If sales hold", f"Cut 1 {('line cook' if above_floor_line > 0 else 'dish')} at {next_check}", "yellow"))

        # Scenario: sales drop 10%
        sales_drop_10 = projected_final_sales * 0.90
        boh_target_10 = sales_drop_10 * (target_boh_pct / 100)
        room_10 = boh_target_10 - boh_labor_so_far
        hrs_supported_10 = room_10 / max(boh_burn_per_hour, 1)
        if hrs_supported_10 < hours_remaining * 0.5:
            cut_sequence.append(("If sales drop 10%", f"Cut 1 line cook immediately + recheck in 15 min", "red"))
        else:
            cut_sequence.append(("If sales drop 10%", f"Cut 1 line cook at {next_check}", "yellow"))

        # Scenario: sales drop 20%
        sales_drop_20 = projected_final_sales * 0.80
        boh_target_20 = sales_drop_20 * (target_boh_pct / 100)
        room_20 = boh_target_20 - boh_labor_so_far
        hrs_supported_20 = room_20 / max(boh_burn_per_hour, 1)
        if hrs_supported_20 < 0:
            cut_sequence.append(("If sales drop 20%", "Cut 1 line cook + 1 dish now. Floor is all that's left", "red"))
        else:
            cut_sequence.append(("If sales drop 20%", f"Cut 1 line cook at {next_check}, hold dish until decline confirmed", "red"))
    else:
        cut_sequence.append(("Closeout", f"Hold at closeout floor: {closeout_floor['line_cooks']} cooks + {closeout_floor['dishwashers']} dish", "yellow"))

    expected_hourly, actual_line, projected_hourly = build_sales_vectors(
        hours_open=hours_open,
        curve=curve,
        actual_sales_so_far=sales_so_far,
        projected_final_sales=projected_final_sales,
        elapsed_hours=hours_open_so_far,
    )

    affordable_hours_left = boh_room_left / max(boh_burn_per_hour, 1) if boh_room_left > 0 else 0.0

    model = {
        "day_name": day_name,
        "shift": shift,
        "open_t": open_t,
        "close_t": close_t,
        "test_t": test_t,
        "hours_open": hours_open,
        "hours_open_so_far": hours_open_so_far,
        "hours_remaining": hours_remaining,
        "closeout_elapsed": closeout_elapsed,
        "progress": progress,
        "phase": phase,
        "is_closed": is_closed,
        "sales_so_far": sales_so_far,
        "average_check": average_check,
        "covers_so_far": covers_so_far,
        "total_reservations_today": total_reservations_today,
        "boh_labor_so_far": boh_labor_so_far,
        "prep_labor": prep_labor,
        "foh_labor_so_far": foh_labor_so_far,
        "line_cooks": line_cooks,
        "dishwashers": dishwashers,
        "dining_room_feel": dining_room_feel,
        "projected_final_sales": projected_final_sales,
        "expected_sales_so_far": expected_sales_so_far,
        "target_boh_dollars": target_boh_dollars,
        "target_total_labor_dollars": target_total_labor_dollars,
        "current_boh_pct": current_boh_pct,
        "projected_boh_pct": projected_boh_pct,
        "projected_total_labor_pct": projected_total_labor_pct,
        "boh_room_left": boh_room_left,
        "boh_burn_per_hour": boh_burn_per_hour,
        "allowed_boh_burn": allowed_boh_burn,
        "burn_gap": burn_gap,
        "cost_waiting_15": cost_waiting_15,
        "remaining_sales_room": remaining_sales_room,
        "recovery_ratio": recovery_ratio,
        "actual_sales_pace": actual_sales_pace,
        "expected_sales_pace": expected_sales_pace,
        "pace_difference": pace_difference,
        "hours_until_tight": hours_until_tight,
        "closeout_room_hours": closeout_window_hours if is_closed else closeout_room_hours,
        "in_transition": in_transition,
        "suggested_next_cut": suggested_next_cut,
        "decision": decision,
        "hero_class": hero_class,
        "hero_sub": hero_sub,
        "what_matters": what_matters,
        "why_now": why_now,
        "recovery_label": recovery_label,
        "recovery_copy": recovery_copy,
        "recovery_fill": recovery_fill,
        "recovery_bar": recovery_bar,
        "pressure_label": pressure_label,
        "pressure_copy": pressure_copy,
        "pressure_fill": pressure_fill,
        "pressure_bar": pressure_bar,
        "momentum_label": momentum_label,
        "momentum_copy": momentum_copy,
        "momentum_fill": momentum_fill,
        "momentum_bar": momentum_bar,
        "state_copy": state_copy,
        "floor_now": floor_now,
        "closeout_floor": closeout_floor,
        "next_check": next_check,
        "happy_hour_note": HH_NOTES.get(day_name, ""),
        "expected_hourly": expected_hourly,
        "actual_line": actual_line,
        "projected_hourly": projected_hourly,
        "curve_progress": curve_progress,
        "affordable_hours_left": affordable_hours_left,
        "exec_command": exec_command,
        "exec_saves": exec_saves,
        "exec_urgency": exec_urgency,
        "exec_deadline": exec_deadline,
        "exec_color": exec_color,
        "exec_border": exec_border,
        "cut_sequence": cut_sequence,
        "cost_per_minute": cost_per_minute,
        "projected_overage_at_close": projected_overage_at_close,
        # Early shift guard: suppress unreliable projections when shift just started
        # Threshold: less than 20% through the shift OR less than $1,500 in sales
        "early_shift_guard": progress < 0.20 or sales_so_far < 1500,
        "early_recheck_time": (test_dt.replace(hour=test_dt.hour, minute=test_dt.minute) if True else None),
    }
    return model


def compute_splh(
    model: dict,
    target_boh_pct: float,
    target_total_pct: float,
    boh_avg_wage: float = 18.0,
    foh_avg_wage: float = 4.50,
) -> dict:
    """
    Compute Sales Per Labor Hour (SPLH) metrics.

    Hours are estimated from labor dollars using configurable avg wage rates.
    Defaults: BOH $18/hr, FOH $4.50/hr (Amore blended: servers $1/hr,
    host $16-17/hr, barback $18/hr — weighted by hours on clock).

    Live SPLH      = sales so far ÷ total hours on clock right now
    Target SPLH    = blended_wage ÷ target_total_labor_%
    Projected SPLH = projected final sales ÷ projected total hours at close
    """
    BOH_WAGE  = boh_avg_wage
    FOH_WAGE  = foh_avg_wage

    sales        = model["sales_so_far"]
    proj_sales   = model["projected_final_sales"]
    boh_dollars  = model["boh_labor_so_far"]
    foh_dollars  = model["foh_labor_so_far"]
    avg_check    = model["average_check"]
    hrs_elapsed  = max(model["hours_open_so_far"], 0.25)
    hrs_remaining = model["hours_remaining"]
    burn_per_hr  = model["boh_burn_per_hour"]

    # Estimated hours on clock right now
    boh_hours_so_far = boh_dollars / BOH_WAGE
    foh_hours_so_far = foh_dollars / FOH_WAGE
    total_hours_so_far = max(boh_hours_so_far + foh_hours_so_far, 0.5)

    # Live SPLH
    live_splh = sales / total_hours_so_far

    # Projected total hours at close:
    # remaining BOH hours = burn_per_hr * hours_remaining / BOH_WAGE
    # remaining FOH hours estimated from FOH hourly rate
    foh_hourly_rate = foh_dollars / max(hrs_elapsed, 0.25)
    projected_boh_hours = boh_hours_so_far + (burn_per_hr * hrs_remaining / BOH_WAGE)
    projected_foh_hours = foh_hours_so_far + (foh_hourly_rate * hrs_remaining / FOH_WAGE)
    projected_total_hours = max(projected_boh_hours + projected_foh_hours, 0.5)
    projected_splh = proj_sales / projected_total_hours

    # Target SPLH derived from target labor % and avg check
    # If target total labor % = 16%, then for every $1 of sales
    # you spend $0.16 on labor. At avg_check per cover, SPLH target
    # = avg_check / (target_total_pct / 100) * blended_covers_per_hour
    # Simpler: target SPLH = 1 / (target_total_pct / 100) per dollar
    # = $1 of sales requires target_pct cents of labor
    # Express as: at what SPLH does labor % hit target?
    # SPLH_target = blended_wage / target_labor_%
    blended_wage = (boh_dollars * BOH_WAGE + foh_dollars * FOH_WAGE) / max(boh_dollars + foh_dollars, 1)
    target_splh = blended_wage / (target_total_pct / 100)

    # Color coding
    if live_splh >= target_splh * 1.05:
        splh_color = "#22c55e"
        splh_status = "On target"
    elif live_splh >= target_splh * 0.90:
        splh_color = "#f59e0b"
        splh_status = "Watch"
    else:
        splh_color = "#ef4444"
        splh_status = "Below target"

    return {
        "live_splh": live_splh,
        "projected_splh": projected_splh,
        "target_splh": target_splh,
        "splh_color": splh_color,
        "splh_status": splh_status,
        "total_hours_so_far": total_hours_so_far,
        "projected_total_hours": projected_total_hours,
    }


# =========================
# UI HELPERS
# =========================

def metric_card(label: str, value: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_card(label: str, value: str, copy: str, fill_pct: float, fill_class: str, footer: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-copy">{copy}</div>
            <div class="bar-wrap">
                <div class="{fill_class}" style="width:{clamp(fill_pct,0,100)}%;"></div>
            </div>
            <div class="metric-copy" style="margin-top:8px;">{footer}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



# =========================
# HEADER
# =========================
now_stamp = datetime.now().strftime("%I:%M %p").lstrip("0")
tz_day = datetime.now().strftime("%A")
st.markdown(
    f"""
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
        <div>
            <div style="font-size:2.0rem; font-weight:900; letter-spacing:-0.01em;">MarginCommand</div>
            <div class="small-note">BOH labor decision engine · {now_stamp} Eastern · {tz_day}</div>
        </div>
        <div style="text-align:right;">
            <div class="small-note" style="font-size:0.78rem;">Amore Italian Chophouse</div>
            <div class="small-note">Manager-first · real-time decisions</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# SCENARIO PRESET (full width, above columns)
# =========================
scenario_name = st.selectbox("Scenario preset", list(SCENARIOS.keys()), index=0, label_visibility="collapsed")
scenario = SCENARIOS[scenario_name]

if scenario is None:
    default_day = "Saturday"
    default_shift = "Dinner"
    default_hour12 = 6
    default_minute = 15
    default_am_pm = "PM"
    default_sales = 17020.10
    default_avg_check = 45.47
    default_covers = 190.0
    default_res = 368.0
    default_boh = 1351.66
    default_prep = 476.12
    default_foh = 556.78
    default_line = st.session_state.pop("override_line_cooks", 6)
    default_dish = st.session_state.pop("override_dishwashers", 2)
    default_feel = 3
else:
    default_day = scenario["day_name"]
    default_shift = scenario["shift"]
    default_hour12 = scenario["hour12"]
    default_minute = scenario["minute"]
    default_am_pm = scenario["am_pm"]
    default_sales = scenario["sales_so_far"]
    default_avg_check = scenario["average_check"]
    default_covers = scenario["covers_so_far"]
    default_res = scenario["total_reservations_today"]
    default_boh = scenario["boh_labor_so_far"]
    default_prep = scenario["prep_labor"]
    default_foh = scenario["foh_labor_so_far"]
    default_line = st.session_state.pop("override_line_cooks", scenario["line_cooks"])
    default_dish = st.session_state.pop("override_dishwashers", scenario["dishwashers"])
    default_feel = scenario["dining_room_feel"]

day_options = list(DAYPART_WINDOWS.keys())
default_day_index = day_options.index(default_day)
shift_options = available_shifts_for_day(default_day)
default_shift_index = shift_options.index(default_shift) if default_shift in shift_options else 0

# =========================
# TWO COLUMN LAYOUT
# =========================
col_left, col_right = st.columns([1.0, 1.4], gap="large")

with col_left:
    with st.form("shift_inputs", clear_on_submit=False):

        # --- Section 1: Shift Setup ---
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px; margin:16px 0 10px 0;">
                <div style="background:#1e40af; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.72rem; font-weight:900; flex-shrink:0;">1</div>
                <div style="font-weight:800; font-size:1.0rem;">Shift Setup</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            day_name = st.selectbox("Day of week", day_options, index=default_day_index)
        with c2:
            current_shift_options = available_shifts_for_day(day_name)
            selected_shift_index = current_shift_options.index(default_shift) if default_shift in current_shift_options else 0
            shift = st.selectbox("Shift", current_shift_options, index=selected_shift_index)

        c1, c2, c3 = st.columns(3)
        with c1:
            hour12 = st.selectbox("Hour", list(range(1, 13)), index=list(range(1, 13)).index(default_hour12))
        with c2:
            minute_options = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
            minute = st.selectbox("Minute", minute_options, index=minute_options.index(default_minute), format_func=lambda x: f"{x:02d}")
        with c3:
            am_pm = st.selectbox("AM / PM", ["AM", "PM"], index=0 if default_am_pm == "AM" else 1)

        # --- Section 2: Sales ---
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px; margin:16px 0 10px 0;">
                <div style="background:#1e40af; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.72rem; font-weight:900; flex-shrink:0;">2</div>
                <div style="font-weight:800; font-size:1.0rem;">Sales</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            sales_so_far = st.number_input("Sales so far ($)", min_value=0.0, value=float(default_sales), step=50.0)
        with c2:
            average_check = st.number_input("Average check ($)", min_value=0.0, value=float(default_avg_check), step=0.25)

        # --- Section 3: Guests ---
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px; margin:16px 0 10px 0;">
                <div style="background:#1e40af; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.72rem; font-weight:900; flex-shrink:0;">3</div>
                <div style="font-weight:800; font-size:1.0rem;">Guests</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            covers_so_far = st.number_input("Covers so far", min_value=0.0, value=float(default_covers), step=1.0)
        with c2:
            total_reservations_today = st.number_input("Total reservations today", min_value=0.0, value=float(default_res), step=1.0)

        # --- Section 4: Labor & Staff ---
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px; margin:16px 0 10px 0;">
                <div style="background:#1e40af; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.72rem; font-weight:900; flex-shrink:0;">4</div>
                <div style="font-weight:800; font-size:1.0rem;">Labor &amp; Staff</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        boh_labor_so_far = st.number_input("BOH labor so far ($)", min_value=0.0, value=float(default_boh), step=10.0)
        prep_labor = st.number_input("Prep labor ($)", min_value=0.0, value=float(default_prep), step=10.0)
        foh_labor_so_far = st.number_input("FOH labor so far ($)", min_value=0.0, value=float(default_foh), step=10.0)

        c1, c2 = st.columns(2)
        with c1:
            line_cooks = st.number_input("Line cooks", min_value=0, value=int(default_line), step=1)
        with c2:
            dishwashers = st.number_input("Dishwashers", min_value=0, value=int(default_dish), step=1)

        dining_room_feel = st.slider("Dining room feel", 1, 5, int(default_feel))

        # --- Targets ---
        st.markdown(
            "<div style=\"font-weight:700; font-size:0.85rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin:14px 0 8px 0;\">Targets</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            target_boh_pct = st.number_input("Target BOH %", min_value=1.0, max_value=30.0, value=float(DEFAULT_TARGET_BOH_PCT), step=0.5)
        with c2:
            target_total_pct = st.number_input("Target total labor %", min_value=1.0, max_value=40.0, value=float(DEFAULT_TARGET_TOTAL_PCT), step=0.5)

        # --- Wage Rates (for SPLH) ---
        st.markdown(
            "<div style=\"font-weight:700; font-size:0.85rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; margin:14px 0 8px 0;\">Avg Wage Rates</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            boh_avg_wage = st.number_input("BOH avg wage ($/hr)", min_value=1.0, max_value=50.0, value=20.82, step=0.50)
        with c2:
            foh_avg_wage = st.number_input("FOH avg wage ($/hr)", min_value=1.0, max_value=50.0, value=7.58, step=0.25)

        st.form_submit_button("Run MarginCommand →", use_container_width=True)

test_t = current_test_time(hour12, minute, am_pm)

model = build_projection_model(
    day_name=day_name,
    shift=shift,
    test_t=test_t,
    sales_so_far=sales_so_far,
    average_check=average_check,
    covers_so_far=covers_so_far,
    total_reservations_today=total_reservations_today,
    boh_labor_so_far=boh_labor_so_far,
    prep_labor=prep_labor,
    foh_labor_so_far=foh_labor_so_far,
    line_cooks=line_cooks,
    dishwashers=dishwashers,
    dining_room_feel=dining_room_feel,
    target_boh_pct=target_boh_pct,
    target_total_pct=target_total_pct,
)

splh = compute_splh(model, target_boh_pct, target_total_pct, boh_avg_wage=boh_avg_wage, foh_avg_wage=foh_avg_wage)

# =========================
# RIGHT COLUMN — OUTPUTS
# =========================

with col_right:

    # 1. Status bar
    open_str = model["open_t"].strftime("%I:%M %p").lstrip("0")
    close_str = model["close_t"].strftime("%I:%M %p").lstrip("0")
    hours_remaining_text = "Closed" if model["is_closed"] else f"{model['hours_remaining']:.1f} hrs remaining"

    phase_badge_colors = {
        "OPEN": ("#2563eb", "#dbeafe"),
        "BUILD": ("#d97706", "#fef3c7"),
        "PEAK": ("#16a34a", "#dcfce7"),
        "DECLINE": ("#ea580c", "#ffedd5"),
        "CLOSEOUT": ("#dc2626", "#fee2e2"),
    }
    phase_key = "CLOSEOUT" if model["is_closed"] else model["phase"]
    pb_bg, pb_text = phase_badge_colors.get(phase_key, ("#475569", "#f8fafc"))

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:14px; background:rgba(8,15,32,0.80); border:1px solid rgba(148,163,184,0.18); border-radius:12px; padding:10px 16px; margin-bottom:12px; flex-wrap:wrap;">
            <div style="background:{pb_bg}; color:{pb_text}; font-size:0.70rem; font-weight:900; text-transform:uppercase; letter-spacing:0.07em; border-radius:6px; padding:3px 9px; flex-shrink:0;">{phase_key}</div>
            <div class="small-note" style="flex-shrink:0;">Open {model['hours_open_so_far']:.1f} hrs</div>
            <div class="small-note" style="flex-shrink:0;">{hours_remaining_text}</div>
            <div class="small-note" style="flex-shrink:0; margin-left:auto;">Close: {close_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Decision hero card
    st.markdown(
        f"""
        <div class="hero {model['hero_class']}">
            <div class="hero-title">{model['decision']}</div>
            <div class="hero-sub">{model['hero_sub']}</div>
            <div class="hero-text">
                <strong>What matters right now:</strong> {model['what_matters']}. Recheck at {model['next_check']} based on test time.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Execution Order block — only when not HOLD STEADY
    if model["decision"] != "HOLD STEADY":
        exec_color = model["exec_color"]
        exec_border = model["exec_border"]
        st.markdown(
            f"""
            <div style="
                background: rgba(8,15,32,0.95);
                border: 2px solid {exec_border};
                border-left: 6px solid {exec_color};
                border-radius: 16px;
                padding: 18px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size:0.72rem; font-weight:800; text-transform:uppercase; color:{exec_color}; letter-spacing:0.08em; margin-bottom:6px;">Execution Order</div>
                <div style="font-size:1.25rem; font-weight:900; color:#f8fafc; margin-bottom:10px; letter-spacing:0.01em;">{model['exec_command']}</div>
                <div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
                    <div style="background:rgba(255,255,255,0.07); border-radius:8px; padding:8px 12px; font-size:0.84rem; font-weight:700; color:#f8fafc;">💰 {model['exec_saves']}</div>
                    <div style="background:rgba(255,255,255,0.07); border-radius:8px; padding:8px 12px; font-size:0.84rem; font-weight:700; color:#fca5a5;">⏱ {model['exec_urgency']}</div>
                    <div style="background:{exec_color}22; border:1px solid {exec_border}; border-radius:8px; padding:8px 12px; font-size:0.84rem; font-weight:800; color:{exec_color};">🎯 {model['exec_deadline']}</div>
                </div>
                <div style="font-size:0.80rem; color:#94a3b8; margin-top:4px;">{model['why_now']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. I Made the Cut button — only when CUT NOW or TIGHTEN CLOSEOUT
    if model["decision"] in {"CUT NOW", "TIGHTEN CLOSEOUT"}:
        if st.button("✅ I Made the Cut — Recalculate", use_container_width=True):
            floor_ref = model["closeout_floor"] if model["is_closed"] else model["floor_now"]
            if line_cooks > floor_ref["line_cooks"]:
                st.session_state["override_line_cooks"] = max(line_cooks - 1, floor_ref["line_cooks"])
            elif dishwashers > floor_ref["dishwashers"]:
                st.session_state["override_dishwashers"] = max(dishwashers - 1, floor_ref["dishwashers"])
            st.rerun()

    # 5. Rest of Shift — Cut Sequence — always when not HOLD STEADY
    if model["decision"] != "HOLD STEADY":
        cut_sequence = model["cut_sequence"]
        if cut_sequence:
            seq_color_map = {"green": "#22c55e", "yellow": "#f59e0b", "red": "#ef4444"}
            rows_html = ""
            for label, action, color_key in cut_sequence:
                c = seq_color_map.get(color_key, "#94a3b8")
                rows_html += f"""
                <div style="display:flex; align-items:flex-start; gap:12px; padding:8px 0; border-bottom:1px solid rgba(148,163,184,0.10);">
                    <div style="min-width:130px; font-size:0.75rem; font-weight:800; color:{c}; text-transform:uppercase; letter-spacing:0.04em; padding-top:2px;">{label}</div>
                    <div style="font-size:0.85rem; color:#f8fafc;">{action}</div>
                </div>
                """
            st.markdown(
                f"""
                <div style="
                    background: rgba(8,15,32,0.88);
                    border: 1px solid rgba(148,163,184,0.18);
                    border-radius: 14px;
                    padding: 14px 16px;
                    margin-bottom: 12px;
                ">
                    <div style="font-size:0.72rem; font-weight:800; text-transform:uppercase; color:#cbd5e1; letter-spacing:0.06em; margin-bottom:8px;">Rest of Shift — Cut Sequence</div>
                    {rows_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 6. Manager Signals — 2x2 grid
    c1, c2 = st.columns(2)
    with c1:
        signal_card(
            "Momentum",
            model["momentum_label"],
            model["momentum_copy"],
            model["momentum_fill"],
            model["momentum_bar"],
            f"Actual pace: {money_hr(model['actual_sales_pace'])} · Expected pace: {money_hr(model['expected_sales_pace']) if not model['is_closed'] else 'Locked'}",
        )
    with c2:
        pressure_footer = (
            f"Projected BOH finish {pct(model['projected_boh_pct'])} · Decision window: {max(model['hours_until_tight'],0):.2f} hrs"
            if not model["is_closed"]
            else f"Projected BOH finish {pct(model['projected_boh_pct'])} · Closeout burn {money_hr(model['boh_burn_per_hour'])}"
        )
        signal_card(
            "Pressure",
            model["pressure_label"],
            model["pressure_copy"],
            model["pressure_fill"],
            model["pressure_bar"],
            pressure_footer,
        )

    c3, c4 = st.columns(2)
    with c3:
        signal_card(
            "Remaining BOH room",
            model["recovery_label"],
            model["recovery_copy"],
            model["recovery_fill"],
            model["recovery_bar"],
            f"Remaining BOH room: {money(model['boh_room_left'])}",
        )
    with c4:
        signal_card(
            "Shift state",
            model["phase"].title() if not model["is_closed"] else "Closeout",
            model["state_copy"],
            65 if not model["is_closed"] else 100,
            "bar-fill-green" if not model["is_closed"] else "bar-fill-yellow",
            f"Line cooks on: {model['line_cooks']} · Dish on: {model['dishwashers']}",
        )


# =========================
# LOWER SECTION — Full width
# =========================

st.markdown("<hr style='border:none; border-top:1px solid rgba(148,163,184,0.15); margin:24px 0 20px 0;'>", unsafe_allow_html=True)

# Early shift guard — show holding message instead of bad projections
if model["early_shift_guard"]:
    recheck_min = model["next_check"]
    st.markdown(
        f"""
        <div style="
            background: rgba(8,15,32,0.92);
            border: 1px solid rgba(148,163,184,0.2);
            border-left: 5px solid #64748b;
            border-radius: 14px;
            padding: 18px 22px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 18px;
        ">
            <div style="font-size:1.8rem;">⏳</div>
            <div>
                <div style="font-size:0.78rem; font-weight:800; text-transform:uppercase; color:#94a3b8; letter-spacing:0.06em;">Shift just started — projections not yet reliable</div>
                <div style="font-size:1.05rem; font-weight:700; color:#f8fafc; margin-top:4px;">Enter sales at {recheck_min} for the first reliable read.</div>
                <div style="font-size:0.82rem; color:#94a3b8; margin-top:4px;">Need at least 20% of the shift (or $1,500 in sales) before the engine can project accurately. Labor metrics below are estimates only.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# BOH Room Visual Bar — full width (greyed out during early guard)
if model["early_shift_guard"]:
    room_bar_class = "bar-fill-grey" if False else "bar-fill-yellow"
    # Suppress entirely during early shift
if not model["early_shift_guard"]:
    if model["boh_room_left"] > 400:
        room_bar_class = "bar-fill-green"
    elif model["boh_room_left"] > 0:
        room_bar_class = "bar-fill-yellow"
    else:
        room_bar_class = "bar-fill-red"

if not model["early_shift_guard"]:
    room_bar_width = clamp((max(model["boh_room_left"], -600) + 600) / 12, 0, 100)
    st.markdown(
        f"""
        <div class="mini-visual" style="margin-bottom:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <div class="mini-label" style="margin-bottom:0;">BOH Labor Room</div>
                <div class="small-note">BOH room left: {money(model["boh_room_left"])} · Allowed burn from here: {money_hr(model["allowed_boh_burn"])}</div>
            </div>
            <div class="bar-wrap" style="height:18px;">
                <div class="{room_bar_class}" style="width:{room_bar_width}%;"></div>
            </div>
            <div class="small-note" style="margin-top:6px;">How much BOH room remains before missing the finish target. Green = comfortable. Yellow = watch it. Red = over.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Early guard label for metric rows
if model["early_shift_guard"]:
    st.markdown(
        "<div style='font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;'>⚠ Estimates only — not enough shift data yet</div>",
        unsafe_allow_html=True,
    )

def make_gauge(value, target, max_val, title, guard):
    if value <= target:
        color = "#22c55e"; label = "On Target"
    elif value <= target + 5:
        color = "#f59e0b"; label = "Watch"
    else:
        color = "#ef4444"; label = "Over"
    suffix = " *" if guard else ""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 32, "color": color}},
        title={"text": f"{title}{suffix}<br><span style='font-size:0.78em;color:#94a3b8;'>{label} · Target {target:.0f}%</span>",
               "font": {"size": 12, "color": "#cbd5e1"}},
        gauge={
            "axis": {"range": [0, max_val], "tickvals": [0, target, max_val],
                     "ticktext": ["0%", f"{target:.0f}%", f"{max_val:.0f}%"],
                     "tickfont": {"color": "#94a3b8", "size": 10}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [0, target],          "color": "rgba(34,197,94,0.2)"},
                {"range": [target, target + 5], "color": "rgba(245,158,11,0.2)"},
                {"range": [target + 5, max_val],"color": "rgba(239,68,68,0.2)"},
            ],
            "threshold": {"line": {"color": "white", "width": 3}, "thickness": 0.85, "value": target},
        },
    ))
    fig.update_layout(paper_bgcolor="rgba(8,15,32,0.92)", plot_bgcolor="rgba(0,0,0,0)",
                      font={"color": "#f8fafc"}, height=210, margin=dict(l=15, r=15, t=55, b=5))
    return fig

# Row 1: BOH Gauge + FOH Gauge + Decision Window
c1, c2, c3 = st.columns([1.0, 1.0, 0.8])
with c1:
    current_boh = model["current_boh_pct"]
    guard = model["early_shift_guard"]
    st.plotly_chart(
        make_gauge(current_boh, target_boh_pct, 30.0, "Current BOH Labor %", guard),
        use_container_width=True,
        config={"displayModeBar": False},
    )

with c2:
    proj_foh = 100 * model["foh_labor_so_far"] / max(model["sales_so_far"], 1)
    foh_target = target_total_pct - target_boh_pct
    st.plotly_chart(make_gauge(proj_foh, foh_target, 20.0, "Current FOH Labor %", guard),
                    use_container_width=True, config={"displayModeBar": False})

with c3:
    decision_window_text = (
        f"{max(model['hours_until_tight'], 0) * 60:.0f} min"
        if not model["is_closed"]
        else f"{max(model['closeout_room_hours'], 0) * 60:.0f} min"
    )
    metric_card("Decision Window", decision_window_text,
        "Minutes before the labor situation gets more urgent if nothing changes.")

# SPLH Row — suppressed during early shift guard
if not model["early_shift_guard"]:
  st.markdown(
    f"""
    <div style="
        background: rgba(8,15,32,0.95);
        border: 1px solid {splh['splh_color']}44;
        border-left: 5px solid {splh['splh_color']};
        border-radius: 14px;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 14px;
    ">
        <div style="display:flex; align-items:center; gap:16px;">
            <div>
                <div style="font-size:0.72rem; font-weight:800; text-transform:uppercase; color:#94a3b8; letter-spacing:0.06em;">Sales Per Labor Hour (SPLH)</div>
                <div style="font-size:1.6rem; font-weight:900; color:{splh['splh_color']}; margin-top:2px;">${splh['live_splh']:,.0f}/hr</div>
                <div style="font-size:0.82rem; color:#cbd5e1; margin-top:2px;">{splh['splh_status']} &nbsp;·&nbsp; Target: ${splh['target_splh']:,.0f}/hr</div>
            </div>
        </div>
        <div style="display:flex; gap:24px; flex-wrap:wrap;">
            <div style="text-align:center;">
                <div style="font-size:0.70rem; font-weight:800; text-transform:uppercase; color:#94a3b8; letter-spacing:0.05em;">Projected SPLH</div>
                <div style="font-size:1.1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${splh['projected_splh']:,.0f}/hr</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:0.70rem; font-weight:800; text-transform:uppercase; color:#94a3b8; letter-spacing:0.05em;">Est. Hours on Clock</div>
                <div style="font-size:1.1rem; font-weight:800; color:#f8fafc; margin-top:4px;">{splh['total_hours_so_far']:,.1f} hrs</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:0.70rem; font-weight:800; text-transform:uppercase; color:#94a3b8; letter-spacing:0.05em;">Proj. Total Hours</div>
                <div style="font-size:1.1rem; font-weight:800; color:#f8fafc; margin-top:4px;">{splh['projected_total_hours']:,.1f} hrs</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
  )

# Row 2: 4 burn metrics
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(
        "BOH Burn / hr",
        money_hr(model["boh_burn_per_hour"]),
        "How much your BOH labor is costing per hour right now. This is what you\u2019re spending on kitchen staff every 60 minutes.",
    )
with c2:
    metric_card(
        "Allowed BOH Burn",
        money_hr(model["allowed_boh_burn"]),
        "The maximum you can spend on BOH per hour from this point and still finish at your target labor %. If current burn exceeds this, you\u2019re heading over.",
    )
with c3:
    # Burn gap: negative = room to spare (green), positive = over (red)
    burn_gap_val = model["burn_gap"]
    if burn_gap_val <= 0:
        burn_gap_label = f"Room to spare: {money_hr(abs(burn_gap_val))}"
        burn_gap_copy = "You're spending less per hour than your target allows — you have labor room left."
        burn_gap_color = "#22c55e"
    else:
        burn_gap_label = f"Over by: {money_hr(burn_gap_val)}"
        burn_gap_copy = "Your BOH is costing more per hour than remaining sales can justify. Every hour you wait adds to your overage."
        burn_gap_color = "#ef4444"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Burn Gap</div>
            <div class="metric-value" style="color:{burn_gap_color};">{burn_gap_label}</div>
            <div class="metric-copy">{burn_gap_copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c4:
    metric_card(
        "Cost of Waiting 15 min",
        money(model["cost_waiting_15"]),
        "If you do nothing right now, this is what the next 15 minutes of BOH labor will cost you.",
    )

# Row 3: Profit Check — always-visible compact 4-col row
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(
        "Actual Sales Pace",
        money_hr(model["actual_sales_pace"]) if not model["is_closed"] else "Locked",
        "Your real-time hourly sales rate. Compare to Expected — if above, you're running hot.",
    )
with c2:
    metric_card(
        "Expected Sales Pace",
        money_hr(model["expected_sales_pace"]) if not model["is_closed"] else "Locked",
        "What the shift should be earning right now based on historical demand pattern.",
    )
with c3:
    metric_card(
        "Remaining BOH Room",
        money(model["boh_room_left"]),
        "Dollar cushion remaining before BOH labor exceeds your target for the shift. When this hits zero, you're over.",
    )
with c4:
    # Projected overage: flip copy and color based on over/under
    overage_val = model["projected_overage_at_close"]
    boh_room = model["boh_room_left"]
    if overage_val > 0:
        overage_label = f"Over by {money(overage_val)}"
        overage_copy = "Where BOH labor % will land at close if nothing changes. This is your projected finish."
        overage_color = "#ef4444"
    elif boh_room > 0:
        overage_label = f"{money(boh_room)} room left"
        overage_copy = "BOH is projected to finish under target. You have room to close."
        overage_color = "#22c55e"
    else:
        overage_label = "At target"
        overage_copy = "BOH is running right at the finish target."
        overage_color = "#94a3b8"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">BOH Finish Outlook</div>
            <div class="metric-value" style="color:{overage_color};">{overage_label}</div>
            <div class="metric-copy">{overage_copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Row 4: Advanced Metrics — collapsed expander, unchanged
with st.expander("Advanced Metrics", expanded=False):
    c1, c2 = st.columns(2)

    hours_remaining_text = "Closed" if model["is_closed"] else f"{model['hours_remaining']:.2f} hrs"

    with c1:
        st.markdown(f"<div class='subtle'>Projected final sales: {money(model['projected_final_sales'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Expected sales so far: {money(model['expected_sales_so_far'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Target BOH dollars: {money(model['target_boh_dollars'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Target total labor dollars: {money(model['target_total_labor_dollars'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Current BOH %: {pct(model['current_boh_pct'])}</div>", unsafe_allow_html=True)
        current_foh_pct = 100 * model["foh_labor_so_far"] / max(model["sales_so_far"], 1)
        st.markdown(f"<div class='subtle'>Current FOH %: {pct(current_foh_pct)}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='subtle'>Phase: {model['phase'].title()}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Hours open so far: {model['hours_open_so_far']:.2f} hrs</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Hours remaining: {hours_remaining_text}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Projected loss if ignored 15 min: {money(model['cost_waiting_15'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Suggested next move: {model['suggested_next_cut']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtle'>Notes: {model['happy_hour_note']}</div>", unsafe_allow_html=True)

    st.markdown("")

    if model["is_closed"]:
        close_fig = build_closeout_chart(model)
        st.plotly_chart(close_fig, use_container_width=True)
        st.markdown(
            f"""
            <div class="blue-box">
                <div class="blue-title">Right now</div>
                <div class="blue-copy">
                    Sales are locked. Burn is running at about {money_hr(model['boh_burn_per_hour'])} through closeout.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        service_fig = build_service_chart(model, model["open_t"])
        st.plotly_chart(service_fig, use_container_width=True)

        # Pace callout — the single most important number off the chart
        pace_diff = model["pace_difference"]
        pace_dir = "ahead of" if pace_diff >= 0 else "behind"
        pace_color = "#22c55e" if pace_diff >= 0 else "#ef4444"
        pace_icon = "▲" if pace_diff >= 0 else "▼"
        st.markdown(
            f"""
            <div style="
                background: rgba(8,15,32,0.95);
                border: 1px solid {pace_color}44;
                border-left: 5px solid {pace_color};
                border-radius: 14px;
                padding: 14px 18px;
                display: flex;
                align-items: center;
                gap: 16px;
                margin-top: 4px;
            ">
                <div style="font-size: 1.6rem; font-weight: 900; color: {pace_color};">{pace_icon} {money_hr(abs(pace_diff))}</div>
                <div>
                    <div style="font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.06em;">Current Sales Pace vs Expected</div>
                    <div style="font-size: 0.9rem; color: #f8fafc; margin-top: 2px;">
                        Running <strong style="color:{pace_color};">{pace_dir} expected</strong> right now &nbsp;·&nbsp;
                        Actual: {money_hr(model['actual_sales_pace'])} &nbsp;·&nbsp; Expected: {money_hr(model['expected_sales_pace'])}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
