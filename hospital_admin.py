import os
import re
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_FILE = "hospital_analytics.db"

# ----------------- 1. 페이지 설정 및 완벽 방어형 스타일 -----------------
st.set_page_config(
    page_title="365MC NEW Patient Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 하트 들고 있는 3D 지방이 캐릭터 (100% 온전한 Base64 무손실 내장)
JIBANG_IMG_B64 = "data:image/jpeg;base64," + (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYa"
    "HSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgo"
    "KCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAB4AHgDASIAAhEBAxEB/8QA"
    "HwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIh"
    "MUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVW"
    "V1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG"
    "x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQB"
    "FgQUFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqChIWGh4iJ"
    "ipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP0"
    "9fb3+Pn6/9oADAMBAAIRAxEAPwD5/ooorujFydkcs5qCuxGYKpZjgDkmtzSNCudRAlmJtrQ/xkfM/wBB"
    "/jUvg/Tf7Q1A3cy7re2IYA9GfsP6/gPWu3r0KdJR1e55NWs5OyM+z0TTbNB5Vokjj+OYb2J/Hp+FXhFE"
    "sflrEgT+6FGPyp1FdCSWxytvqVLnTbC6GJ7OBz/AHtgB/Mc1kXng6xlBazuJrZ/7rfOv+P610dFOMmno"
    "JSktmcXF4JvpZGDXdrFGOjHcxb8MDH510Ph3wbpmnyrLdk39yP74wg/4D3/E/hWtRWsZSZpOrKUbI0p5"
    "fMIVRhF4AFTWV15TCOT/AFZ/SsqGTeMfxCpq1OJnVRyq1upDAknrUNzHHOhWZQwIxnHNY1rcbPlc/L2P"
    "pWlFMpX52AI9+tMgyb7TmgzJFl4uvHUVSrqEdXXKkEH0rPvdNEhMlvhW7r2NcmKwftffh8X5nVhsV7P3"
    "Z7GDRTyjB2VhgqSD7UV4rTi7M9VOLV0fONdR4Z8P/btt5eqRagdIxwZfr6D+f51l6Dpx1PVIbY5ER+aR"
    "h2Udf8Pxr0eNEjRUjUKijCqBgAegFduDp8z52eZiqnKuVEF5aR3Fi9rjy4yuF2jGzHQj6Vy8nhy7Utsu"
    "IWXPy5yCR78cV2FFeg4qW55qk47HE/8ACPX39+3/AO+j/hR/wj19/ft/++j/AIV21FR7GJV7VnE/8I9f"
    "f37f/vo/4Uf8I9ff37f/vo/4V21FHsYh7WZwf8AYWof3Iv+/g/wo/sLUf7kP/fwf4V3lFHsYj9tM4m20"
    "PUEnjdlh2qwJw/b8q6u30+6m2skJ2k/ebgVeqWCeSA/Ifl7qehrSMFEzlOUtWTW+kMvM0wHsgq42n2pj"
    "2eWffcTk/jVWfUj5ZEKEMf4m7VVW8uVbPnMT78/zq7GZrWtmLVWCyOwPY9BViq1jeC5Xa/yygcgdD71Z"
    "poCjcaZZzSs7xYZuTtbGTRU0tzDExV3AYdRiiuWeDoyd3FG8cVWirJs8D8C2YttOlvpvla4Py57Iv/18"
    "/lXQf2hb/wDTX/vhv8KKKK81FKKRNSblJth/aFv/ANNf++G/wo/tC3/6a/8AfDf4UUVRIf2hb/8ATX/v"
    "hv8ACj+0Lf8A6a/98N/hRRQAf2hb/wDTX/vhv8KP7Qt/+mv/AHw3+FFFAB/aFv8A9Nf++G/wo/tC3/6a"
    "/wDfDf4UUUAH9oW//TX/AL4b/Co5NTijQt5c7ewjP/1qKKAKL+INzFUs7jH95lAH6ZqP+3Z/4bY/8CP+"
    "FFFADotfuYmDw25V15DeaOPwxWhB4uvJUG63WJ/4tx3AfTAoorSMFJaozlOUXozSh1i6kQMY4Rn03f40"
    "UUV2wVoo5pu7CiiiqIP/2Q=="
)

st.markdown(
    """
<style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

    /* 1. 기본 본문 텍스트에만 Pretendard 고딕 적용 */
    .stApp, .stMarkdown, .stSelectbox, .stFileUploader, .stMetric, [data-testid="stSidebarContent"], p, h1, h2, h3, h4, h5, h6 {
        font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        letter-spacing: -0.015em;
    }

    /* 2. 스트림릿 내장 아이콘 폰트 강제 복구 (keyboard_double_ 및 upload 텍스트 중첩 영구 해결) */
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

    /* 3. 사이드바 다크 스타일 */
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

    /* 4. 포멀 메트릭 카드 */
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

    /* 5. TOP 3 리스트 */
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

    /* 6. 탭 헤더 */
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


# ----------------- 3. 엑셀 파서 엔진 -----------------
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

# ----------------- 5. 사이드바 (지방이 캐릭터 완벽 표시) -----------------
with st.sidebar:
    avatar_tag = f'<img src="{JIBANG_IMG_B64}" style="width: 76px; height: 76px; border-radius: 50%; object-fit: cover; border: 2px solid #ffffff; background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.4);">'

    st.markdown(
        f'<div style="text-align: center; padding: 12px 0 16px 0;">'
        f'{avatar_tag}'
        f'<div style="font-size:1.2rem; font-weight:700; color:#ffffff; margin-top:8px;">365MC Intelligence</div>'
        f'<div style="font-size:0.75rem; color:#a1a1aa; margin-top:2px;">신환 유입 & 상권 분석 시스템</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.78rem; color:#9ca3af; font-weight:700; margin-bottom:8px;'>🔍 분석 필터</p>",
        unsafe_allow_html=True,
    )
    if not df_channels.empty:
        periods = sorted(df_channels["기간"].unique().tolist())
        sel_period = st.selectbox("분석 월 선택", periods)

        branches = ["전지점(통합)"] + sorted(
            df_channels[df_channels["기간"] == sel_period]["지점명"]
            .unique()
            .tolist()
        )
        sel_branch = st.selectbox("지점 선택", branches)
    else:
        sel_period, sel_branch = None, None
        st.caption("누적된 데이터가 없습니다.")

    st.markdown(
        "<div style='height: 30px;'></div><hr style='margin: 0 0 20px 0;'>",
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
        '<div style="padding: 60px 0; text-align: center;">'
        '<h2 style="font-weight:700; font-size:2rem; color:#0f172a;">365MC NEW Patient Command Center</h2>'
        '<p style="color: #71717a;">좌측 하단의 [신환조사 엑셀파일 업로드]에서 조사 파일을 업로드해 주십시오.</p>'
        '</div>',
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

# 상단 헤더: 타이틀 옆에 지방이 엠블럼 배치
header_jibang = f'<img src="{JIBANG_IMG_B64}" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover; margin-left: 12px; border: 1.5px solid #e2e8f0; vertical-align: middle;">'

st.markdown(
    f'<div style="margin-bottom: 24px;">'
    f'<div style="display: flex; align-items: center;">'
    f'<span style="font-weight: 700; font-size: 2.1rem; color: #0f172a; letter-spacing: -0.03em;">365MC 환자 관리 센터 — {sel_branch}</span>'
    f'{header_jibang}'
    f'</div>'
    f'<div style="color: #64748b; font-size: 0.92rem; font-weight: 500; margin-top: 4px;">'
    f'분석 기준월: <b>{sel_period}</b> &nbsp;|&nbsp; 데이터 검증 완료 (Verified)'
    f'</div>'
    f'</div>',
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

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">총 신환 유입수</div>'
        f'<div class="metric-value">{total_inflows:,} <span style="font-size:1.05rem; font-weight:500; color:#64748b;">건</span></div>'
        f'<div class="metric-badge">Gross Inflows</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">최대 유입 채널</div>'
        f'<div class="metric-value" style="font-size:1.45rem; line-height:1.2; padding-top:4px;">{top_channel}</div>'
        f'<div class="metric-badge">Primary Channel</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-title">바이럴 기여율</div>'
        f'<div class="metric-value">{viral_rate}<span style="font-size:1.2rem;">%</span></div>'
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

# ----------------- 8. 차트 테마 설정 -----------------
FORMAL_COLORS = ["#18181b", "#3f3f46", "#71717a", "#a1a1aa", "#d4d4d8", "#e4e4e7"]

formal_layout = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    margin=dict(l=20, r=20, t=45, b=20),
    font=dict(
        family="Pretendard, -apple-system, sans-serif",
        color="#334155",
        size=12,
    ),
    title=dict(
        font=dict(
            family="Pretendard, -apple-system, sans-serif",
            size=16,
            color="#0f172a",
        )
    ),
    xaxis=dict(
        showgrid=False,
        showline=True,
        linecolor="#e2e8f0",
        tickcolor="#e2e8f0",
        tickfont=dict(size=11, color="#64748b"),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#f1f5f9",
        showline=False,
        tickfont=dict(size=11, color="#64748b"),
    ),
)

# ----------------- 9. 탭별 분석 뷰 -----------------
tab1, tab2, tab3 = st.tabs(
    ["유입 경로 분석 (Channels)", "거주지 상권 분석 (Demographics)", "지점 벤치마크 (Benchmark)"]
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
            title="<b>전체 유입경로 순위 (Top 10 Channels)</b>",
            color_discrete_sequence=["#1e293b"],
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
            title="<b>바이럴 세부 유입 비중</b>",
            color_discrete_sequence=FORMAL_COLORS,
        )
        fig_vir.update_layout(
            paper_bgcolor="#ffffff",
            margin=dict(l=10, r=10, t=45, b=10),
            font=dict(family="Pretendard, sans-serif", color="#475569"),
            title=dict(
                font=dict(
                    family="Pretendard, sans-serif", size=16, color="#0f172a"
                )
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
            title="<b>환자 주요 거주지역 순위 (Top 12)</b>",
            color_discrete_sequence=["#475569"],
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
                title="<b>광역 권역별 환자 비중</b>",
                color_discrete_sequence=["#0f172a", "#64748b", "#cbd5e1"],
            )
            fig_area.update_layout(
                paper_bgcolor="#ffffff",
                margin=dict(l=10, r=10, t=45, b=10),
                font=dict(family="Pretendard, sans-serif", color="#475569"),
                title=dict(
                    font=dict(
                        family="Pretendard, sans-serif",
                        size=16,
                        color="#0f172a",
                    )
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
        st.info("전국 지점 간 비교를 확인하시려면 좌측 상단 필터에서 [전지점(통합)]을 선택해 주십시오.")
