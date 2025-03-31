import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="ブロイラー体重測定アプリ", layout="wide")

# 🔐 Google Sheets 認証
SERVICE_ACCOUNT_FILE = 'angular-yen-455321-q0-c4d5a8728ad8.json'
SPREADSHEET_ID = '1SJGu0vnjZwXqRYcJUgug2JoO78iI8MSEtWWZbhMNLHU'

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(credentials)

@st.cache_resource
def get_sheet():
    return client.open_by_key(SPREADSHEET_ID).sheet1

sheet = get_sheet()

# 🌟 UI 設定
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        .button-row button {
            border-radius: 8px;
            font-weight: bold;
        }
        .header-container {
            display: flex;
            align-items: center;
            margin-top: 30px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-container">
        <h1>🐔 ブロイラー体重測定</h1>
    </div>
""", unsafe_allow_html=True)

# 📅 測定日入力
today = st.date_input("測定日を選んでください", datetime.date.today())
farm = st.selectbox("農場名を選んでください", ["緒川", "安達", "羽石", "真原"])

# 農場別の鶏舎数
def get_houses(farm_name):
    if farm_name == "安達":
        return [str(i) for i in range(1, 9)]  # 1~8
    else:
        return [str(i) for i in range(1, 6)]  # 1~5

house = st.selectbox("鶏舎番号を選んでください", get_houses(farm))

# 日齢入力
day_age = st.selectbox("日齢を選択", list(range(0, 56)))

# ✅ 測定羽数切り替え
st.header("🐤 測定データ入力")
num_birds = 30
is_half = st.checkbox("今回は15羽だけ測定した", value=False)
if is_half:
    num_birds = 15

weights = []
if is_half:
    st.subheader("無鑑別")
    for i in range(num_birds):
        weight = st.number_input(f"無鑑別 {i+1} 羽目", min_value=0, step=1, format="%d")
        weights.append(weight)
else:
    cols = st.columns(2)
    with cols[0]:
        st.subheader("オス")
        for section in ["前方", "中央", "後方"]:
            st.markdown(f"**{section}**")
            for i in range(5):
                weight = st.number_input(f"{section} オス {i+1} 羽目", min_value=0, step=1, format="%d")
                weights.append(weight)
    with cols[1]:
        st.subheader("メス")
        for section in ["前方", "中央", "後方"]:
            st.markdown(f"**{section}**")
            for i in range(5):
                weight = st.number_input(f"{section} メス {i+1} 羽目", min_value=0, step=1, format="%d")
                weights.append(weight)

# ✅ 集計と送信ボタン
if st.button("集計"):
    measured_weights = [w for w in weights if w > 0]
    avg_weight = round(sum(measured_weights) / len(measured_weights), 1) if measured_weights else 0
    variance = pd.Series(measured_weights).std() / avg_weight * 100 if avg_weight else 0

    st.subheader("📊 結果サマリー")
    st.write(f"測った鶏の数: {len(measured_weights)} 羽")
    st.write(f"平均体重: {avg_weight} g, CV値: {round(variance, 1)}%")

if st.button("結果を送信"):
    avg_weight = round(sum(weights) / len(weights), 1) if weights else 0
    variance = pd.Series(weights).std() / avg_weight * 100 if avg_weight else 0
    try:
        row = [str(today), farm, house, day_age, avg_weight, round(variance, 1), len(weights), str(weights)]
        sheet.append_row(row)
        st.success("✅ データをスプレッドシートに送信しました！")
    except Exception as e:
        st.error(f"❌ データ送信に失敗しました: {e}")
