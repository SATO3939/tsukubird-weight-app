import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import os

# Renderの環境変数として設定した値を読み込む
service_account_info = json.loads(os.getenv('broiler-taisoku-45883b87495b.json'))

# スコープの設定（Google Sheets APIの範囲）
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# 認証に使うコード
credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)

# Google Sheets APIのクライアントを作成
client = gspread.authorize(credentials)

# ここからはクライアントを使ってGoogle Sheetsにアクセスする処理


# 雛体重記憶ファイル
CHICK_WEIGHT_FILE = "chick_weight.json"

# 雛体重の読み込み／保存
def load_chick_weights():
    if os.path.exists(CHICK_WEIGHT_FILE):
        with open(CHICK_WEIGHT_FILE, "r") as f:
            return json.load(f)
    return {}

def save_chick_weight(farm, house, weight):
    data = load_chick_weights()
    key = f"{farm}-{house}"
    data[key] = weight
    with open(CHICK_WEIGHT_FILE, "w") as f:
        json.dump(data, f)

# 成長倍率の目標（週齢基準）
target_ratios = {
    1: 5,
    2: 12,
    3: 23,
    4: 37,
    5: 52,
    6: 68,
    7: 83
}

st.set_page_config(page_title="ブロイラー体重測定", layout="wide")
st.title("🐤 ブロイラー体重測定")

# --- 入力エリア ---
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("📅 測定日", value=datetime.date.today())
        age = st.number_input("日齢", 0, 55, step=1, key="age_input")
    with col2:
        farm = st.selectbox("農場名", ["緒川", "安達", "羽石", "真原"])
        max_house = 8 if farm == "安達" else 5
        house = st.selectbox("鶏舎番号", list(range(1, max_house+1)))
    with col3:
        chick_weights = load_chick_weights()
        key = f"{farm}-{house}"
        default_weight = chick_weights.get(key, 0)
        chick_weight = st.number_input("雛時体重（g）", 0, 100, value=default_weight, step=1, key="chick_input")
        if st.button("🐣 雛体重を保存"):
            save_chick_weight(farm, house, chick_weight)
            st.success("雛体重を保存しました！")

# --- 測定モード選択 ---
mode_15 = st.checkbox("15羽（無鑑別）モード", value=(age <= 7))

# --- 体重入力エリア ---
weights = []

def weight_input(label, key):
    return st.number_input(label, min_value=0, step=1, key=key, label_visibility="collapsed")

st.divider()
if mode_15:
    st.subheader("体重入力（15羽・無鑑別）")
    for pos in ["前方", "中央", "後方"]:
        with st.expander(f"{pos}入力", expanded=True):
            cols = st.columns(5)
            for i in range(5):
                with cols[i]:
                    w = weight_input(f"{pos} {i+1}", f"{pos}_w{i}")
                    weights.append(w)
else:
    st.subheader("体重入力（30羽：オス・メス × 前中後）")
    for pos in ["前方", "中央", "後方"]:
        with st.expander(f"{pos}入力", expanded=True):
            cols = st.columns(2)
            for i in range(5):
                with cols[0]:
                    m = st.number_input(f"オス{i+1}", min_value=0, step=1, key=f"{pos}_m{i}")
                    weights.append(m)
                with cols[1]:
                    f = st.number_input(f"メス{i+1}", min_value=0, step=1, key=f"{pos}_f{i}")
                    weights.append(f)

# --- 集計処理 ---
st.divider()
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
    st.session_state.row_data = None

if st.button("📊 集計して表示"):
    valid = [w for w in weights if w > 0]
    count = len(valid)
    avg = round(np.mean(valid), 2) if valid else 0
    std = np.std(valid) if valid else 0
    cv = round((std / avg) * 100, 2) if avg else 0

    week = age // 7
    target = target_ratios.get(week, 0)
    ratio = round(avg / chick_weight, 2) if chick_weight else 0
    diff = round(((ratio - target) / target) * 100, 2) if target else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("測定数", count)
    with c2:
        st.metric("平均体重", f"{avg} g")
    with c3:
        st.metric("CV値", f"{cv} %")

    r1, r2 = st.columns(2)
    with r1:
        st.info(f"成長倍率：{ratio} 倍（目標 {target}）")
    with r2:
        st.info(f"乖離率：{diff} %")

    row_data = [
        str(date), farm, house, age, chick_weight,
        avg, cv, ratio, diff, count,
        ",".join(str(w) for w in weights)
    ]
    st.session_state.calculated = True
    st.session_state.row_data = row_data

# --- 送信処理 ---
if st.session_state.calculated:
    st.divider()
    if st.button("📤 スプレッドシートに送信"):
        # 認証設定
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(credentials)

        # スプレッドシートに接続
        sheet = client.open("taisoku2").sheet1  # ここでスプレッドシート名を指定

        # 測定データを送信
        sheet.append_row(row_data)

        # 成功メッセージ
        st.success("✅ 測定データがスプレッドシートに送信されました！")
