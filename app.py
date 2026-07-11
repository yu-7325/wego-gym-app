# app.py

import streamlit as st

st.set_page_config(page_title="We Go GYM", page_icon="🏋️", layout="centered")

import json
from datetime import datetime
import services
from views import nutrition, workout, body, recover, history, analytics

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

if "show_pr_balloons" in st.session_state and st.session_state.show_pr_balloons:
    st.balloons()
    st.success(st.session_state.new_pr_msg)
    st.session_state.show_pr_balloons = False

# 側邊欄控制中樞 (已整合地下室斷網防護機制)
with st.sidebar:
    st.header("⚙️ 系統控制中樞")
    if st.session_state.unsynced:
        st.warning("系統有尚未同步的變更。", icon="⚠️")
    else:
        st.success("所有資料皆已與雲端同步。", icon="☁️")
        
    if st.button("🔄 手動同步至雲端", type="primary", use_container_width=True):
        with st.spinner("正在安全打包數據上傳 Google Sheets..."):
            success = services.save_data(
                st.session_state.nutrition_entries, st.session_state.workout_entries,
                st.session_state.body_entries, st.session_state.custom_exercises
            )
        if success:
            st.toast("☁️ 雲端備份成功！", icon="✅")
            st.session_state.unsynced = False
            st.rerun()
        else:
            # 🛡️ 離線機制 UI 觸發：不崩潰、不重置，安全保留在本地端
            st.error("📡 訊號微弱連線失敗！已啟動【地下室離線防護】，數據已安全保存在本地記憶體中。回到地面後再次點擊即可同步！")
        
    st.divider()
    st.subheader("💾 雙重備份系統")
    backup_data = {
        "nutrition": st.session_state.nutrition_entries,
        "workout": st.session_state.workout_entries,
        "body_metrics": st.session_state.body_entries,
        "custom_exercises": st.session_state.custom_exercises
    }
    
    # 🔥 已經修復 Bug：將 json_backup 改回官方正確的 data 參數
    st.download_button(
        label="📥 下載完整資料庫 (JSON)", 
        data=json.dumps(backup_data, ensure_ascii=False, indent=2),
        file_name=f"WeGoGYM_Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json", 
        use_container_width=True
    )

st.title("We Go GYM ☁️")
if st.session_state.unsynced:
    st.info("💡 提示：您有尚未同步的紀錄，訓練結束後請打開左上角選單 `>` 進行雲端同步！", icon="💾")

tab_nutri, tab_work, tab_body, tab_recover, tab_hist, tab_analytics = st.tabs([
    "🍃 飲食", "🏋️ 課表", "⚖️ 體重", "💪 恢復", "🕒 歷史", "📈 數據"
])

with tab_nutri: nutrition.render()
with tab_work: workout.render()
with tab_body: body.render()
with tab_recover: recover.render()
with tab_hist: history.render()
with tab_analytics: analytics.render()
