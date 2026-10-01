import os
import re
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_FILE = "hospital_analytics.db"

# ----------------- 1. 페이지 설정 & 모던 UI 스타일 -----------------
st.set_page_config(
    page_title="365MC NEW Patient Dashboard",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp {
        background: linear-gradient(135deg, #f6f5fc 0%, #ece8f9 50%, #e3ddfa 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Segoe UI", sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(12px);
        border-right: 1px solid #e2dcfa;
    }
    .metric-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 18px 22px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.06);
        border: 1px solid #f0eef9;
        margin-bottom: 12px;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-title {
        color: #64748b;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #1e1b4b;
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.3;
    }
    .metric-badge {
        display: inline-flex;
        font-size: 0.72rem;
        font-weight: 600;
        color: #4f46e5;
        background: #eef2ff;
        padding: 2px 8px;
        border-radius: 6px;
        width: fit-content;
        margin-top: 6px;
    }
    .top3-item {
        font-size: 0.88rem;
        color: #1e1b4b;
        font-weight: 600;
        margin: 1px 0;
        display: flex;
        justify-content: space-between;
    }
    .top3-rank {
        color: #6366f1;
        font-weight: 700;
        margin-right: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

COLOR_PALETTE = [
    "#4f46e5",
    "#6366f1",
    "#818cf8",
    "#a5b4fc",
    "#fb7185",
    "#f43f5e",
    "#fbbf24",
    "#38bdf8",
]


# ----------------- 2. SQLite DB 초기화 -----------------
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


# ----------------- 3. 엑셀 파서 엔진 (안정성 확보) -----------------
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
                if (
                    branch
                    and branch != "nan"
                    and branch != "지점"
                    and pd.notna(row_vals[2])
                ):
                    try:
                        tot_in = int(row_vals[2])
                        vir_in = int(row_vals[3])
                        ratio = (
                            float(row_vals[4]) if pd.notna(row_vals[4]) else 0.0
                        )
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

        # 헤더 탐색
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

        # 1) 거주 지역
        if region_col is not None and region_col + 1 < df.shape[1]:
            for r in range(header_row_idx + 1, len(df)):
                reg = df.iloc[r, region_col]
                cnt = df.iloc[r, region_col + 1]
                if (
                    pd.notna(reg)
                    and str(reg).strip()
                    and str(reg).strip() != "nan"
                ):
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

        # 2) 전체 유입 경로
        if channel_col is not None and channel_col + 1 < df.shape[1]:
            for r in range(header_row_idx + 1, len(df)):
                ch = df.iloc[r, channel_col]
                cnt = df.iloc[r, channel_col + 1]
                if (
                    pd.notna(ch)
                    and str(ch).strip()
                    and str(ch).strip() != "nan"
                ):
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

        # 3) 바이럴 세부 경로
        if viral_col is not None and viral_col + 1 < df.shape[1]:
            for r in range(header_row_idx + 1, len(df)):
                vch = df.iloc[r, viral_col]
                cnt = df.iloc[r, viral_col + 1]
                if (
                    pd.notna(vch)
                    and str(vch).strip()
                    and str(vch).strip() != "nan"
                ):
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


# ----------------- 4. DB 데이터 조회 -----------------
conn = sqlite3.connect(DB_FILE)
try:
    df_channels = pd.read_sql_query(
        "SELECT DISTINCT * FROM channels", conn
    )
    df_regions = pd.read_sql_query("SELECT DISTINCT * FROM regions", conn)
    df_viral = pd.read_sql_query("SELECT DISTINCT * FROM viral", conn)
    df_vsum = pd.read_sql_query(
        "SELECT DISTINCT * FROM viral_summary", conn
    )
finally:
    conn.close()


# ----------------- 5. 사이드바 구성 (순서 변경 적용) -----------------
with st.sidebar:
    st.markdown("### 🏥 365MC NEW Patient Dashboard")
    st.caption("신환 유입 & 상권 분석 시스템")

    # [수정 1] 상단: 분석 필터
    st.markdown("---")
    st.markdown("#### 🔍 분석 필터")

    if not df_channels.empty:
        periods = sorted(df_channels["기간"].unique().tolist())
        sel_period = st.selectbox("📅 분석 월 선택", periods)

        branches = ["전지점(통합)"] + sorted(
            df_channels[df_channels["기간"] == sel_period]["지점명"]
            .unique()
            .tolist()
        )
        sel_branch = st.selectbox("🎯 지점 선택", branches)
    else:
        sel_period = None
        sel_branch = None
        st.warning("데이터가 없습니다. 아래에서 파일을 업로드해주세요.")

    # [수정 1] 하단: 엑셀 파일 업로드
    st.markdown("---")
    st.markdown("#### 📤 신환조사 엑셀파일 업로드")
    uploaded_files = st.file_uploader(
        "엑셀 파일 (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("데이터 파싱 및 누적 저장", use_container_width=True):
            conn = sqlite3.connect(DB_FILE)
            for file in uploaded_files:
                period_tag = extract_period_from_name(file.name)
                df_r, df_c, df_v, df_vs = parse_hospital_excel(file, period_tag)

                if not df_r.empty:
                    df_r.to_sql(
                        "regions", conn, if_exists="append", index=False
                    )
                if not df_c.empty:
                    df_c.to_sql(
                        "channels", conn, if_exists="append", index=False
                    )
                if not df_v.empty:
                    df_v.to_sql("viral", conn, if_exists="append", index=False)
                if not df_vs.empty:
                    df_vs.to_sql(
                        "viral_summary",
                        conn,
                        if_exists="append",
                        index=False,
                    )
            conn.close()
            st.success("데이터 파싱 및 누적 저장 완료!")
            st.rerun()


# ----------------- 6. 메인 화면 뷰 -----------------
if df_channels.empty:
    st.info(
        "👋 좌측 사이드바 하단에서 `람스 신환조사` 엑셀 파일을 업로드하고 [데이터 파싱 및 누적 저장] 버튼을 눌러주세요."
    )
    st.stop()

# 필터 적용
f_ch = df_channels[df_channels["기간"] == sel_period]
f_reg = df_regions[df_regions["기간"] == sel_period]
f_vir = df_viral[df_viral["기간"] == sel_period]
f_vsum = df_vsum[df_vsum["기간"] == sel_period]

if sel_branch != "전지점(통합)":
    f_ch = f_ch[f_ch["지점명"] == sel_branch]
    f_reg = f_reg[f_reg["지점명"] == sel_branch]
    f_vir = f_vir[f_vir["지점명"] == sel_branch]
    f_vsum = f_vsum[f_vsum["지점명"] == sel_branch]

st.markdown(
    f"<h2 style='color: #1e1b4b; margin-bottom: 0px;'>📈 {sel_branch} 성과 지표 요약</h2>"
    f"<p style='color: #64748b; font-size: 0.95rem; margin-top: 4px;'>분석 기준월: <b>{sel_period}</b></p>",
    unsafe_allow_html=True,
)

# ----------------- 7. 핵심 지표 계산 -----------------
# 3. 총 신환 유입수
total_inflows = f_ch["유입수"].sum() if not f_ch.empty else 0

# 2위 카드: 최대 전환 경로
top_channel = (
    f_ch.groupby("유입경로")["유입수"].sum().idxmax()
    if not f_ch.empty
    else "-"
)

# 5. 바이럴 기여율
viral_rate = (
    round(
        (f_vsum["바이럴유입건수"].sum() / f_vsum["전체유입건수"].sum()) * 100, 1
    )
    if not f_vsum.empty and f_vsum["전체유입건수"].sum() > 0
    else 0.0
)

# 4. 모객 거주지 TOP3 계산
top3_html = ""
if not f_reg.empty:
    top3_reg = (
        f_reg.groupby("거주지역")["신환수"]
        .sum()
        .reset_index()
        .sort_values(by="신환수", ascending=False)
        .head(3)
    )
    for idx, row in enumerate(top3_reg.itertuples(), start=1):
        top3_html += f"""
        <div class="top3-item">
            <span><span class="top3-rank">{idx}위</span> {row.거주지역}</span>
            <span>{row.신환수:,}명</span>
        </div>
        """
else:
    top3_html = "<div style='color:#94a3b8;'>데이터 없음</div>"

# ----------------- 8. 상단 4대 KPI 카드 렌더링 -----------------
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f"""<div class="metric-card">
        <div>
            <div class="metric-title">총 신환 유입수</div>
            <div class="metric-value">{total_inflows:,} <span style="font-size:1rem; font-weight:500;">건</span></div>
        </div>
        <div class="metric-badge">Total Inflow Contacts</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""<div class="metric-card">
        <div>
            <div class="metric-title">최대 유입 채널</div>
            <div class="metric-value" style="font-size:1.35rem; line-height: 1.8rem;">{top_channel}</div>
        </div>
        <div class="metric-badge">Top Performing Channel</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""<div class="metric-card">
        <div>
            <div class="metric-title">바이럴 기여율</div>
            <div class="metric-value">{viral_rate}%</div>
        </div>
        <div class="metric-badge">Blog / SNS Organic</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""<div class="metric-card">
        <div>
            <div class="metric-title">모객 거주지 TOP 3</div>
            {top3_html}
        </div>
        <div class="metric-badge">Top 3 Core Regions</div>
    </div>""",
        unsafe_allow_html=True,
    )

# ----------------- 9. 차트 레이아웃 -----------------
layout_opts = dict(
    paper_bgcolor="rgba(255,255,255,1)",
    plot_bgcolor="rgba(255,255,255,1)",
    margin=dict(l=15, r=15, t=35, b=15),
    font=dict(family="sans-serif", color="#475569"),
    xaxis=dict(showgrid=False, linecolor="#f1f5f9"),
    yaxis=dict(showgrid=True, gridcolor="#f8fafc", linecolor="#f1f5f9"),
)

tab1, tab2, tab3 = st.tabs(
    ["🎯 유입 채널 & 바이럴 심층분석", "🗺️️ 거주지 상권 분석", "📊 지점별 비교 (Rank)"]
)

with tab1:
    c1, c2 = st.columns([1.3, 1])
    with c1:
        ch_sum = (
            f_ch.groupby("유입경로")["유입수"]
            .sum()
            .reset_index()
            .sort_values(by="유입수", ascending=True)
        )
        fig_ch = px.bar(
            ch_sum.tail(12),
            x="유입수",
            y="유입경로",
            orientation="h",
            text_auto=True,
            title="<b>전체 유입경로 Top 12</b>",
            color_discrete_sequence=["#4f46e5"],
        )
        fig_ch.update_layout(**layout_opts)
        st.plotly_chart(fig_ch, use_container_width=True)

    with c2:
        v_sum = (
            f_vir.groupby("바이럴채널")["유입수"]
            .sum()
            .reset_index()
            .sort_values(by="유입수", ascending=False)
        )
        fig_vir = px.pie(
            v_sum,
            names="바이럴채널",
            values="유입수",
            hole=0.6,
            title="<b>바이럴 세부 유입 믹스</b>",
            color_discrete_sequence=COLOR_PALETTE,
        )
        fig_vir.update_layout(
            paper_bgcolor="rgba(255,255,255,1)",
            margin=dict(l=10, r=10, t=35, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
            ),
        )
        st.plotly_chart(fig_vir, use_container_width=True)

with tab2:
    r1, r2 = st.columns([1.2, 1])
    with r1:
        reg_sum = (
            f_reg.groupby("거주지역")["신환수"]
            .sum()
            .reset_index()
            .sort_values(by="신환수", ascending=True)
        )
        fig_reg = px.bar(
            reg_sum.tail(15),
            x="신환수",
            y="거주지역",
            orientation="h",
            text_auto=True,
            title="<b>신환 상위 거주지 (Top 15)</b>",
            color_discrete_sequence=["#fb7185"],
        )
        fig_reg.update_layout(**layout_opts)
        st.plotly_chart(fig_reg, use_container_width=True)

    with r2:
        if not f_reg.empty:
            f_reg_copy = f_reg.copy()
            f_reg_copy["권역분류"] = f_reg_copy["거주지역"].apply(
                lambda x: "서울권"
                if "서울" in str(x)
                else ("경기/인천" if ("경기" in str(x) or "인천" in str(x)) else "기타 지방")
            )
            area_group = (
                f_reg_copy.groupby("권역분류")["신환수"].sum().reset_index()
            )
            fig_area = px.pie(
                area_group,
                names="권역분류",
                values="신환수",
                hole=0.55,
                title="<b>광역 권역별 비중</b>",
                color_discrete_sequence=["#818cf8", "#f43f5e", "#fbbf24"],
            )
            fig_area.update_layout(
                paper_bgcolor="rgba(255,255,255,1)",
                margin=dict(l=10, r=10, t=35, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.15,
                    xanchor="center",
                    x=0.5,
                ),
            )
            st.plotly_chart(fig_area, use_container_width=True)

with tab3:
    if sel_branch == "전지점(통합)":
        sorted_vs = f_vsum.sort_values(by="바이럴비중", ascending=False)
        fig_rank = px.bar(
            sorted_vs,
            x="지점명",
            y="바이럴비중",
            color="바이럴비중",
            color_continuous_scale="Purples",
            text="바이럴비중",
            title="<b>전국 지점 바이럴 유입 비중 (%) 비교</b>",
        )
        fig_rank.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_rank.update_layout(**layout_opts)
        st.plotly_chart(fig_rank, use_container_width=True)

        st.dataframe(
            sorted_vs[
                [
                    "지점명",
                    "전체유입건수",
                    "바이럴유입건수",
                    "바이럴비중",
                ]
            ].reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info("지점별 비교를 보시려면 사이드바에서 [전지점(통합)]을 선택해주세요.")
