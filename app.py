import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import base64
import os

st.set_page_config(page_title="농가 유류비 분석기", layout="wide")

st.markdown("""
<style>
    html, body, p, span, label, input, li, a { font-size: 18px !important; }
    table th, table td, .stTable th, .stTable td, th[scope="row"], th[scope="col"] {
        font-size: 18px !important; font-weight: 900 !important; color: inherit !important;
    }
    .stNumberInput input { font-size: 18px !important; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

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

render_header()
st.markdown("<div style='font-size: 46px; font-weight: bold; margin-bottom: 15px;'>농업용 면세유 현재 가격 및 농가 임계소득 계산기</div>", unsafe_allow_html=True)
st.divider()

# 1. 현재 유류 가격 (API)
@st.cache_data(ttl=3600)
def get_current_oil_price():
    url = f"http://www.opinet.co.kr/api/avgAllPrice.do?out=json&code=F260311396"
    try:
        response = requests.get(url)
        return pd.DataFrame(response.json()['RESULT']['OIL'])
    except:
        return None

current_price_df = get_current_oil_price()
st.markdown("<div style='font-size: 26px; font-weight: bold; margin-top: 10px; margin-bottom: 15px;'>1. 현재 유류 가격 현황</div>", unsafe_allow_html=True)

price_gas, price_diesel, price_kero = 1600.0, 1500.0, 1300.0
price_gas_taxfree, price_diesel_taxfree, price_kero_taxfree = price_gas * 0.55, price_diesel * 0.65, price_kero * 0.85

if current_price_df is not None:
    df_filtered = current_price_df[current_price_df['PRODCD'].isin(['B027', 'D047', 'C004'])].copy()
    try:
        price_gas = float(df_filtered[df_filtered['PRODCD'] == 'B027']['PRICE'].values[0])
        price_diesel = float(df_filtered[df_filtered['PRODCD'] == 'D047']['PRICE'].values[0])
        price_kero = float(df_filtered[df_filtered['PRODCD'] == 'C004']['PRICE'].values[0])
        price_gas_taxfree, price_diesel_taxfree, price_kero_taxfree = price_gas * 0.55, price_diesel * 0.65, price_kero * 0.85
        
        display_data = {
            '유종': ['휘발유', '경유', '실내 등유'],
            '일반 유가 (원/L)': [f"{price_gas:,.2f}", f"{price_diesel:,.2f}", f"{price_kero:,.2f}"],
            '농업용 면세유 (원/L)': [f"{price_gas_taxfree:,.2f}", f"{price_diesel_taxfree:,.2f}", f"{price_kero_taxfree:,.2f}"]
        }
        st.table(pd.DataFrame(display_data))
    except IndexError:
        pass

st.divider()

# 2. 유류가격 분석 (요약본 읽기)
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

    fig_this_year = px.line(df_trend_this_year, x='날짜', 
                     y=[c for c in ['일반 휘발유', '일반 경유', '일반 등유', '농업용 면세 휘발유', '농업용 면세 경유', '농업용 면세 등유'] if c in df_trend_this_year.columns], 
                     title="가. 최근 3개월 유종별 가격변동 추이")
    fig_this_year.update_layout(title_font_size=18, font=dict(size=18))
    st.plotly_chart(fig_this_year, width="stretch")

    fig_last_year = px.line(df_trend_last_year, x='날짜', 
                     y=[c for c in ['일반 휘발유', '일반 경유', '일반 등유', '농업용 면세 휘발유', '농업용 면세 경유', '농업용 면세 등유'] if c in df_trend_last_year.columns], 
                     title="나. 전년도 동기간 유종별 가격변동 내역")
    fig_last_year.update_layout(title_font_size=18, font=dict(size=18))
    st.plotly_chart(fig_last_year, width="stretch")

    st.markdown("<div style='font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;'>다. 유종별 전년비 증감율(%)</div>", unsafe_allow_html=True)
    def calc_yoy(this_avg, last_avg):
        if last_avg == 0 or pd.isna(last_avg): return 0
        return ((this_avg - last_avg) / last_avg) * 100

    yoy_df_list = []
    for oil_type in ['일반 휘발유', '일반 경유', '일반 등유', '농업용 면세 휘발유', '농업용 면세 경유', '농업용 면세 등유']:
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

st.divider()

# 3. 계산기
st.markdown("<div style='font-size: 26px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;'>3. 유류비 감안 손익분기점 계산기</div>", unsafe_allow_html=True)
st.markdown("<div style='font-size: 18px; margin-bottom: 20px;'>항목을 위에서부터 차례대로 입력해 주세요.</div>", unsafe_allow_html=True)
st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>■ 입력 항목</div>", unsafe_allow_html=True)

revenue_this_month = st.number_input("가. 이번 달 매출액 (만원)", value=10000, step=1000)
fuel_type = st.radio("※ 계산 기준 유종 선택", ["면세 등유", "면세 경유", "면세 휘발유"], horizontal=True)
fuel_usage = st.number_input("나. 이번 달 유류 사용량 (리터)", value=2000, step=100)

st.markdown("<div style='font-size: 18px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;'>다. 현재 기준 농업용 면세유 유종별 가격 (원/리터)</div>", unsafe_allow_html=True)
input_kero = st.number_input(" - 면세 등유 가격", value=float(price_kero_taxfree) if price_kero_taxfree > 0 else 1000.0, step=10.0)
input_diesel = st.number_input(" - 면세 경유 가격", value=float(price_diesel_taxfree) if price_diesel_taxfree > 0 else 1100.0, step=10.0)
input_gas = st.number_input(" - 면세 휘발유 가격", value=float(price_gas_taxfree) if price_gas_taxfree > 0 else 1000.0, step=10.0)

other_expenses = st.number_input("라. 유류비 외 모든 지출액 (만원 / 이자 지출 포함)", value=4000, step=500)

selected_price = input_kero if fuel_type == "면세 등유" else (input_diesel if fuel_type == "면세 경유" else input_gas)

cost_fuel = (fuel_usage * selected_price) / 10000
fuel_ratio = (cost_fuel / revenue_this_month) * 100 if revenue_this_month > 0 else 0
profit_no_fuel = revenue_this_month - cost_fuel
net_profit = revenue_this_month - cost_fuel - other_expenses
max_fuel_cost = revenue_this_month - other_expenses

st.markdown("<div style='font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 10px;'>■ 유류비 감안 손익분기점 계산 결과</div>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #d1d5db;">
    <span style="font-size: 18px !important; color: #0044cc; font-weight: bold;">■ 이번 달 유류비 예상 지출: {cost_fuel:,.1f} 만원</span>
</div>
<div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #d1d5db;">
    <span style="font-size: 18px !important; color: #0044cc; font-weight: bold;">■ 이번 달 매출액 대비 유류비 비중: {fuel_ratio:,.1f} %</span>
</div>
<div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #d1d5db;">
    <span style="font-size: 18px !important; color: #0044cc; font-weight: bold;">■ 이번 달 유류비 제외한 수익 (매출액-유류비): {profit_no_fuel:,.1f} 만원</span>
</div>
<div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #d1d5db;">
    <span style="font-size: 18px !important; color: #0044cc; font-weight: bold;">■ 이번 달 모든 지출 제외한 순수익 (매출액-유류비-기타 모든 지출액): {net_profit:,.1f} 만원</span>
</div>
<div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #d1d5db;">
    <span style="font-size: 18px !important; color: #0044cc; font-weight: bold;">■ 임계소득 유류비 계산 결과 (기타 모든 지출액 고정 시 유류비 상한값): {max_fuel_cost:,.1f} 만원</span>
</div>
""", unsafe_allow_html=True)

if net_profit >= 600:
    st.markdown(f"""
    <div style="background-color: #0066cc; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #004085;">
        <span style="font-size: 18px !important; color: white; font-weight: bold;">■ 안정: 이번 달 순수익({net_profit:,.1f}만원)이 600만원 이상으로 안정적인 수익 구간입니다.</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="background-color: #dc3545; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #c82333;">
        <span style="font-size: 18px !important; color: white; font-weight: bold;">■ 위험 경고: 이번 달 순수익({net_profit:,.1f}만원)이 600만원 미만으로 떨어져 수익성 악화가 우려됩니다!</span>
    </div>
    """, unsafe_allow_html=True)