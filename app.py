# app.py

import streamlit as st

# 1. 網頁初始設定 (絕對第一行)
st.set_page_config(page_title="We Go GYM", page_icon="🏋️", layout="centered")

import json
from datetime import datetime
import services
from views import nutrition, workout, body, recover, history, analytics

# 狀態安全初始化
if "nutrition_entries" not in st.session_state: st.session_state.nutrition_entries = []
if "workout_entries" not in st.session_state: st.session_state.workout_entries = []
if "body_entries" not in st.session_state: st.session_state.body_entries = []
if "custom_exercises" not in st.session_state: st.session_state.custom_exercises = {}
if "active_routine" not in st.session_state: st.session_state.active_routine = "4日力量與有氧 (目前)"
if "unsynced" not in st.session_state: st.session_state.unsynced = False

if "data_loaded" not in st.session_state:
    with st.spinner("🔄 正在與 Google 雲端資料庫同步中..."):
        data = services.load_data()
        st.session_state.nutrition_entries = data.get("nutrition", [])
        st.session_state.workout_entries = data.get("workout", [])
        st.session_state.body_entries = data.get("body_metrics", [])
        st.session_state.custom_exercises = data.get("custom_exercises", {})
        st.session_state.data_loaded = True

def trigger_save():
    services.save_data(
        st.session_state.nutrition_entries, st.session_state.workout_entries,
        st.session_state.body_entries, st.session_state.custom_exercises
    )

if "show_pr_balloons" in st.session_state and st.session_state.show_pr_balloons:
    st.balloons()
    st.success(st.session_state.new_pr_msg)
    st.session_state.show_pr_balloons = False

# 側邊欄控制中樞
with st.sidebar:
    st.header("⚙️ 系統控制中樞")
    if st.session_state.unsynced:
        st.warning("系統有尚未同步的變更。請在離開前手動同步，以免資料遺失！", icon="⚠️")
    else:
        st.success("目前所有資料皆已與雲端同步。", icon="☁️")
        
    if st.button("🔄 手動同步至雲端", type="primary", use_container_width=True):
        with st.spinner("正在將資料安全批次寫入 Google Sheets..."):
            trigger_save()
        st.session_state.unsynced = False
        st.rerun()
        
    st.divider()
    st.subheader("💾 雙重備份系統")
    st.caption("為防止雲端 API 異常，您隨時可將完整資料庫下載至本機端安全保存。")
    backup_data = {
        "nutrition": st.session_state.nutrition_entries,
        "workout": st.session_state.workout_entries,
        "body_metrics": st.session_state.body_entries,
        "custom_exercises": st.session_state.custom_exercises
    }
    json_backup = json.dumps(backup_data, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 下載完整資料庫 (JSON)", data=json_backup,
        file_name=f"WeGoGYM_Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json", use_container_width=True
    )

st.title("We Go GYM ☁️")
if st.session_state.unsynced:
    st.info("💡 提示：您有尚未同步的紀錄，訓練結束後請打開左上角選單 `>` 進行雲端同步！", icon="💾")

tab_nutri, tab_work, tab_body, tab_recover, tab_hist, tab_analytics = st.tabs([
    "🍃 飲食", "🏋️ 課表", "⚖️ 體重", "💪 恢復", "🕒 歷史", "📈 數據"
])

# 路由渲染
with tab_nutri: nutrition.render()
with tab_work: workout.render()
with tab_body: body.render()
with tab_recover: recover.render()
with tab_hist: history.render()
with tab_analytics: analytics.render()
