import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_FILE = "hospital_cumulative_data.xlsx"
REQUIRED_COLUMNS = ["년월", "지점명", "유입경로", "신환수"]

# ----------------- 페이지 설정 & 모던 UI CSS 주입 -----------------
st.set_page_config(
    page_title="Clinic Growth Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 이미지 디자인을 반영한 보라 계열 그라디언트 및 화이트 카드 스타일
st.markdown(
    """
<style>
    /* 전체 배경 그라디언트 */
    .stApp {
        background: linear-gradient(135deg, #f5f4fb 0%, #ece8f9 50%, #e2dcfa 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-right: 1px solid #e0dcf5;
    }
    
    /* 상단 헤더 숨김 및 여백 조정 */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* SaaS 카드 위젯 스타일 */
    .metric-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.05);
        border: 1px solid #f0eef9;
        margin-bottom: 12px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.1);
    }
    .metric-title {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: -0.01em;
        text-transform: uppercase;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .metric-value {
        color: #1e1b4b;
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .metric-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.75rem;
        font-weight: 600;
        color: #4f46e5;
        background: #eef2ff;
        padding: 2px 8px;
        border-radius: 6px;
    }

    /* 차트 컨테이너 래핑 */
    .chart-box {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #f0eef9;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.04);
        margin-bottom: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)


def load_cumulative_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)
        df["년월"] = df["년월"].astype(str)
        return df
    # 기본 예시 데이터셋 자동 생성 (첫 실행 시에도 대시보드가 비어있지 않도록 구성)
    sample_data = {
        "년월": [
            "2026-01",
            "2026-01",
            "2026-01",
            "2026-01",
            "2026-02",
            "2026-02",
            "2026-02",
            "2026-02",
            "2026-03",
            "2026-03",
            "2026-03",
            "2026-03",
        ],
        "지점명": [
            "강남본점",
            "강남본점",
            "서초점",
            "분당점",
            "강남본점",
            "서초점",
            "서초점",
            "분당점",
            "강남본점",
            "강남본점",
            "서초점",
            "분당점",
        ],
        "유입경로": [
            "네이버 플레이스",
            "인스타그램",
            "네이버 플레이스",
            "지인소개",
            "네이버 플레이스",
            "네이버 플레이스",
            "인스타그램",
            "당근마켓",
            "네이버 플레이스",
            "지인소개",
            "인스타그램",
            "지인소개",
        ],
        "신환수": [140, 95, 88, 52, 160, 105, 110, 68, 175, 115, 130, 84],
    }
    df = pd.DataFrame(sample_data)
    df.to_excel(DATA_FILE, index=False)
    return df


def save_cumulative_data(df):
    df.to_excel(DATA_FILE, index=False)


# ----------------- 데이터 로드 & 사이드바 -----------------
master_df = load_cumulative_data()

with st.sidebar:
    st.markdown("### 📊 Management")
    st.caption("병원 지점별 신환 분석 포털")

    all_branches = ["전지점(통합)"] + sorted(
        master_df["지점명"].unique().tolist()
    )
    selected_branch = st.selectbox("🎯 지점 선택", all_branches)

    all_months = sorted(master_df["년월"].unique().tolist())
    selected_period = st.select_slider(
        "📅 분석 기간",
        options=all_months,
        value=(all_months[0], all_months[-1])
        if len(all_months) > 1
        else (all_months[0], all_months[0]),
    )

    st.markdown("---")
    st.markdown("### 📤 데이터 업로드")
    uploaded_file = st.file_uploader(
        "엑셀 파일 병합 (.xlsx)", type=["xlsx"]
    )
    if uploaded_file is not None:
        new_df = pd.read_excel(uploaded_file)
        new_df["년월"] = new_df["년월"].astype(str)
        if all(col in new_df.columns for col in REQUIRED_COLUMNS):
            if st.button("신규 데이터 병합", use_container_width=True):
                combined_df = pd.concat([master_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(
                    subset=["년월", "지점명", "유입경로"], keep="last"
                )
                save_cumulative_data(combined_df)
                st.success("업로드 완료!")
                st.rerun()

# ----------------- 데이터 필터링 -----------------
start_m, end_m = selected_period
filtered_df = master_df[
    (master_df["년월"] >= start_m) & (master_df["년월"] <= end_m)
]
if selected_branch != "전지점(통합)":
    filtered_df = filtered_df[filtered_df["지점명"] == selected_branch]

# ----------------- 메인 대시보드 헤더 -----------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        f"<h2 style='color: #1e1b4b; margin-bottom: 0px;'>📌 Clinic Growth KPIs</h2>"
        f"<p style='color: #64748b; margin-top: 4px; font-size: 0.95rem;'>지점: <b>{selected_branch}</b> | 분석기간: <b>{start_m} ~ {end_m}</b></p>",
        unsafe_allow_html=True,
    )

# ----------------- 상단 4개 KPI 메트릭 카드 (이미지 스타일) -----------------
total_patients = filtered_df["신환수"].sum()
top_channel = (
    filtered_df.groupby("유입경로")["신환수"].sum().idxmax()
    if not filtered_df.empty
    else "-"
)
avg_monthly = (
    round(
        total_patients / len(filtered_df["년월"].unique()),
        1,
    )
    if not filtered_df.empty
    else 0
)
active_branches = (
    len(filtered_df["지점명"].unique())
    if selected_branch == "전지점(통합)"
    else 1
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-title">👥 누적 신환수</div>
        <div class="metric-value">{total_patients:,} <span style="font-size:1rem; font-weight:500;">명</span></div>
        <div class="metric-badge">Total Acquisition</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-title">🔥 1위 유입 채널</div>
        <div class="metric-value" style="font-size:1.45rem;">{top_channel}</div>
        <div class="metric-badge">Top Performing</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-title">📈 월평균 신환수</div>
        <div class="metric-value">{avg_monthly:,} <span style="font-size:1rem; font-weight:500;">명</span></div>
        <div class="metric-badge">Monthly Avg</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-title">🏥 집계 지점수</div>
        <div class="metric-value">{active_branches} <span style="font-size:1rem; font-weight:500;">개소</span></div>
        <div class="metric-badge">Active Clinics</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ----------------- 그래프 테마 및 팔레트 (사진과 유사한 모던 파스텔 톤) -----------------
COLOR_PALETTE = ["#4f46e5", "#818cf8", "#fb7185", "#f43f5e", "#fbbf24", "#38bdf8"]

chart_layout_base = dict(
    paper_bgcolor="rgba(255,255,255,1)",
    plot_bgcolor="rgba(255,255,255,1)",
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(family="sans-serif", color="#475569"),
    xaxis=dict(showgrid=False, linecolor="#f1f5f9"),
    yaxis=dict(showgrid=True, gridcolor="#f1f5f9", linecolor="#f1f5f9"),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
    ),
)

# ----------------- 대시보드 차트 2단 레이아웃 -----------------
c_left, c_right = st.columns([1.6, 1])

with c_left:
    # 1. 월별 성장 곡선 (부드러운 곡선 차트)
    if selected_branch == "전지점(통합)":
        trend_df = (
            filtered_df.groupby(["년월", "지점명"])["신환수"]
            .sum()
            .reset_index()
        )
        fig_trend = px.line(
            trend_df,
            x="년월",
            y="신환수",
            color="지점명",
            color_discrete_sequence=COLOR_PALETTE,
            title="<b>지점별 월간 신환 유치 추이</b>",
            markers=True,
        )
    else:
        trend_df = filtered_df.groupby("년월")["신환수"].sum().reset_index()
        fig_trend = px.area(
            trend_df,
            x="년월",
            y="신환수",
            color_discrete_sequence=["#6366f1"],
            title=f"<b>{selected_branch} 성장 추이</b>",
        )
        fig_trend.update_traces(
            line=dict(width=3, shape="spline"), fillcolor="rgba(99, 102, 241, 0.15)"
        )

    fig_trend.update_layout(**chart_layout_base)
    st.plotly_chart(fig_trend, use_container_width=True)

with c_right:
    # 2. 채널별 유입 비율 (도넛 차트)
    channel_df = (
        filtered_df.groupby("유입경로")["신환수"].sum().reset_index()
    )
    fig_donut = px.pie(
        channel_df,
        names="유입경로",
        values="신환수",
        hole=0.6,
        color_discrete_sequence=COLOR_PALETTE,
        title="<b>유입 채널 믹스</b>",
    )
    fig_donut.update_layout(
        paper_bgcolor="rgba(255,255,255,1)",
        plot_bgcolor="rgba(255,255,255,1)",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# 하단 테이블 뷰
with st.expander("📋 세부 누적 원본 데이터 확인하기"):
    st.dataframe(filtered_df, use_container_width=True)
