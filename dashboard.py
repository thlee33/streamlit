import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests
import zipfile
import io
import warnings
warnings.filterwarnings('ignore')

# 페이지 설정
st.set_page_config(
    page_title="🚗 EPA 자동차 연비 대시보드",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS로 레이아웃 최적화
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.2rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 35px;
        padding: 0px 12px;
        font-size: 14px;
    }
    h1 {
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
    }
    h3 {
        font-size: 1.2rem !important;
        margin-bottom: 0.5rem !important;
    }
    .plotly-chart {
        height: 300px !important;
    }
</style>
""", unsafe_allow_html=True)

# 캐시된 데이터 로딩 함수
@st.cache_data
def load_data():
    """EPA 자동차 데이터를 다운로드하고 전처리"""
    try:
        # ZIP 파일 다운로드
        url = "https://www.fueleconomy.gov/feg/epadata/vehicles.csv.zip"
        response = requests.get(url)
        
        # ZIP 파일 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            csv_filename = zip_file.namelist()[0]
            with zip_file.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)
        
        # 데이터 전처리
        essential_cols = ['year', 'make', 'model', 'VClass', 'drive', 'trans', 
                         'fuelType', 'cylinders', 'displ', 'city08', 'highway08', 
                         'comb08', 'co2TailpipeGpm', 'fuelCost08']
        
        # 컬럼이 존재하는지 확인하고 선택
        available_cols = [col for col in essential_cols if col in df.columns]
        df = df[available_cols].copy()
        
        # 연비 관련 컬럼 결측치 제거
        mpg_cols = ['city08', 'highway08', 'comb08']
        available_mpg_cols = [col for col in mpg_cols if col in df.columns]
        
        for col in available_mpg_cols:
            df = df[df[col] > 0]
        
        # 기본 결측치 처리
        df = df.dropna(subset=['year', 'make'] + available_mpg_cols)
        
        # 데이터 타입 최적화
        df['year'] = df['year'].astype(int)
        if 'cylinders' in df.columns:
            df['cylinders'] = pd.to_numeric(df['cylinders'], errors='coerce')
        if 'displ' in df.columns:
            df['displ'] = pd.to_numeric(df['displ'], errors='coerce')
        
        # 최근 20년 데이터만 필터링
        current_year = pd.Timestamp.now().year
        df = df[df['year'] >= (current_year - 20)]
        
        return df
        
    except Exception as e:
        st.error(f"데이터 로딩 실패: {str(e)}")
        return None

def main():
    # 간결한 헤더
    st.title("🚗 EPA 자동차 연비 대시보드")
    
    # 데이터 로드 (로딩 상태는 스피너로 간단히)
    with st.spinner('EPA 데이터 로딩 중...'):
        df = load_data()
    
    if df is None:
        st.stop()
    
    # 사이드바 필터 (더 컴팩트하게)
    st.sidebar.header("🎛️ 필터")
    
    # 연도 필터
    year_range = st.sidebar.slider(
        "연도",
        min_value=int(df['year'].min()),
        max_value=int(df['year'].max()),
        value=(int(df['year'].min()), int(df['year'].max()))
    )
    
    # 제조사 필터
    makes = ['전체'] + sorted(df['make'].unique().tolist())
    selected_make = st.sidebar.selectbox("제조사", makes)
    
    # 연료 타입 필터
    if 'fuelType' in df.columns:
        fuel_types = ['전체'] + sorted(df['fuelType'].dropna().unique().tolist())
        selected_fuel = st.sidebar.selectbox("연료", fuel_types)
    else:
        selected_fuel = '전체'
    
    # 실린더 수 필터
    if 'cylinders' in df.columns and df['cylinders'].notna().sum() > 0:
        cylinders = ['전체'] + sorted([str(int(x)) for x in df['cylinders'].dropna().unique()])
        selected_cylinders = st.sidebar.selectbox("실린더", cylinders)
    else:
        selected_cylinders = '전체'
    
    # 필터 적용
    filtered_df = df.copy()
    
    filtered_df = filtered_df[
        (filtered_df['year'] >= year_range[0]) & 
        (filtered_df['year'] <= year_range[1])
    ]
    
    if selected_make != '전체':
        filtered_df = filtered_df[filtered_df['make'] == selected_make]
    
    if selected_fuel != '전체' and 'fuelType' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['fuelType'] == selected_fuel]
    
    if selected_cylinders != '전체' and 'cylinders' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['cylinders'] == float(selected_cylinders)]
    
    if len(filtered_df) == 0:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
        return
    
    # 컴팩트한 주요 통계
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("모델 수", f"{len(filtered_df):,}")
    
    with col2:
        if 'comb08' in filtered_df.columns:
            avg_mpg = filtered_df['comb08'].mean()
            st.metric("평균 연비", f"{avg_mpg:.1f} MPG")
    
    with col3:
        if 'co2TailpipeGpm' in filtered_df.columns:
            avg_co2 = filtered_df['co2TailpipeGpm'].mean()
            st.metric("CO2 배출", f"{avg_co2:.0f} g/mi")
    
    with col4:
        if 'cylinders' in filtered_df.columns:
            avg_cylinders = filtered_df['cylinders'].mean()
            st.metric("평균 실린더", f"{avg_cylinders:.1f}")
    
    with col5:
        if 'displ' in filtered_df.columns:
            avg_displ = filtered_df['displ'].mean()
            st.metric("평균 배기량", f"{avg_displ:.1f}L")
    
    # 컴팩트한 차트 영역 (높이 줄임)
    tab1, tab2, tab3, tab4 = st.tabs(["📊 연비", "🏭 제조사", "📈 트렌드", "⚙️ 성능"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'comb08' in filtered_df.columns:
                fig_hist = px.histogram(
                    filtered_df,
                    x='comb08',
                    nbins=25,
                    title="연비 분포",
                    labels={'comb08': '연비(MPG)', 'count': '모델수'}
                )
                fig_hist.update_layout(height=280, showlegend=False, margin=dict(t=40, b=40))
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            if 'city08' in filtered_df.columns and 'highway08' in filtered_df.columns:
                fig_scatter = px.scatter(
                    filtered_df,
                    x='city08',
                    y='highway08',
                    title="시내 vs 고속도로 연비",
                    labels={'city08': '시내연비', 'highway08': '고속연비'},
                    opacity=0.6
                )
                fig_scatter.update_layout(height=280, margin=dict(t=40, b=40))
                st.plotly_chart(fig_scatter, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            make_counts = filtered_df['make'].value_counts().head(8)
            fig_make = px.bar(
                x=make_counts.values,
                y=make_counts.index,
                orientation='h',
                title="제조사별 모델 수 (Top8)",
                labels={'x': '모델수', 'y': '제조사'}
            )
            fig_make.update_layout(height=280, yaxis={'categoryorder': 'total ascending'}, margin=dict(t=40, b=40))
            st.plotly_chart(fig_make, use_container_width=True)
        
        with col2:
            if 'comb08' in filtered_df.columns:
                make_mpg = filtered_df.groupby('make')['comb08'].mean().sort_values(ascending=False).head(8)
                fig_make_mpg = px.bar(
                    x=make_mpg.values,
                    y=make_mpg.index,
                    orientation='h',
                    title="제조사별 평균 연비 (Top8)",
                    labels={'x': '연비(MPG)', 'y': '제조사'}
                )
                fig_make_mpg.update_layout(height=280, yaxis={'categoryorder': 'total ascending'}, margin=dict(t=40, b=40))
                st.plotly_chart(fig_make_mpg, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'comb08' in filtered_df.columns:
                yearly_mpg = filtered_df.groupby('year')['comb08'].mean().reset_index()
                fig_trend = px.line(
                    yearly_mpg,
                    x='year',
                    y='comb08',
                    title="연도별 평균 연비",
                    labels={'year': '연도', 'comb08': '연비(MPG)'}
                )
                fig_trend.update_layout(height=280, margin=dict(t=40, b=40))
                st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            yearly_count = filtered_df['year'].value_counts().sort_index()
            fig_count = px.area(
                x=yearly_count.index,
                y=yearly_count.values,
                title="연도별 출시 모델 수",
                labels={'x': '연도', 'y': '모델수'}
            )
            fig_count.update_layout(height=280, margin=dict(t=40, b=40))
            st.plotly_chart(fig_count, use_container_width=True)
    
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'displ' in filtered_df.columns and 'comb08' in filtered_df.columns:
                fig_displ = px.scatter(
                    filtered_df,
                    x='displ',
                    y='comb08',
                    title="배기량 vs 연비",
                    labels={'displ': '배기량(L)', 'comb08': '연비(MPG)'},
                    opacity=0.6
                )
                fig_displ.update_layout(height=280, margin=dict(t=40, b=40))
                st.plotly_chart(fig_displ, use_container_width=True)
        
        with col2:
            if 'cylinders' in filtered_df.columns and 'comb08' in filtered_df.columns:
                cylinder_mpg = filtered_df.groupby('cylinders')['comb08'].mean().reset_index()
                fig_cyl = px.bar(
                    cylinder_mpg,
                    x='cylinders',
                    y='comb08',
                    title="실린더 수별 평균 연비",
                    labels={'cylinders': '실린더수', 'comb08': '연비(MPG)'}
                )
                fig_cyl.update_layout(height=280, margin=dict(t=40, b=40))
                st.plotly_chart(fig_cyl, use_container_width=True)
    
    # 상세 데이터는 확장 가능한 섹션으로
    with st.expander("📋 상세 데이터 보기"):
        display_cols = ['year', 'make', 'model', 'comb08', 'city08', 'highway08']
        if 'cylinders' in filtered_df.columns:
            display_cols.append('cylinders')
        if 'displ' in filtered_df.columns:
            display_cols.append('displ')
        
        available_display_cols = [col for col in display_cols if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_display_cols].head(50),
            use_container_width=True,
            height=300
        )
        st.caption(f"필터링된 데이터: {len(filtered_df):,}개 중 상위 50개 표시")

if __name__ == "__main__":
    main()