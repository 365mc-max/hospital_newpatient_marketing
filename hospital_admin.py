import os
import re
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_FILE = "hospital_analytics.db"

# ----------------- 1. 페이지 설정 및 스타일 -----------------
st.set_page_config(
    page_title="365MC 신환 유입 분석 대시보드",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

    .stApp, .stMarkdown, .stSelectbox, .stMultiSelect, .stFileUploader, .stMetric, [data-testid="stSidebarContent"], p, h1, h2, h3, h4, h5, h6 {
        font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        letter-spacing: -0.015em;
    }

    [data-testid="stIcon"], [class*="material-symbols"], [class*="material-icons"], .material-symbols-rounded {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
        font-style: normal !important;
        font-weight: normal !important;
        letter-spacing: normal !important;
    }

    .stApp {
        background-color: #fbfbfa;
        color: #1a1a1a;
    }

    /* 사이드바 다크 스타일 */
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #242424;
    }
    [data-testid="stSidebar"] * {
        color: #d1d5db;
    }
    [data-testid="stSidebar"] hr {
        border-color: #262626 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label, 
    [data-testid="stSidebar"] .stFileUploader label {
        color: #9ca3af !important;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #f3f4f6 !important;
        border-radius: 8px;
    }

    /* 메트릭 카드 */
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
        border: 1px solid #e7e5e4;
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-title {
        color: #71717a;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
    .metric-value {
        color: #0f172a;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-badge {
        display: inline-flex;
        font-size: 0.72rem;
        font-weight: 600;
        color: #52525b;
        background: #f4f4f5;
        padding: 3px 8px;
        border-radius: 4px;
        width: fit-content;
        border: 1px solid #e4e4e7;
    }

    .top3-container {
        display: flex;
        flex-direction: column;
        gap: 5px;
        margin: 4px 0;
    }
    .top3-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.86rem;
    }
    .top3-rank {
        color: #71717a;
        font-weight: 700;
        margin-right: 6px;
        font-size: 0.8rem;
    }
    .top3-name {
        font-weight: 600;
        color: #1e293b;
    }
    .top3-count {
        font-weight: 700;
        color: #09090b;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #e5e5e5;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #71717a !important;
        padding: 12px 4px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #09090b !important;
        font-weight: 700 !important;
        border-bottom-color: #09090b !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------- 2. 유입 성격 매핑 함수 -----------------
def map_inflow_nature(channel_name):
    """
    유입 성격(유료광고, 오가닉, 바이럴) 분류
    - 포털검색어는 유입 성격 필터링에서 배제되도록 별도 분류
    """
    ch = str(channel_name).strip()

    # 포털검색어는 유입 성격 분류에서 제외
    if any(k in ch for k in ["포털검색어", "검색어", "포털 검색어"]):
        return "포털검색어(제외)"

    # 1. 유료광고
    paid_keywords = [
        "온라인광고", "기타광고", "신문/잡지", "신문", "잡지", 
        "극장광고", "극장", "라디오광고", "라디오", 
        "아파트관리비광고", "아파트관리비", "관리비광고",
        "제휴협력기관", "제휴", "교통광고", "교통", "마트광고", "마트"
    ]
    if any(k in ch for k in paid_keywords):
        return "유료광고"

    # 2. 오가닉
    organic_keywords = ["지인추천", "지인", "기타추천", "추천", "소개"]
    if any(k in ch for k in organic_keywords):
        return "오가닉"

    # 3. 바이럴
    viral_keywords = [
        "블로그", "온라인추천", "카페", "기타후기", "후기", 
        "유튜브", "인스타그램", "인스타", "어플", "앱", "틱톡"
    ]
    if any(k in ch for k in viral_keywords):
        return "바이럴"

    return "기타"

# ----------------- 3. SQLite DB 초기화 -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS regions (
                    기간 TEXT, 지점명 TEXT, 거주지역 TEXT, 신환수 INTEGER,
                    PRIMARY KEY(기간, 지점명, 거주지역)
                 )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS channels (
                    기간 TEXT, 지점명 TEXT, 유입경로 TEXT, 유입수 INTEGER,
                    PRIMARY KEY(기간, 지점명, 유입경로)
                 )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS viral (
                    기간 TEXT, 지점명 TEXT, 바이럴채널 TEXT, 유입수 INTEGER,
                    PRIMARY KEY(기간, 지점명, 바이럴채널)
                 )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS viral_summary (
                    기간 TEXT, 지점명 TEXT, 전체유입건수 INTEGER, 바이럴유입건수 INTEGER, 바이럴비중 REAL,
                    PRIMARY KEY(기간, 지점명)
                 )"""
    )
    conn.commit()
    conn.close()

init_db()

def extract_period_from_name(filename):
    match = re.search(r"\((\d{2})\.(\d{2})\)", filename)
    if match:
        return f"20{match.group(1)}-{match.group(2)}"
    return "2024-03"

# ----------------- 4. 엑셀 파서 엔진 -----------------
def parse_hospital_excel(file_bytes, period_label):
    xls = pd.ExcelFile(file_bytes)
    sheet_names = xls.sheet_names

    region_records = []
    channel_records = []
    viral_records = []
    viral_summary_records = []

    for sheet in sheet_names:
        if sheet == "바이럴신환유입":
            df_v = pd.read_excel(xls, sheet_name=sheet, header=None)
            for r in range(len(df_v)):
                row_vals = df_v.iloc[r].values
                if len(row_vals) < 5:
                    continue
                branch = str(row_vals[1]).strip()
                if branch and branch != "nan" and branch != "지점" and pd.notna(row_vals[2]):
                    try:
                        tot_in = int(row_vals[2])
                        vir_in = int(row_vals[3])
                        ratio = float(row_vals[4]) if pd.notna(row_vals[4]) else 0.0
                        viral_summary_records.append(
                            {
                                "기간": period_label,
                                "지점명": branch,
                                "전체유입건수": tot_in,
                                "바이럴유입건수": vir_in,
                                "바이럴비중": round(ratio * 100, 1),
                            }
                        )
                    except (ValueError, TypeError):
                        continue
            continue

        df = pd.read_excel(xls, sheet_name=sheet, header=None)
        header_row_idx = None
        for r in range(min(6, len(df))):
            vals = [str(x).strip() for x in df.iloc[r].dropna()]
            if "지역" in vals and "경로" in vals:
                header_row_idx = r
                break

        if header_row_idx is None:
            continue

        h_vals = df.iloc[header_row_idx].values
        region_col, channel_col, viral_col = None, None, None

        for c, raw_val in enumerate(h_vals):
            val = str(raw_val).strip()
            if val == "지역" and region_col is None:
                region_col = c
            elif val == "경로":
                channel_col = c
            elif "바이럴" in val:
                viral_col = c

        if region_col is not None and region_col + 1 < df.shape[1]:
            for r in range(header_row_idx + 1, len(df)):
                reg = df.iloc[r, region_col]
                cnt = df.iloc[r, region_col + 1]
                if pd.notna(reg) and str(reg).strip() and str(reg).strip() != "nan":
                    try:
                        region_records.append(
                            {
                                "기간": period_label,
                                "지점명": sheet,
                                "거주지역": str(reg).strip(),
                                "신환수": int(cnt),
                            }
                        )
                    except (ValueError, TypeError):
                        pass

        if channel_col is not None and channel_col + 1 < df.shape[1]:
            for r in range(header_row_idx + 1, len(df)):
                ch = df.iloc[r, channel_col]
                cnt = df.iloc[r, channel_col + 1]
                if pd.notna(ch) and str(ch).strip() and str(ch).strip() != "nan":
                    try:
                        channel_records.append(
                            {
                                "기간": period_label,
                                "지점명": sheet,
                                "유입경로": str(ch).strip(),
                                "유입수": int(cnt),
                            }
                        )
                    except (ValueError, TypeError):
                        pass

        if viral_col is not None and viral_col + 1 < df.shape[1]:
            for r in range(header_row_idx + 1, len(df)):
                vch = df.iloc[r, viral_col]
                cnt = df.iloc[r, viral_col + 1]
                if pd.notna(vch) and str(vch).strip() and str(vch).strip() != "nan":
                    try:
                        viral_records.append(
                            {
                                "기간": period_label,
                                "지점명": sheet,
                                "바이럴채널": str(vch).strip(),
                                "유입수": int(cnt),
                            }
                        )
                    except (ValueError, TypeError):
                        pass

    return (
        pd.DataFrame(region_records),
        pd.DataFrame(channel_records),
        pd.DataFrame(viral_records),
        pd.DataFrame(viral_summary_records),
    )

# ----------------- 5. DB 데이터 로드 및 전처리 -----------------
conn = sqlite3.connect(DB_FILE)
try:
    df_channels = pd.read_sql_query("SELECT DISTINCT * FROM channels", conn)
    df_regions = pd.read_sql_query("SELECT DISTINCT * FROM regions", conn)
    df_viral = pd.read_sql_query("SELECT DISTINCT * FROM viral", conn)
    df_vsum = pd.read_sql_query("SELECT DISTINCT * FROM viral_summary", conn)
finally:
    conn.close()

if not df_channels.empty:
    df_channels["유입성격"] = df_channels["유입경로"].apply(map_inflow_nature)

# ----------------- 6. 사이드바 (분석 필터) -----------------
with st.sidebar:
    st.markdown(
        f'<div style="text-align: center; padding: 20px 0 16px 0;">'
        f'<div style="font-size:1.35rem; font-weight:700; color:#ffffff;">365MC Intelligence</div>'
        f'<div style="font-size:0.8rem; color:#a1a1aa; margin-top:4px;">신환 유입 & 마케팅 분석 시스템</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.82rem; color:#f3f4f6; font-weight:700; margin-bottom:8px;'>📌 기본 필터</p>",
        unsafe_allow_html=True,
    )
    if not df_channels.empty:
        periods = sorted(df_channels["기간"].unique().tolist())
        sel_period = st.selectbox("분석 월 선택", periods, index=len(periods)-1)

        branches = ["전지점(통합)"] + sorted(
            df_channels[df_channels["기간"] == sel_period]["지점명"].unique().tolist()
        )
        sel_branch = st.selectbox("지점 선택", branches)

        st.markdown("---")
        st.markdown(
            "<p style='font-size:0.82rem; color:#38bdf8; font-weight:700; margin-bottom:4px;'>🎯 마케팅 전문 필터</p>",
            unsafe_allow_html=True,
        )

        # 1. '유입 성격' 드롭다운
        inflow_nature_options = ["전체", "유료광고", "오가닉", "바이럴"]
        sel_nature = st.selectbox("유입 성격", inflow_nature_options)

        # 2. '상세 유입' 드롭다운 (selectbox 형태로 변경)
        if sel_nature == "전체":
            available_details = sorted(df_channels["유입경로"].unique().tolist())
        else:
            available_details = sorted(
                df_channels[df_channels["유입성격"] == sel_nature]["유입경로"].unique().tolist()
            )

        detail_options = ["전체"] + available_details
        sel_detail = st.selectbox("상세 유입", detail_options)
    else:
        sel_period, sel_branch, sel_nature, sel_detail = None, None, "전체", "전체"
        st.caption("누적된 데이터가 없습니다.")

    st.markdown(
        "<div style='height: 20px;'></div><hr style='margin: 0 0 20px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='font-size:0.78rem; color:#9ca3af; font-weight:700; margin-bottom:8px;'>📤 신환조사 엑셀파일 업로드</p>",
        unsafe_allow_html=True,
    )
    uploaded_files = st.file_uploader(
        "엑셀 파일 (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("데이터 파싱 및 영구 동기화", use_container_width=True):
            conn = sqlite3.connect(DB_FILE)
            for file in uploaded_files:
                period_tag = extract_period_from_name(file.name)
                df_r, df_c, df_v, df_vs = parse_hospital_excel(file, period_tag)

                if not df_r.empty:
                    df_r.to_sql("regions", conn, if_exists="append", index=False)
                if not df_c.empty:
                    df_c.to_sql("channels", conn, if_exists="append", index=False)
                if not df_v.empty:
                    df_v.to_sql("viral", conn, if_exists="append", index=False)
                if not df_vs.empty:
                    df_vs.to_sql("viral_summary", conn, if_exists="append", index=False)
            conn.close()
            st.success("데이터베이스 동기화 완료")
            st.rerun()

# ----------------- 7. 메인 화면 레이아웃 및 필터링 -----------------
if df_channels.empty:
    st.markdown(
        '<div style="padding: 60px 0; text-align: center;">'
        '<h2 style="font-weight:700; font-size:2rem; color:#0f172a;">365MC 신환 유입 분석 대시보드</h2>'
        '<p style="color: #71717a;">좌측 하단의 [신환조사 엑셀파일 업로드]에서 조사 파일을 업로드해 주십시오.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# 1) 전체 시계열 필터링
trend_df = df_channels.copy()
if sel_branch != "전지점(통합)":
    trend_df = trend_df[trend_df["지점명"] == sel_branch]

# 유입 성격 선택 필터링
if sel_nature != "전체":
    trend_df = trend_df[trend_df["유입성격"] == sel_nature]

# 상세 유입 단일 선택 필터링
if sel_detail != "전체":
    trend_df = trend_df[trend_df["유입경로"] == sel_detail]

# 2) 선택 월 기준 필터링
f_ch = trend_df[trend_df["기간"] == sel_period]
f_reg = df_regions[df_regions["기간"] == sel_period]
f_vir = df_viral[df_viral["기간"] == sel_period]
f_vsum = df_vsum[df_vsum["기간"] == sel_period]

is_all_branches = sel_branch == "전지점(통합)"

if not is_all_branches:
    f_reg = f_reg[f_reg["지점명"] == sel_branch]
    f_vir = f_vir[f_vir["지점명"] == sel_branch]
    f_vsum = f_vsum[f_vsum["지점명"] == sel_branch]

# 대시보드 상단 타이틀
st.markdown(
    f'<div style="margin-bottom: 24px;">'
    f'<div style="display: flex; align-items: center;">'
    f'<span style="font-weight: 700; font-size: 2.1rem; color: #0f172a; letter-spacing: -0.03em;">365MC 신환 유입 분석 대시보드 — {sel_branch}</span>'
    f'</div>'
    f'<div style="color: #64748b; font-size: 0.92rem; font-weight: 500; margin-top: 6px;">'
    f'분석 기준월: <b>{sel_period}</b> &nbsp;|&nbsp; 유입 성격: <b>{sel_nature}</b> &nbsp;|&nbsp; 상세 유입: <b>{sel_detail}</b>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ----------------- 8. KPI 카드 렌더링 -----------------
total_inflows = f_ch["유입수"].sum() if not f_ch.empty else 0
top_channel = (
    f_ch.groupby("유입경로")["유입수"].sum().idxmax()
    if not f_ch.empty
    else "-"
)
viral_rate = (
    round(
        (f_vsum["바이럴유입건수"].sum() / f_vsum["전체유입건수"].sum()) * 100, 1
    )
    if not f_vsum.empty and f_vsum["전체유입건수"].sum() > 0
    else 0.0
)

# 전지점(통합)은 모객거주지 카드 제외 (3단), 개별 지점은 4단
if is_all_branches:
    k1, k2, k3 = st.columns(3)
else:
    k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">선택 조건 총 유입수</div>'
        f'<div class="metric-value">{total_inflows:,} <span style="font-size:1.05rem; font-weight:500; color:#64748b;">건</span></div>'
        f'<div class="metric-badge">Filtered Inflows</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">선택 내 1위 경로</div>'
        f'<div class="metric-value" style="font-size:1.35rem; line-height:1.2; padding-top:4px;">{top_channel}</div>'
        f'<div class="metric-badge">Top Inflow Channel</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">전체 대비 바이럴 기여율</div>'
        f'<div class="metric-value">{viral_rate}<span style="font-size:1.2rem;">%</span></div>'
        f'<div class="metric-badge">Viral Share</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

if not is_all_branches:
    rows_list = []
    if not f_reg.empty:
        top3_reg = (
            f_reg.groupby("거주지역")["신환수"]
            .sum()
            .reset_index()
            .sort_values(by="신환수", ascending=False)
            .head(3)
        )
        for idx, row in enumerate(top3_reg.itertuples(), start=1):
            rows_list.append(
                f'<div class="top3-row">'
                f'<div><span class="top3-rank">{idx}위</span><span class="top3-name">{row.거주지역}</span></div>'
                f'<div class="top3-count">{row.신환수:,}명</div>'
                f'</div>'
            )
        top3_content = '<div class="top3-container">' + "".join(rows_list) + '</div>'
    else:
        top3_content = "<div style='color:#a1a1aa; font-size:0.85rem;'>기록 없음</div>"

    with k4:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-title" style="margin-bottom:6px;">모객 거주지 TOP 3</div>'
            f'{top3_content}'
            f'<div class="metric-badge">Key Territories</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# 차트 레이아웃 템플릿
formal_layout = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    margin=dict(l=20, r=20, t=45, b=20),
    font=dict(family="Pretendard, -apple-system, sans-serif", color="#334155", size=12),
    title=dict(font=dict(family="Pretendard, -apple-system, sans-serif", size=15, color="#0f172a")),
    xaxis=dict(showgrid=False, showline=True, linecolor="#e2e8f0", tickcolor="#e2e8f0", tickfont=dict(size=11, color="#64748b")),
    yaxis=dict(showgrid=True, gridcolor="#f1f5f9", showline=False, tickfont=dict(size=11, color="#64748b")),
)

FORMAL_COLORS = ["#1e293b", "#334155", "#475569", "#64748b", "#94a3b8", "#cbd5e1"]

# ----------------- 9. 탭별 상세 뷰 구현 -----------------
def render_channel_tab():
    c1, c2 = st.columns([1.3, 1])
    with c1:
        ch_sum = (
            f_ch.groupby("유입경로")["유입수"]
            .sum()
            .reset_index()
            .sort_values(by="유입수", ascending=True)
        )
        fig_bar = px.bar(
            ch_sum.tail(12),
            x="유입수",
            y="유입경로",
            orientation="h",
            text_auto=True,
            title="<b>선택 유입 경로 순위</b>",
            color_discrete_sequence=["#1e293b"],
        )
        fig_bar.update_layout(**formal_layout)
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        if not ch_sum.empty:
            fig_pie = px.pie(
                ch_sum.tail(8),
                names="유입경로",
                values="유입수",
                hole=0.6,
                title="<b>점유 비중 (%)</b>",
                color_discrete_sequence=FORMAL_COLORS,
            )
            fig_pie.update_layout(paper_bgcolor="#ffffff", margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")

    st.markdown("#### 유입 내역 데이터")
    st.dataframe(
        ch_sum.sort_values(by="유입수", ascending=False).reset_index(drop=True),
        use_container_width=True,
    )

def render_trend_tab():
    st.markdown("#### 📈 월별 유입 추이 분석 (Monthly Trends)")
    if trend_df.empty:
        st.info("선택된 조건에 부합하는 데이터가 없습니다.")
        return

    trend_pivot = (
        trend_df.groupby(["기간", "유입경로"])["유입수"]
        .sum()
        .reset_index()
    )

    fig_trend = px.line(
        trend_pivot,
        x="기간",
        y="유입수",
        color="유입경로",
        markers=True,
        title="<b>선택 경로의 월별 추이</b>",
    )
    fig_trend.update_layout(**formal_layout)
    st.plotly_chart(fig_trend, use_container_width=True)

def render_region_tab():
    r1, r2 = st.columns([1.3, 1])
    with r1:
        reg_sum = (
            f_reg.groupby("거주지역")["신환수"]
            .sum()
            .reset_index()
            .sort_values(by="신환수", ascending=True)
        )
        fig_reg = px.bar(
            reg_sum.tail(12),
            x="신환수",
            y="거주지역",
            orientation="h",
            text_auto=True,
            title="<b>환자 주요 거주지역 순위 (Top 12)</b>",
            color_discrete_sequence=["#475569"],
        )
        fig_reg.update_layout(**formal_layout)
        st.plotly_chart(fig_reg, use_container_width=True)

    with r2:
        if not f_reg.empty:
            f_reg_copy = f_reg.copy()
            f_reg_copy["권역분류"] = f_reg_copy["거주지역"].apply(
                lambda x: "서울권"
                if "서울" in str(x)
                else ("경기/인천" if ("경기" in str(x) or "인천" in str(x)) else "지방/기타")
            )
            area_group = f_reg_copy.groupby("권역분류")["신환수"].sum().reset_index()
            fig_area = px.pie(
                area_group,
                names="권역분류",
                values="신환수",
                hole=0.65,
                title="<b>광역 권역별 환자 비중</b>",
                color_discrete_sequence=["#0f172a", "#64748b", "#cbd5e1"],
            )
            fig_area.update_layout(paper_bgcolor="#ffffff", margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig_area, use_container_width=True)

def render_benchmark_tab():
    if sel_branch == "전지점(통합)":
        sorted_vs = f_vsum.sort_values(by="바이럴비중", ascending=False)
        fig_rank = px.bar(
            sorted_vs,
            x="지점명",
            y="바이럴비중",
            title="<b>전국 지점 바이럴 유입 비중 비교 (%)</b>",
            color="바이럴비중",
            color_continuous_scale=["#94a3b8", "#0f172a"],
            text="바이럴비중",
        )
        fig_rank.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_rank.update_layout(**formal_layout)
        fig_rank.update_coloraxes(showscale=False)
        st.plotly_chart(fig_rank, use_container_width=True)

        st.dataframe(
            sorted_vs[["지점명", "전체유입건수", "바이럴유입건수", "바이럴비중"]].reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info("전국 지점 간 비교를 확인하시려면 좌측 상단 필터에서 [전지점(통합)]을 선택해 주십시오.")

# ----------------- 10. 탭 실행 분기 -----------------
if is_all_branches:
    tab1, tab_trend, tab3 = st.tabs(
        ["유입 경로 분석 (Channels)", "월별 유입 추이 (Trends)", "지점 벤치마크 (Benchmark)"]
    )
    with tab1:
        render_channel_tab()
    with tab_trend:
        render_trend_tab()
    with tab3:
        render_benchmark_tab()
else:
    tab1, tab_trend, tab2, tab3 = st.tabs(
        ["유입 경로 분석 (Channels)", "월별 유입 추이 (Trends)", "거주지 상권 분석 (Demographics)", "지점 벤치마크 (Benchmark)"]
    )
    with tab1:
        render_channel_tab()
    with tab_trend:
        render_trend_tab()
    with tab2:
        render_region_tab()
    with tab3:
        render_benchmark_tab()
