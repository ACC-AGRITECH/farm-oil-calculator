import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import base64
import os
import glob

# 1. 페이지 기본 설정
st.set_page_config(page_title="농가 유류비 분석기", layout="wide")

# ==========================================
# [디자인 강제 통일] 강력한 표(Table) CSS 적용
# ==========================================
st.markdown("""
<style>
    html, body, p, span, label, input, li, a {
        font-size: 18px !important;
    }
    table th, table td, .stTable th, .stTable td, th[scope="row"], th[scope="col"] {
        font-size: 18px !important;
        font-weight: 900 !important;
        color: inherit !important;
    }
    .stNumberInput input {
        font-size: 18px !important;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [기능 1] 상단 고정 로고 및 타이틀 영역
# ==========================================
def render_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            
        html_code = f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{encoded_string}" style="width: 80px; height: 80px; object-fit: contain; flex-shrink: 0;">
            <div style="margin-left: 20px; font-size: 26px; font-weight: bold; white-space: nowrap;">농업문화원</div>
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    else:
        st.warning("⚠️ 폴더에 'logo.png' 파일이 없습니다. 로고 이미지를 넣어주세요.")

render_header()

# ★ 36px 적용 완료
st.markdown("<div style='font-size: 36px; font-weight: bold; margin-bottom: 15px;'>농업용 면세유 현재 가격 및 농가 임계소득 계산기</div>", unsafe_allow_html=True)
st.divider()

# ==========================================
# [기능 2] 1번 항목: 실시간 API 연동 (현재가 유지)
# ==========================================
@st.cache_data(ttl=3600)
def get_current_oil_price():
    api_key = "F260311396" 
    url = f"http://www.opinet.co.kr/api/avgAllPrice.do?out=json&code={api_key}"
    try:
        response = requests.get(url)
        return pd.DataFrame(response.json()['RESULT']['OIL'])
    except:
        return None

current_price_df = get_current_oil_price()
st.markdown("<div style='font-size: 26px; font-weight: bold; margin-top: 10px; margin-bottom: 15px;'>1. 현재 유류 가격 현황</div>", unsafe_allow_html=True)

# 기준가 초기화
price_gas, price_diesel, price_kero = 1600.0, 1500.0, 1300.0
price_gas_taxfree, price_diesel_taxfree, price_kero_taxfree = price_gas * 0.55, price_diesel * 0.65, price_kero * 0.85

if current_price_df is not None:
    df_filtered = current_price_df[current_price_df['PRODCD'].isin(['B027', 'D047', 'C004'])].copy()
    try:
        price_gas = float(df_filtered[df_filtered['PRODCD'] == 'B027']['PRICE'].values[0])
        price_diesel = float(df_filtered[df_filtered['PRODCD'] == 'D047']['PRICE'].values[0])
        price_kero = float(df_filtered[df_filtered['PRODCD'] == 'C004']['PRICE'].values[0])
        
        price_gas_taxfree = price_gas * 0.55
        price_diesel_taxfree = price_diesel * 0.65
        price_kero_taxfree = price_kero * 0.85
        
        display_data = {
            '유종': ['휘발유', '경유', '실내 등유'],
            '일반 유가 (원/L)': [f"{price_gas:,.2f}", f"{price_diesel:,.2f}", f"{price_kero:,.2f}"],
            '농업용 면세유 (원/L)': [f"{price_gas_taxfree:,.2f}", f"{price_diesel_taxfree:,.2f}", f"{price_kero_taxfree:,.2f}"]
        }
        st.table(pd.DataFrame(display_data))
    except IndexError:
        st.error("일부 유종의 데이터를 불러오지 못했습니다.")
else:
    st.error("유가 데이터를 불러오는 데 실패했습니다.")

st.divider()

# ==========================================
# [기능 3] 2번 항목: 다운로드한 엑셀(CSV) 강력 자동 병합 로직
# ==========================================
st.markdown("<div style='font-size: 26px; font-weight: bold; margin-top: 10px; margin-bottom: 15px;'>2. 유류가격 분석 (최근 3개월)</div>", unsafe_allow_html=True)

@st.cache_data
def load_summary_data():
    if not os.path.exists("oil_summary.csv"):
        return None
    df = pd.read_csv("oil_summary.csv")
    df['날짜'] = pd.to_datetime(df['날짜'])
    return df

df_full_data = load_summary_data()

if df_full_data is not None and not df_full_data.empty:
    df_trend_this_year = df_full_data[df_full_data['날짜'].dt.year == 2026]
    df_trend_last_year = df_full_data[df_full_data['날짜'].dt.year == 2025]

    # [가] 올해 그래프
    fig_this_year = px.line(df_trend_this_year, x='날짜', 
                     y=[c for c in ['일반 휘발유', '일반 경유', '일반 등유', '농업용 면세 휘발유', '농업용 면세 경유', '농업용 면세 등유'] if c in df_trend_this_year.columns], 
                     title="가. 최근 3개월 유종별 가격변동 추이")
    # ★ 범례(Legend) 상단 가로 배치로 그래프 넓히기 적용
    fig_this_year.update_layout(
        title_font_size=18, 
        font=dict(size=18),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            title_text=""
        )
    )
    st.plotly_chart(fig_this_year, use_container_width=True)

    # [나] 작년 그래프
    fig_last_year = px.line(df_trend_last_year, x='날짜', 
                     y=[c for c in ['일반 휘발유', '일반 경유', '일반 등유', '농업용 면세 휘발유', '농업용 면세 경유', '농업용 면세 등유'] if c in df_trend_last_year.columns], 
                     title="나. 전년도 동기간 유종별 가격변동 내역")
    # ★ 범례(Legend) 상단 가로 배치로 그래프 넓히기 적용
    fig_last_year.update_layout(
        title_font_size=18, 
        font=dict(size=18),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            title_text=""
        )
    )
    st.plotly_chart(fig_last_year, use_container_width=True)

    # [다] 증감율 표
    st.markdown("<div style='font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;'>다. 유종별 전년비 증감율(%)</div>", unsafe_allow_html=True)
    
    def calc_yoy(this_avg, last_avg):
        if last_avg == 0 or pd.isna(last_avg): return 0
        return ((this_avg - last_avg) / last_avg) * 100

    yoy_df_list = []
    columns_to_check = ['일반 휘발유', '일반 경유', '일반 등유', '농업용 면세 휘발유', '농업용 면세 경유', '농업용 면세 등유']
    
    for oil_type in columns_to_check:
        if oil_type in df_trend_this_year.columns and oil_type in df_trend_last_year.columns:
            this_avg = df_trend_this_year[oil_type].mean()
            last_avg = df_trend_last_year[oil_type].mean()
            rate = calc_yoy(this_avg, last_avg)
            yoy_df_list.append({'유종': oil_type, '전년 동기 평균(원/L)': last_avg, '올해 평균(원/L)': this_avg, '증감율(%)': rate})

    if yoy_df_list:
        df_yoy = pd.DataFrame(yoy_df_list)
        df_yoy['전년 동기 평균(원/L)'] = df_yoy['전년 동기 평균(원/L)'].map("{:,.2f}".format)
        df_yoy['올해 평균(원/L)'] = df_yoy['올해 평균(원/L)'].map("{:,.2f}".format)
        df_yoy['증감율(%)'] = df_yoy['증감율(%)'].map(lambda x: f"▲ {x:.1f}%" if x > 0 else f"▼ {abs(x):.1f}%")
        st.table(df_yoy)
    else:
        st.warning("비교할 수 있는 유종 데이터가 부족합니다.")
else:
    st.error("🚨 폴더에 'oil_summary.csv' 파일이 없거나 읽을 수 없습니다.")

st.divider()

# ==========================================
# [기능 4] 스마트폰 맞춤형 세로형 손익 계산기
# ==========================================
st.markdown("<div style='font-size: 26px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;'>3. 유류비 감안 손익분기점 계산기</div>", unsafe_allow_html=True)
st.markdown("<div style='font-size: 18px; margin-bottom: 20px;'>항목