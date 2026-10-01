import os
import re
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_FILE = "hospital_analytics.db"

# ----------------- 1. 페이지 설정 & Harvey 스타일 포멀 테마 -----------------
st.set_page_config(
    page_title="365MC NEW Patient Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    .stApp {
        background-color: #fbfbfa;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1a1a1a;
    }

    .formal-title {
        font-family: 'Newsreader', Georgia, serif;
        font-weight: 500;
        font-size: 2.35rem;
        color: #121212;
        letter-spacing: -0.02em;
        margin-bottom: 2px;
    }

    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #242424;
    }
    [data-testid="stSidebar"] * {
        color: #d1d5db !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #262626 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label, 
    [data-testid="stSidebar"] .stFileUploader label {
        color: #9ca3af !important;
        font-size: 0.82rem;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #f3f4f6 !important;
        border-radius: 8px;
    }

    .metric-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03), 0 1px 2px rgba(0, 0, 0, 0.02);
        border: 1px solid #e7e5e4;
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-title {
        color: #71717a;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .metric-value {
        font-family: 'Newsreader', Georgia, serif;
        color: #18181b;
        font-size: 2.1rem;
        font-weight: 500;
        line-height: 1.15;
    }
    .metric-badge {
        display: inline-flex;
        font-size: 0.72rem;
        font-weight: 500;
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
        gap: 4px;
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
        font-weight: 600;
        margin-right: 6px;
        font-size: 0.8rem;
    }
    .top3-name {
        font-weight: 500;
        color: #27272a;
    }
    .top3-count {
        font-weight: 600;
        color: #09090b;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #e5e5e5;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.9rem;
        font-weight: 500;
        color: #71717a;
        padding: 10px 4px;
    }
    .stTabs [aria-selected="true"] {
        color: #09090b !important;
        font-weight: 600;
        border-bottom-color: #09090b !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

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


# ----------------- 3. 안전한 엑셀 파서 엔진 -----------------
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


# ----------------- 4. DB 데이터 로드 -----------------
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

# ----------------- 5. 사이드바 -----------------
with st.sidebar:
    st.markdown(
        "<div style='padding: 6px 0 16px 0;'>"
        "<div style='font-family:Newsreader, serif; font-size:1.35rem; font-weight:500; color:#ffffff;'>365MC Intelligence</div>"
        "<div style='font-size:0.75rem; color:#71717a;'>Enterprise Command Center</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<p style='font-size:0.75rem; color:#a1a1aa; font-weight:600; text-transform:uppercase; margin-bottom:8px;'>Parameters</p>", unsafe_allow_html=True)
    if not df_channels.empty:
        periods = sorted(df_channels["기간"].unique().tolist())
        sel_period = st.selectbox("분석 기간 (DATE RANGE)", periods)

        branches = ["전지점(통합)"] + sorted(
            df_channels[df_channels["기간"] == sel_period]["지점명"]
            .unique()
            .tolist()
        )
        sel_branch = st.selectbox("지점 (BRANCH OFFICE)", branches)
    else:
        sel_period, sel_branch = None, None
        st.caption("누적된 데이터베이스가 없습니다.")

    st.markdown("<div style='height: 40px;'></div><hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

    st.markdown("<p style='font-size:0.75rem; color:#a1a1aa; font-weight:600; text-transform:uppercase; margin-bottom:8px;'>Data Ingestion</p>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "신환 조사 엑셀 로드 (.XLSX)",
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
            st.success("데이터베이스 동기화 완료")
            st.rerun()

# ----------------- 6. 메인 화면 레이아웃 -----------------
if df_channels.empty:
    st.markdown(
        "<div style='padding: 60px 0; text-align: center;'>"
        "<h2 class='formal-title'>365MC NEW Patient Command Center</h2>"
        "<p style='color: #71717a;'>좌측 하단의 Data Ingestion 패널에서 조사 엑셀 파일을 업로드해 주십시오.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# 필터링
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
    f"""
    <div style="margin-bottom: 24px;">
        <div class="formal-title">Whitford Lanes Command Center — {sel_branch}</div>
        <div style="color: #71717a; font-size: 0.9rem; margin-top: 4px;">
            Target Cycle: <b>{sel_period}</b> &nbsp;|&nbsp; Status: Verified Data Source
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- 7. 지표 계산 및 KPI 카드 렌더링 -----------------
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

# TOP 3 거주지 HTML 구성 (들여쓰기 제거로 마크다운 코드블록 오인 방지)
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
            f'<div><span class="top3-rank">{idx}</span><span class="top3-name">{row.거주지역}</span></div>'
            f'<div class="top3-count">{row.신환수:,}명</div>'
            f'</div>'
        )
    top3_content = '<div class="top3-container">' + "".join(rows_list) + '</div>'
else:
    top3_content = "<div style='color:#a1a1aa; font-size:0.85rem;'>기록 없음</div>"

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">총 신환 유입수</div>'
        f'<div class="metric-value">{total_inflows:,} <span style="font-size:1.1rem; font-family:\'Plus Jakarta Sans\'; font-weight:400; color:#71717a;">건</span></div>'
        f'<div class="metric-badge">Gross Inflows</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">최대 유입 채널</div>'
        f'<div class="metric-value" style="font-size:1.45rem; line-height:1.2; padding-top:6px;">{top_channel}</div>'
        f'<div class="metric-badge">Primary Channel</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">바이럴 기여율</div>'
        f'<div class="metric-value">{viral_rate}<span style="font-size:1.3rem;">%</span></div>'
        f'<div class="metric-badge">Organic & SNS</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

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

# ----------------- 8. Harvey 스타일 모노톤 차트 테마 (오류 수정 완료) -----------------
FORMAL_COLORS = ["#18181b", "#3f3f46", "#71717a", "#a1a1aa", "#d4d4d8", "#e4e4e7"]

# linecolor='transparent' 제거 -> showline=False 로 수정하여 ValueError 해결
formal_layout = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    margin=dict(l=20, r=20, t=45, b=20),
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#3f3f46", size=12),
    title=dict(
        font=dict(family="Newsreader, serif", size=17, color="#18181b")
    ),
    xaxis=dict(
        showgrid=False,
        showline=True,
        linecolor="#e4e4e7",
        tickcolor="#e4e4e7",
        tickfont=dict(size=11, color="#71717a"),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#f4f4f5",
        showline=False,
        tickfont=dict(size=11, color="#71717a"),
    ),
)

# ----------------- 9. 탭별 분석 뷰 -----------------
tab1, tab2, tab3 = st.tabs(
    ["유입 경로 분석 (Channels)", "배후 상권 분석 (Demographics)", "지점 벤치마크 (Benchmark)"]
)

with tab1:
    c1, c2 = st.columns([1.4, 1])
    with c1:
        ch_sum = (
            f_ch.groupby("유입경로")["유입수"]
            .sum()
            .reset_index()
            .sort_values(by="유입수", ascending=True)
        )
        fig_ch = px.bar(
            ch_sum.tail(10),
            x="유입수",
            y="유입경로",
            orientation="h",
            text_auto=True,
            title="Channel Attribution (Top 10 Channels)",
            color_discrete_sequence=["#27272a"],
        )
        fig_ch.update_layout(**formal_layout)
        fig_ch.update_traces(marker_line_width=0, opacity=0.9)
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
            hole=0.68,
            title="Viral Inflow Breakdown",
            color_discrete_sequence=FORMAL_COLORS,
        )
        fig_vir.update_layout(
            paper_bgcolor="#ffffff",
            margin=dict(l=10, r=10, t=45, b=10),
            font=dict(family="Plus Jakarta Sans", color="#52525b"),
            title=dict(
                font=dict(family="Newsreader, serif", size=17, color="#18181b")
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
            ),
        )
        st.plotly_chart(fig_vir, use_container_width=True)

with tab2:
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
            title="Patient Geographic Origins (Top 12)",
            color_discrete_sequence=["#52525b"],
        )
        fig_reg.update_layout(**formal_layout)
        fig_reg.update_traces(marker_line_width=0)
        st.plotly_chart(fig_reg, use_container_width=True)

    with r2:
        if not f_reg.empty:
            f_reg_copy = f_reg.copy()
            f_reg_copy["권역분류"] = f_reg_copy["거주지역"].apply(
                lambda x: "서울권"
                if "서울" in str(x)
                else ("경기/인천" if ("경기" in str(x) or "인천" in str(x)) else "지방/기타")
            )
            area_group = (
                f_reg_copy.groupby("권역분류")["신환수"].sum().reset_index()
            )
            fig_area = px.pie(
                area_group,
                names="권역분류",
                values="신환수",
                hole=0.68,
                title="Regional Proportions",
                color_discrete_sequence=["#18181b", "#71717a", "#d4d4d8"],
            )
            fig_area.update_layout(
                paper_bgcolor="#ffffff",
                margin=dict(l=10, r=10, t=45, b=10),
                font=dict(family="Plus Jakarta Sans", color="#52525b"),
                title=dict(
                    font=dict(family="Newsreader, serif", size=17, color="#18181b")
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
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
            title="Branch Viral Contribution Comparison (%)",
            color="바이럴비중",
            color_continuous_scale=["#a1a1aa", "#27272a"],
            text="바이럴비중",
        )
        fig_rank.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_rank.update_layout(**formal_layout)
        fig_rank.update_coloraxes(showscale=False)
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
        st.info("지점 간 비교를 진행하려면 좌측 상단 필터에서 [전지점(통합)]을 지정하십시오.")
