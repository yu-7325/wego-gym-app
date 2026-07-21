# app.py

import streamlit as st

st.set_page_config(page_title="We Go GYM", page_icon="🏋️", layout="centered")

import json
from datetime import datetime
import services
# 🔥 記得導入最新的 gallery 模組
from views import nutrition, workout, body, recover, history, analytics, gallery

# 狀態安全初始化
if "current_goal" not in st.session_state: st.session_state.current_goal = "🥩 增肌期 (Hypertrophy)"
if "nutrition_entries" not in st.session_state: st.session_state.nutrition_entries = []
if "workout_entries" not in st.session_state: st.session_state.workout_entries = []
if "body_entries" not in st.session_state: st.session_state.body_entries = []
if "custom_exercises" not in st.session_state: st.session_state.custom_exercises = {}
# 🔥 初始化圖庫狀態
if "gallery_entries" not in st.session_state: st.session_state.gallery_entries = []
if "active_routine" not in st.session_state: st.session_state.active_routine = "4日力量與有氧 (目前)"
if "unsynced" not in st.session_state: st.session_state.unsynced = False

# 預設記憶分頁，鎖定在課表頁面
if "active_tab" not in st.session_state: st.session_state.active_tab = "🏋️ 課表"

if "data_loaded" not in st.session_state:
    with st.spinner("🔄 正在與 Google 雲端資料庫同步中..."):
        data = services.load_data()
        st.session_state.nutrition_entries = data.get("nutrition", [])
        st.session_state.workout_entries = data.get("workout", [])
        st.session_state.body_entries = data.get("body_metrics", [])
        st.session_state.custom_exercises = data.get("custom_exercises", {})
        # 🔥 載入圖庫資料
        st.session_state.gallery_entries = data.get("gallery", [])
        st.session_state.data_loaded = True

if "show_pr_balloons" in st.session_state and st.session_state.show_pr_balloons:
    st.balloons()
    st.success(st.session_state.new_pr_msg)
    st.session_state.show_pr_balloons = False

with st.sidebar:
    st.header("⚙️ 系統控制中樞")
    
    st.subheader("🎯 當前週期目標")
    goal_options = [
        "🥩 增肌期 (Hypertrophy)", 
        "⚡ 力量/爆發力期 (Strength/Power)", 
        "🔥 減脂期 (Cutting)", 
        "🩹 復健/活動度期 (Rehab)"
    ]
    # 確保不會因為目標變動而報錯
    current_idx = goal_options.index(st.session_state.current_goal) if st.session_state.current_goal in goal_options else 0
    st.session_state.current_goal = st.selectbox("切換大週期狀態", goal_options, index=current_idx)
    st.divider()
    
    if st.session_state.unsynced:
        st.warning("系統有尚未同步的變更。", icon="⚠️")
    else:
        st.success("所有資料皆已與雲端同步。", icon="☁️")
        
    if st.button("🔄 手動同步至雲端", type="primary", use_container_width=True):
        with st.spinner("正在安全打包數據上傳 Google Sheets..."):
            success = services.save_data(
                st.session_state.nutrition_entries, 
                st.session_state.workout_entries,
                st.session_state.body_entries, 
                st.session_state.custom_exercises,
                st.session_state.gallery_entries  # 🔥 將圖庫資料一起打包上傳
            )
        if success:
            st.toast("☁️ 雲端備份成功！", icon="✅")
            st.session_state.unsynced = False
            st.rerun()
        else:
            st.error("📡 訊號微弱連線失敗！已啟動【地下室離線防護】，數據已安全保存在本地記憶體中。回到地面後再次點擊即可同步！")
        
    st.divider()
    st.subheader("💾 雙重備份系統")
    backup_data = {
        "nutrition": st.session_state.nutrition_entries,
        "workout": st.session_state.workout_entries,
        "body_metrics": st.session_state.body_entries,
        "custom_exercises": st.session_state.custom_exercises,
        "gallery": st.session_state.gallery_entries  # 🔥 確保 JSON 備份檔也包含圖片編碼
    }
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

# ─── 綁定 Session State 的防跳脫導覽列 ───
# 🔥 加入 "📷 影像" 選項
tab_options = ["🍃 飲食", "🏋️ 課表", "⚖️ 體重", "💪 恢復", "🕒 歷史", "📈 數據", "📷 影像"]
selected_tab = st.radio("導覽列", tab_options, horizontal=True, label_visibility="collapsed", key="active_tab")
st.divider()

# 根據導覽列狀態渲染對應視圖
if selected_tab == "🍃 飲食": nutrition.render()
elif selected_tab == "🏋️ 課表": workout.render()
elif selected_tab == "⚖️ 體重": body.render()
elif selected_tab == "💪 恢復": recover.render()
elif selected_tab == "🕒 歷史": history.render()
elif selected_tab == "📈 數據": analytics.render()
elif selected_tab == "📷 影像": gallery.render()  # 🔥 渲染圖庫視圖
