import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = "data_store"
os.makedirs(DATA_DIR, exist_ok=True)
PARSED_MASTER_FILE = os.path.join(DATA_DIR, "master_parsed_analytics.parquet")

# ----------------- 페이지 설정 & SaaS 스타일 CSS -----------------
st.set_page_config(
    page_title="LAMS 신환 마케팅 인텔리전스",
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
        background-color: rgba(255, 255, 255, 0.92);
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
    }
    .metric-title {
        color: #64748b;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #1e1b4b;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-badge {
        display: inline-flex;
        font-size: 0.75rem;
        font-weight: 600;
        color: #4f46e5;
        background: #eef2ff;
        padding: 2px 8px;
        border-radius: 6px;
        margin-top: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------- 전문 파서 엔진 -----------------
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


def extract_period_from_name(filename):
    """파일명에서 연월(YY.MM 등) 추출"""
    match = re.search(r"\((\d{2})\.(\d{2})\)", filename)
    if match:
        return f"20{match.group(1)}-{match.group(2)}"
    return "2024-03"  # 기본값


def parse_hospital_excel(file_bytes, period_label):
    """지점별 시트 내 복수 테이블(지역, 전체경로, 바이럴채널) 및 집계시트 자동 파싱"""
    xls = pd.ExcelFile(file_bytes)
    sheet_names = xls.sheet_names

    region_records = []
    channel_records = []
    viral_records = []
    viral_summary_records = []

    for sheet in sheet_names:
        if sheet == "바이럴신환유입":
            df_v = pd.read_excel(xls, sheet_name=sheet)
            # 2행부터 데이터 위치
            for r in range(len(df_v)):
                row_vals = df_v.iloc[r].values
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

        # 지점별 시트 파싱
        df = pd.read_excel(xls, sheet_name=sheet)

        # 1. 헤더 행 위치 탐색 ('지역', '경로')
        header_row_idx = None
        for r in range(min(5, len(df))):
            vals = [str(x).strip() for x in df.iloc[r].dropna()]
            if "지역" in vals and "경로" in vals:
                header_row_idx = r
                break

        if header_row_idx is None:
            continue

        h_row = df.iloc[header_row_idx]
        region_col, channel_col, viral_col = None, None, None

        for c in range(len(h_row)):
            val = str(h_row[c]).strip()
            if val == "지역" and region_col is None:
                region_col = c
            elif val == "경로":
                channel_col = c
            elif "바이럴" in val:
                viral_col = c

        # 지역별 데이터 추출
        if region_col is not None:
            for r in range(header_row_idx + 1, len(df)):
                reg = df.iloc[r, region_col]
                cnt = df.iloc[r, region_col + 1]
                if (
                    pd.notna(reg)
                    and str(reg).strip()
                    and str(reg).strip() != "nan"
                ):
                    if pd.notna(cnt) and str(cnt).strip().isdigit():
                        region_records.append(
                            {
                                "기간": period_label,
                                "지점명": sheet,
                                "거주지역": str(reg).strip(),
                                "신환수": int(cnt),
                            }
                        )

        # 전체 유입경로 추출
        if channel_col is not None:
            for r in range(header_row_idx + 1, len(df)):
                ch = df.iloc[r, channel_col]
                cnt = df.iloc[r, channel_col + 1]
                if (
                    pd.notna(ch)
                    and str(ch).strip()
                    and str(ch).strip() != "nan"
                ):
                    if pd.notna(cnt) and str(cnt).strip().isdigit():
                        channel_records.append(
                            {
                                "기간": period_label,
                                "지점명": sheet,
                                "유입경로": str(ch).strip(),
                                "유입수": int(cnt),
                            }
                        )

        # 바이럴 세부채널 추출
        if viral_col is not None:
            for r in range(header_row_idx + 1, len(df)):
                vch = df.iloc[r, viral_col]
                cnt = df.iloc[r, viral_col + 1]
                if (
                    pd.notna(vch)
                    and str(vch).strip()
                    and str(vch).strip() != "nan"
                ):
                    if pd.notna(cnt) and str(cnt).strip().isdigit():
                        viral_records.append(
                            {
                                "기간": period_label,
                                "지점명": sheet,
                                "바이럴채널": str(vch).strip(),
                                "유입수": int(cnt),
                            }
                        )

    return (
        pd.DataFrame(region_records),
        pd.DataFrame(channel_records),
        pd.DataFrame(viral_records),
        pd.DataFrame(viral_summary_records),
    )


# ----------------- 데이터 저장 및 로드 매니저 -----------------
@st.cache_data
def get_stored_data():
    if os.path.exists(PARSED_MASTER_FILE):
        return pd.read_parquet(PARSED_MASTER_FILE)
    return None


# ----------------- 사이드바 설정 -----------------
with st.sidebar:
    st.markdown("### 🏥 LAMS Marketing HQ")
    st.caption("신환 유입 & 상권 분석 시스템")

    uploaded_files = st.file_uploader(
        "신환 조사 엑셀 파일 업로드 (다중 선택 가능)",
        type=["xlsx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        all_r, all_c, all_v, all_vs = [], [], [], []
        for file in uploaded_files:
            period_tag = extract_period_from_name(file.name)
            df_r, df_c, df_v, df_vs = parse_hospital_excel(file, period_tag)
            all_r.append(df_r)
            all_c.append(df_c)
            all_v.append(df_v)
            all_vs.append(df_vs)

        if st.button("데이터 파싱 및 누적 저장", use_container_width=True):
            r_full = pd.concat(all_r, ignore_index=True).drop_duplicates()
            c_full = pd.concat(all_c, ignore_index=True).drop_duplicates()
            v_full = pd.concat(all_v, ignore_index=True).drop_duplicates()
            vs_full = pd.concat(all_vs, ignore_index=True).drop_duplicates()

            # 저장
            r_full.to_parquet(
                os.path.join(DATA_DIR, "regions.parquet"), index=False
            )
            c_full.to_parquet(
                os.path.join(DATA_DIR, "channels.parquet"), index=False
            )
            v_full.to_parquet(
                os.path.join(DATA_DIR, "viral.parquet"), index=False
            )
            vs_full.to_parquet(
                os.path.join(DATA_DIR, "viral_summary.parquet"), index=False
            )
            st.success("데이터 파싱 및 누적이 완료되었습니다!")
            st.rerun()

# ----------------- 데이터 로드 확인 -----------------
reg_path = os.path.join(DATA_DIR, "regions.parquet")
ch_path = os.path.join(DATA_DIR, "channels.parquet")
vir_path = os.path.join(DATA_DIR, "viral.parquet")
vsum_path = os.path.join(DATA_DIR, "viral_summary.parquet")

if not os.path.exists(ch_path):
    st.info(
        "👋 좌측 사이드바에서 `람스 신환조사` 엑셀 파일을 업로드하고 [데이터 파싱 및 누적 저장]을 눌러주세요."
    )
    st.stop()

df_regions = pd.read_parquet(reg_path)
df_channels = pd.read_parquet(ch_path)
df_viral = pd.read_parquet(vir_path)
df_vsum = pd.read_parquet(vsum_path)

# ----------------- 필터 UI -----------------
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔍 분석 필터")

    periods = sorted(df_channels["기간"].unique().tolist())
    sel_period = st.selectbox("분석 월 선택", periods)

    branches = ["전지점(통합)"] + sorted(
        df_channels[df_channels["기간"] == sel_period]["지점명"]
        .unique()
        .tolist()
    )
    sel_branch = st.selectbox("지점 선택", branches)

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

# ----------------- 메인 대시보드 뷰 -----------------
st.markdown(
    f"<h2 style='color: #1e1b4b; margin-bottom: 0px;'>📈 {sel_branch} 마케팅 성과 대시보드</h2>"
    f"<p style='color: #64748b; font-size: 0.95rem; margin-top: 4px;'>분석 기준월: <b>{sel_period}</b></p>",
    unsafe_allow_html=True,
)

# KPI 4대 지표 카드 계산
total_touches = f_ch["유입수"].sum()
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
top_residence = (
    f_reg.groupby("거주지역")["신환수"].sum().idxmax()
    if not f_reg.empty
    else "-"
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-title">총 유입 접점수</div>
        <div class="metric-value">{total_touches:,} <span style="font-size:1rem;">건</span></div>
        <div class="metric-badge">All Inflow Touchpoints</div>
    </div>""",
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-title">최대 전환 경로</div>
        <div class="metric-value" style="font-size:1.35rem; line-height: 2rem;">{top_channel}</div>
        <div class="metric-badge">Core Marketing Channel</div>
    </div>""",
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-title">바이럴 기여율</div>
        <div class="metric-value">{viral_rate}%</div>
        <div class="metric-badge">Blog/Cafe/SNS Organic</div>
    </div>""",
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-title">핵심 모객 상권(1위)</div>
        <div class="metric-value" style="font-size:1.35rem; line-height: 2rem;">{top_residence}</div>
        <div class="metric-badge">Top Residential Area</div>
    </div>""",
        unsafe_allow_html=True,
    )

# 공통 차트 레이아웃 템플릿
layout_opts = dict(
    paper_bgcolor="rgba(255,255,255,1)",
    plot_bgcolor="rgba(255,255,255,1)",
    margin=dict(l=15, r=15, t=35, b=15),
    font=dict(family="sans-serif", color="#475569"),
    xaxis=dict(showgrid=False, linecolor="#f1f5f9"),
    yaxis=dict(showgrid=True, gridcolor="#f8fafc", linecolor="#f1f5f9"),
)

# ----------------- 마케팅 인텔리전스 탭 분할 -----------------
tab1, tab2, tab3 = st.tabs(
    ["🎯 유입 채널 & 바이럴 심층분석", "🗺️ 거주지 상권 분석", "📊 지점별 비교 (Rank)"]
)

with tab1:
    c1, c2 = st.columns([1.3, 1])

    with c1:
        # 전체 유입 채널 랭킹
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
            title="<b>전체 유입경로 Top 12 (온/오프라인)</b>",
            color_discrete_sequence=["#4f46e5"],
        )
        fig_ch.update_layout(**layout_opts)
        st.plotly_chart(fig_ch, use_container_width=True)

    with c2:
        # 바이럴 세부 채널 도넛 차트
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
            title="<b>바이럴 세부 유입 믹스 (블로그·카페·SNS)</b>",
            color_discrete_sequence=COLOR_PALETTE,
        )
        fig_vir.update_layout(
            paper_bgcolor="rgba(255,255,255,1)",
            margin=dict(l=10, r=10, t=35, b=10),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5
            ),
        )
        st.plotly_chart(fig_vir, use_container_width=True)

with tab2:
    r1, r2 = st.columns([1.2, 1])
    with r1:
        # 거주지 상위 지역 랭킹
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
            title="<b>내원 신환 상위 거주지 (Top 15 권역)</b>",
            color_discrete_sequence=["#fb7185"],
        )
        fig_reg.update_layout(**layout_opts)
        st.plotly_chart(fig_reg, use_container_width=True)

    with r2:
        # 서울 vs 경기/타지역 비중 간이 분석
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
                title="<b>광역 권역별 환자 비중</b>",
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
        st.markdown("#### 🏆 지점별 바이럴 마케팅 기여율 순위")
        # 바이럴 기여율 내림차순 정렬
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
