import os
import pandas as pd
import plotly.express as px
import streamlit as st

# 데이터 저장 경로
DATA_FILE = "hospital_cumulative_data.xlsx"

# 기본 필수 컬럼 정의
REQUIRED_COLUMNS = ["년월", "지점명", "유입경로", "신환수"]


def load_cumulative_data():
    """누적 엑셀 파일 로드 (없으면 빈 데이터프레임 반환)"""
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)
        # 년월 형식 표준화 (예: '2026-05' 문자열 형태 유지)
        df["년월"] = df["년월"].astype(str)
        return df
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def save_cumulative_data(df):
    """누적 데이터를 엑셀 파일로 저장"""
    df.to_excel(DATA_FILE, index=False)


# 페이지 기본 설정
st.set_page_config(page_title="병원 지점별 신환 분석 시스템", layout="wide")
st.title("🏥 병원 월별 신환 수 및 유입경로 통합 대시보드")

# 누적 데이터 불러오기
master_df = load_cumulative_data()

# ----------------- 사이드바: 엑셀 파일 업로드 & 필터 -----------------
with st.sidebar:
    st.header("📂 월별 데이터 업로드")
    uploaded_file = st.file_uploader(
        "신규 엑셀 파일 업로드 (.xlsx)", type=["xlsx"]
    )

    if uploaded_file is not None:
        try:
            new_df = pd.read_excel(uploaded_file)
            new_df["년월"] = new_df["년월"].astype(str)

            # 필수 컬럼 체크
            if all(col in new_df.columns for col in REQUIRED_COLUMNS):
                if st.button("누적 데이터에 병합하기"):
                    # 기존 데이터와 새 데이터 병합 후 중복 행 제거
                    combined_df = pd.concat(
                        [master_df, new_df], ignore_index=True
                    )
                    # 동일 년월/지점/유입경로에 대해 중복 업로드 방지 (최신 데이터 덮어쓰기)
                    combined_df = combined_df.drop_duplicates(
                        subset=["년월", "지점명", "유입경로"], keep="last"
                    )

                    save_cumulative_data(combined_df)
                    st.success("데이터가 성공적으로 누적 저장되었습니다!")
                    st.rerun()
            else:
                st.error(
                    f"엑셀 파일에 다음 컬럼이 모두 포함되어야 합니다: {', '.join(REQUIRED_COLUMNS)}"
                )
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    st.markdown("---")
    st.header("🔍 분석 필터")

    if not master_df.empty:
        # 지점 선택 (전체 선택 옵션 포함)
        all_branches = ["전지점(통합)"] + sorted(
            master_df["지점명"].unique().tolist()
        )
        selected_branch = st.selectbox("지점 선택", all_branches)

        # 기간 선택
        all_months = sorted(master_df["년월"].unique().tolist())
        selected_period = st.select_slider(
            "분석 기간 선택",
            options=all_months,
            value=(all_months[0], all_months[-1])
            if len(all_months) > 1
            else (all_months[0], all_months[0]),
        )
    else:
        selected_branch = None
        selected_period = None

# ----------------- 메인 대시보드 뷰 -----------------
if master_df.empty:
    st.info(
        "💡 아직 등록된 누적 데이터가 없습니다. 좌측 사이드바에서 엑셀 파일을 업로드해주세요."
    )
    st.subheader("업로드용 엑셀 파일 양식 예시")
    sample_df = pd.DataFrame(
        {
            "년월": ["2026-01", "2026-01", "2026-01", "2026-01"],
            "지점명": ["강남점", "강남점", "서초점", "분당점"],
            "유입경로": ["네이버플레이스", "지인소개", "인스타그램", "당근마켓"],
            "신환수": [45, 20, 35, 18],
        }
    )
    st.dataframe(sample_df)
else:
    # 데이터 필터링 적용
    start_m, end_m = selected_period
    filtered_df = master_df[
        (master_df["년월"] >= start_m) & (master_df["년월"] <= end_m)
    ]

    if selected_branch != "전지점(통합)":
        filtered_df = filtered_df[filtered_df["지점명"] == selected_branch]

    # 상단 핵심 KPI 지표
    total_patients = filtered_df["신환수"].sum()
    st.subheader(
        f"📊 분석 요약: {selected_branch} ({start_m} ~ {end_m})"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("기간 내 총 신환수", f"{total_patients:,}명")

    top_channel = (
        filtered_df.groupby("유입경로")["신환수"].sum().idxmax()
        if not filtered_df.empty
        else "-"
    )
    col2.metric("최대 유입 채널", top_channel)

    branch_count = (
        len(filtered_df["지점명"].unique())
        if selected_branch == "전지점(통합)"
        else 1
    )
    col3.metric("포함된 지점 수", f"{branch_count}개 지점")

    st.markdown("---")

    # 차트 영역
    tab1, tab2, tab3 = st.tabs(
        ["📈 월별 신환 추이", "🎯 유입경로 분석", "📋 원본 데이터"]
    )

    with tab1:
        # 월별 신환 추이 라인/바 차트
        if selected_branch == "전지점(통합)":
            # 전지점인 경우 지점별 추이 비교
            monthly_trend = (
                filtered_df.groupby(["년월", "지점명"])["신환수"]
                .sum()
                .reset_index()
            )
            fig_trend = px.bar(
                monthly_trend,
                x="년월",
                y="신환수",
                color="지점명",
                barmode="stack",
                title="전지점 월별 신환 추이 (누적)",
                text_auto=True,
            )
        else:
            monthly_trend = (
                filtered_df.groupby("년월")["신환수"].sum().reset_index()
            )
            fig_trend = px.line(
                monthly_trend,
                x="년월",
                y="신환수",
                markers=True,
                title=f"{selected_branch} 월별 신환 추이",
                text="신환수",
            )
            fig_trend.update_traces(textposition="top center")

        st.plotly_chart(fig_trend, use_container_width=True)

    with tab2:
        # 유입경로별 파이/바 차트
        c1, c2 = st.columns(2)

        channel_sum = (
            filtered_df.groupby("유입경로")["신환수"].sum().reset_index()
        )

        with c1:
            fig_pie = px.pie(
                channel_sum,
                names="유입경로",
                values="신환수",
                title="유입경로별 비율",
                hole=0.4,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            fig_bar = px.bar(
                channel_sum.sort_values(by="신환수", ascending=True),
                x="신환수",
                y="유입경로",
                orientation="h",
                title="유입경로별 절대 환자 수",
                text_auto=True,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.dataframe(filtered_df, use_container_width=True)
        # 누적 전체 데이터 다운로드 버튼
        csv = master_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "전체 누적 데이터 CSV 다운로드",
            data=csv,
            file_name="master_hospital_data.csv",
            mime="text/csv",
        )