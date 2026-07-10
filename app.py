import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import uuid
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. 常數與多維度課表設定
# ==========================================
MEAL_TYPES = ["早餐", "午餐", "練前餐", "練後餐", "晚餐", "宵夜"]
SHEET_NAME = "WeGoGYM_Database" # 雲端資料庫名稱

WORKOUT_MUSCLE_MAPPING = {
    "Chest Day": ["Chest", "Triceps", "Shoulders"],
    "Back Day": ["Back", "Biceps", "Forearms"],
    "Leg Day": ["Legs", "Abs"],
    "Power Day": ["Abs", "Back", "Legs"],
    "Chest+Tricep": ["Chest", "Triceps"],
    "Back+Biceps": ["Back", "Biceps"],
    "Shoulder+Chest": ["Shoulders", "Chest"],
    "Hamstring+Back": ["Legs", "Back"],
    "Arm Day": ["Biceps", "Triceps", "Forearms"],
    "Cardio": []
}

MUSCLE_GROUPS = {
    "Chest": {"recovery_hours": 48}, "Back": {"recovery_hours": 72},
    "Legs": {"recovery_hours": 72}, "Abs": {"recovery_hours": 24},
    "Biceps": {"recovery_hours": 24}, "Shoulders": {"recovery_hours": 48},
    "Triceps": {"recovery_hours": 48}, "Forearms": {"recovery_hours": 24}
}

ROUTINE_PLANS = {
    "4日力量與有氧 (目前)": {
        "days": ["Chest Day", "Back Day", "Leg Day", "Power Day", "Cardio"],
        "exercises": {
            "Chest Day": ["槓鈴臥推", "機械胸推", "上斜臥推", "肩推", "側平舉&飛鳥", "機械夾胸", "繩索下拉", "壺鈴三頭", "機械卷腹"],
            "Back Day": ["引體向上", "機械上背", "機械下背", "機械下拉", "直臂下拉", "繩索面拉", "反式飛鳥", "二頭彎舉", "機械卷腹"],
            "Leg Day": ["深蹲", "腿推機", "保加利亞", "RDL", "北歐彎舉", "負重提踵", "機械卷腹"],
            "Power Day": ["Clean", "Snatch", "六角槓硬舉", "壺鈴swing", "藥球下砸", "機械卷腹"],
            "Cardio": ["跑步機", "飛輪", "滑步機", "登階機", "跳繩", "戶外跑"]
        }
    },
    "6日健美分化 (新計畫)": {
        "days": ["Leg Day", "Chest+Tricep", "Back+Biceps", "Shoulder+Chest", "Hamstring+Back", "Arm Day", "Cardio"],
        "exercises": {
            "Leg Day": ["深蹲", "腿推機", "保加利亞", "坐姿腿伸展", "負重提踵", "機械卷腹"],
            "Chest+Tricep": ["槓鈴臥推", "上斜臥推", "機械胸推", "雙槓撐體", "繩索下拉", "機械卷腹"],
            "Back+Biceps": ["引體向上", "機械下拉", "機械上背", "機械下背", "單臂亞鈴划船", "二頭彎舉", "機械卷腹"],
            "Shoulder+Chest": ["肩推", "側平舉&飛鳥", "反式飛鳥", "啞鈴前平舉", "機械夾胸", "機械卷腹"],
            "Hamstring+Back": ["RDL", "北歐彎舉", "六角槓硬舉", "俯臥腿彎舉", "直臂下拉", "機械卷腹"],
            "Arm Day": ["壺鈴三頭", "二頭彎舉", "繩索面拉", "牧師凳彎舉", "碎顱式", "機械卷腹"],
            "Cardio": ["跑步機", "飛輪", "滑步機", "登階機", "跳繩", "戶外跑"]
        }
    }
}

# ==========================================
# 2. 雲端資料庫串接 (取代原本的 JSON 存取)
# ==========================================
@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def ensure_worksheets(sh):
    expected_sheets = ["Nutrition", "Workout", "CustomExercises"]
    existing_sheets = [ws.title for ws in sh.worksheets()]
    for ws_name in expected_sheets:
        if ws_name not in existing_sheets:
            sh.add_worksheet(title=ws_name, rows="1000", cols="20")

def load_data():
    gc = get_gsheet_client()
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"找不到名為 '{SHEET_NAME}' 的試算表。請確認已在雲端硬碟建立，並將權限設為『編輯者』共用給服務帳戶！")
        st.stop()
        
    ensure_worksheets(sh)
    
    # 讀取飲食
    ws_nutri = sh.worksheet("Nutrition")
    nutri_records = ws_nutri.get_all_records()
    for r in nutri_records:
        r["foodName"] = r["foodName"] if r["foodName"] != "" else None
        
    # 讀取課表
    ws_work = sh.worksheet("Workout")
    work_records = ws_work.get_all_records()
    for r in work_records:
        r["duration"] = float(r["duration"]) if r["duration"] != "" else None
        r["distance"] = float(r["distance"]) if r["distance"] != "" else None
        r["notes"] = str(r["notes"]) if r["notes"] != "" else None
        
    # 讀取自訂動作
    ws_custom = sh.worksheet("CustomExercises")
    custom_records = ws_custom.get_all_records()
    custom_dict = {}
    for r in custom_records:
        plan_day = r.get("plan_day")
        ex = r.get("exercise_name")
        if plan_day not in custom_dict:
            custom_dict[plan_day] = []
        custom_dict[plan_day].append(ex)

    return {
        "nutrition": nutri_records,
        "workout": work_records,
        "custom_exercises": custom_dict
    }

def update_worksheet(ws, data_list, default_headers):
    ws.clear()
    if not data_list:
        ws.update([default_headers])
        return
    
    headers = list(data_list[0].keys())
    rows = []
    for row_dict in data_list:
        row = []
        for h in headers:
            val = row_dict.get(h)
            row.append(val if val is not None else "")
        rows.append(row)
        
    ws.update([headers] + rows)

def save_data():
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    
    ws_nutri = sh.worksheet("Nutrition")
    update_worksheet(ws_nutri, st.session_state.nutrition_entries, ["id", "date", "type", "foodName", "protein", "carbs", "fat", "calories"])
    
    ws_work = sh.worksheet("Workout")
    update_worksheet(ws_work, st.session_state.workout_entries, ["id", "date", "dayType", "exercise", "weight", "sets", "reps", "distance", "duration", "notes"])
    
    ws_custom = sh.worksheet("CustomExercises")
    custom_list = [{"plan_day": pd, "exercise_name": ex} for pd, ex_list in st.session_state.custom_exercises.items() for ex in ex_list]
    update_worksheet(ws_custom, custom_list, ["plan_day", "exercise_name"])

# 系統啟動與資料載入
if "data_loaded" not in st.session_state:
    with st.spinner("🔄 正在與 Google 雲端資料庫同步中..."):
        data = load_data()
        st.session_state.nutrition_entries = data.get("nutrition", [])
        st.session_state.workout_entries = data.get("workout", [])
        st.session_state.custom_exercises = data.get("custom_exercises", {})
        st.session_state.active_routine = "4日力量與有氧 (目前)"
        st.session_state.data_loaded = True

def get_today_str(): return datetime.now().strftime("%Y-%m-%d")

def get_last_workout_data(exercise_name):
    sorted_workouts = sorted(st.session_state.workout_entries, key=lambda x: x["date"], reverse=True)
    for w in sorted_workouts:
        if w["exercise"] == exercise_name and w.get("dayType") != "Cardio":
            return w["weight"], w["sets"], w["reps"]
    return 0.0, 0, 0 

def calculate_muscle_statuses():
    now = datetime.now()
    statuses = []
    sorted_workouts = sorted(st.session_state.workout_entries, key=lambda x: x["date"], reverse=True)
    
    for muscle, info in MUSCLE_GROUPS.items():
        latest_date = None
        for w in sorted_workouts:
            day_type = w["dayType"]
            if muscle in WORKOUT_MUSCLE_MAPPING.get(day_type, []):
                latest_date = datetime.fromisoformat(w["date"])
                break
        
        hours_needed = info["recovery_hours"]
        if latest_date is None:
            progress = 1.0; remaining = 0.0; color = "green"
        else:
            elapsed_hours = (now - latest_date).total_seconds() / 3600.0
            progress = min(elapsed_hours / hours_needed, 1.0)
            remaining = max(hours_needed - elapsed_hours, 0.0)
            if progress >= 0.75: color = "green"
            elif progress >= 0.25: color = "orange"
            else: color = "red"
                
        statuses.append({
            "muscle": muscle, "latest_date": latest_date,
            "progress": progress, "remaining": remaining, "color": color
        })
    return statuses

# ==========================================
# 主視圖
# ==========================================
st.set_page_config(page_title="We Go GYM", page_icon="🏋️", layout="centered")
st.title("We Go GYM ☁️") # 加上雲端符號標示升級成功

tab_nutri, tab_work, tab_recover, tab_hist_nutri, tab_hist_work, tab_analytics = st.tabs([
    "🍃 飲食", "🏋️ 課表", "💪 恢復圖", "📊 飲食記錄", "🕒 重訓記錄", "📈 數據"
])

# ==========================================
# 4. 今日飲食 
# ==========================================
with tab_nutri:
    st.header("新增攝取")
    selected_date_n = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="nutri_date")
    
    st.subheader("⚡ 快速加入")
    col_q1, col_q2 = st.columns([1, 2])
    with col_q1:
        quick_meal = st.selectbox("快速加入時段", MEAL_TYPES, index=3, label_visibility="collapsed")
    with col_q2:
        if st.button("➕ 加入乳清蛋白一匙 (120 kcal)"):
            entry_date = datetime.combine(selected_date_n, datetime.now().time()).isoformat()
            st.session_state.nutrition_entries.append({
                "id": str(uuid.uuid4()), "date": entry_date,
                "type": quick_meal, "foodName": "乳清蛋白",
                "protein": 25.0, "carbs": 2.0, "fat": 1.5, "calories": 120.0
            })
            with st.spinner("同步至雲端中..."): save_data()
            st.success(f"已將乳清蛋白加入至 {quick_meal}！")
            st.rerun()
            
    st.subheader("✍️ 手動輸入")
    with st.form("nutrition_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_meal = st.selectbox("餐點時段", MEAL_TYPES)
            input_food_name = st.text_input("食物 (例如：雞胸肉便當)")
            input_calories = st.number_input("熱量 (kcal)", min_value=0.0, step=1.0)
        with col2:
            input_protein = st.number_input("蛋白質 (g)", min_value=0.0, step=0.1)
            input_carbs = st.number_input("碳水 (g)", min_value=0.0, step=0.1)
            input_fat = st.number_input("脂肪 (g)", min_value=0.0, step=0.1)
            
        if st.form_submit_button("加入紀錄") and input_calories > 0:
            entry_date = datetime.combine(selected_date_n, datetime.now().time()).isoformat()
            st.session_state.nutrition_entries.append({
                "id": str(uuid.uuid4()), "date": entry_date,
                "type": selected_meal, "foodName": input_food_name if input_food_name else None,
                "protein": input_protein, "carbs": input_carbs, "fat": input_fat, "calories": input_calories
            })
            with st.spinner("同步至雲端中..."): save_data()
            st.success("已加入紀錄！")
            st.rerun()

    st.divider()
    
    target_date_str = selected_date_n.strftime("%Y-%m-%d")
    today_nutri = [e for e in st.session_state.nutrition_entries if e["date"].startswith(target_date_str)]
    total_cal = sum(e["calories"] for e in today_nutri)
    total_p = sum(e["protein"] for e in today_nutri)
    total_c = sum(e["carbs"] for e in today_nutri)
    total_f = sum(e["fat"] for e in today_nutri)
    
    st.subheader(f"清單總計 ({target_date_str}): {total_cal:.0f} kcal")
    st.markdown(f"**🔥 日總計 ➔ 碳水: {total_c:.1f}g | 蛋白質: {total_p:.1f}g | 脂肪: {total_f:.1f}g**")
    
    for entry in today_nutri:
        with st.container():
            col_a, col_b, col_c = st.columns([1, 3, 1])
            with col_a: 
                st.info(entry["type"])
            with col_b:
                if entry.get("foodName"): 
                    st.write(f"**{entry['foodName']}**")
                st.caption(f"碳水: {entry['carbs']:.1f}g | 蛋白質: {entry['protein']:.1f}g | 脂肪: {entry['fat']:.1f}g")
            with col_c:
                st.write(f"**{entry['calories']:.0f} kcal**")
                if st.button("❌", key=f"del_nutri_{entry['id']}"):
                    st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != entry["id"]]
                    with st.spinner("同步至雲端中..."): save_data()
                    st.rerun()

# ==========================================
# 5. 今日課表
# ==========================================
with tab_work:
    st.header("新增訓練動作")
    
    selected_date_w = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="work_date")
    
    st.session_state.active_routine = st.selectbox(
        "當前執行課表", 
        list(ROUTINE_PLANS.keys()),
        index=list(ROUTINE_PLANS.keys()).index(st.session_state.active_routine)
    )
    
    current_plan = ROUTINE_PLANS[st.session_state.active_routine]
    selected_day = st.selectbox("訓練日", current_plan["days"])
    
    base_exercises = current_plan["exercises"].get(selected_day, [])
    custom_key = f"{st.session_state.active_routine}_{selected_day}"
    custom_exercises = st.session_state.custom_exercises.get(custom_key, [])
    
    exercise_options = base_exercises + custom_exercises + ["➕ 新增動作..."]
    selected_ex = st.selectbox("動作", exercise_options)
    
    if selected_ex == "➕ 新增動作...":
        new_ex = st.text_input("輸入新動作名稱")
        if st.button("新增動作") and new_ex:
            if custom_key not in st.session_state.custom_exercises:
                st.session_state.custom_exercises[custom_key] = []
            if new_ex not in st.session_state.custom_exercises[custom_key] and new_ex not in base_exercises:
                st.session_state.custom_exercises[custom_key].append(new_ex)
                with st.spinner("同步至雲端中..."): save_data()
                st.rerun()

    last_w, last_s, last_r = get_last_workout_data(selected_ex)

    with st.form("workout_form", clear_on_submit=False):
        if selected_day == "Cardio" or selected_ex in ["跑步機", "戶外跑", "飛輪", "滑步機", "登階機", "跳繩"]:
            col1, col2 = st.columns(2)
            with col1:
                input_dist = st.number_input("距離 (km)", min_value=0.0, step=0.5, value=42.195)
            with col2:
                input_dur = st.number_input("時長 (分鐘)", min_value=0.0, step=1.0, value=170.0)
            
            if input_dist > 0 and input_dur > 0:
                pace = input_dur / input_dist
                pace_min = int(pace)
                pace_sec = int((pace - pace_min) * 60)
                st.info(f"🏃 目標均速約為 {pace_min}'{pace_sec:02d}\"/km")
                
            input_notes = st.text_input("備註 (例如：心率區間或次數)")
            
            if st.form_submit_button("加入課表") and input_dur > 0 and selected_ex != "➕ 新增動作...":
                entry_date = datetime.combine(selected_date_w, datetime.now().time()).isoformat()
                entry = {
                    "id": str(uuid.uuid4()), "date": entry_date,
                    "dayType": selected_day, "exercise": selected_ex,
                    "distance": input_dist, "duration": input_dur, "notes": input_notes,
                    "weight": 0.0, "sets": 0, "reps": 0
                }
                st.session_state.workout_entries.append(entry)
                with st.spinner("同步至雲端中..."): save_data()
                st.success("已加入有氧紀錄！")
                
        else:
            if last_s > 0:
                st.caption(f"💡 上次紀錄：{last_w}kg | {last_s}組 x {last_r}下")
            col1, col2, col3 = st.columns(3)
            with col1:
                input_weight = st.number_input("重量 (kg)", min_value=0.0, step=2.5, value=float(last_w))
            with col2:
                input_sets = st.number_input("組數", min_value=0, step=1, value=int(last_s) if last_s > 0 else 4)
            with col3:
                input_reps = st.number_input("次數 (下)", min_value=0, step=1, value=int(last_r) if last_r > 0 else 8)
                
            if st.form_submit_button("加入課表") and input_sets > 0 and input_reps > 0 and selected_ex != "➕ 新增動作...":
                entry_date = datetime.combine(selected_date_w, datetime.now().time()).isoformat()
                entry = {
                    "id": str(uuid.uuid4()), "date": entry_date,
                    "dayType": selected_day, "exercise": selected_ex,
                    "weight": input_weight, "sets": input_sets, "reps": input_reps,
                    "duration": None, "distance": None, "notes": None
                }
                st.session_state.workout_entries.append(entry)
                with st.spinner("同步至雲端中..."): save_data()
                st.success("已加入重訓紀錄！")

    st.divider()
    target_date_w_str = selected_date_w.strftime("%Y-%m-%d")
    today_work = [e for e in st.session_state.workout_entries if e["date"].startswith(target_date_w_str)]
    st.subheader(f"課表清單 ({target_date_w_str})")
    
    if not today_work:
        st.write("尚未新增動作")
    else:
        df_work = pd.DataFrame(today_work)
        for day, group in df_work.groupby("dayType"):
            st.markdown(f"#### {day}")
            for ex, ex_group in group.groupby("exercise"):
                st.markdown(f"**{ex}**")
                for _, row in ex_group.iterrows():
                    col_x, col_y, col_z = st.columns([3, 2, 1])
                    with col_x:
                        if row.get("duration") is not None:
                            notes = f" ({row['notes']})" if row.get('notes') else ""
                            st.write(f"⏱️ {row['duration']:.0f} 分鐘{notes}")
                        else:
                            st.write(f"🏋️ {row['weight']:.1f} kg")
                    with col_y:
                        if row.get("duration") is not None:
                            if row.get('distance', 0) > 0: st.write(f"{row['distance']:.1f} km")
                        else:
                            st.write(f"**{int(row['sets'])} 組 x {int(row['reps'])} 下**")
                    with col_z:
                        if st.button("❌", key=f"del_work_{row['id']}"):
                            st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                            with st.spinner("同步至雲端中..."): save_data()
                            st.rerun()

# ==========================================
# 6. 身體恢復圖 
# ==========================================
with tab_recover:
    st.header("人體恢復狀態儀表板")
    color_map = {"red": "🔴", "orange": "🟠", "green": "🟢"}
    statuses = calculate_muscle_statuses()
    for status in statuses:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"### {color_map[status['color']]} {status['muscle']}")
            if status['latest_date']: st.caption(f"上次訓練: {status['latest_date'].strftime('%Y-%m-%d %H:%M')}")
            else: st.caption("無訓練紀錄")
        with col2:
            if status['remaining'] <= 0: st.write("**已恢復**")
            else:
                h = int(status['remaining'])
                m = int((status['remaining'] - h) * 60)
                st.write(f"**剩餘: {h}時{m}分**")
        st.progress(status['progress'])
        st.write("---")

# ==========================================
# 7. 飲食記錄 
# ==========================================
with tab_hist_nutri:
    st.header("歷史飲食記錄")
    if not st.session_state.nutrition_entries:
        st.write("尚未有任何飲食紀錄")
    else:
        df_nutri = pd.DataFrame(st.session_state.nutrition_entries)
        df_nutri['date_str'] = df_nutri['date'].str[:10]
        grouped_nutri = df_nutri.groupby('date_str', sort=False)
        dates_sorted = sorted(grouped_nutri.groups.keys(), reverse=True)
        
        for date in dates_sorted:
            group = grouped_nutri.get_group(date)
            total_c = group['calories'].sum()
            with st.expander(f"📅 {date} | 總熱量: {total_c:.0f} kcal", expanded=True):
                st.markdown(f"**🔥 日總計 ➔ 碳水: {group['carbs'].sum():.1f}g | 蛋白質: {group['protein'].sum():.1f}g | 脂肪: {group['fat'].sum():.1f}g**")
                st.divider()
                for _, row in group.iterrows():
                    col_x, col_y = st.columns([4, 1])
                    with col_x:
                        food_desc = f" - {row['foodName']}" if row.get('foodName') else ""
                        st.write(f"**{row['type']}**{food_desc} : {row['calories']:.0f} kcal")
                        st.caption(f"碳水: {row['carbs']:.1f}g | 蛋白質: {row['protein']:.1f}g | 脂肪: {row['fat']:.1f}g")
                    with col_y:
                        if st.button("❌", key=f"del_h_n_{row['id']}"):
                            st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != row["id"]]
                            with st.spinner("同步至雲端中..."): save_data()
                            st.rerun()

# ==========================================
# 8. 重訓課表記錄
# ==========================================
with tab_hist_work:
    st.header("歷史重訓記錄")
    if not st.session_state.workout_entries:
        st.write("尚未有任何訓練紀錄")
    else:
        df_work_hist = pd.DataFrame(st.session_state.workout_entries)
        df_work_hist['date_str'] = df_work_hist['date'].str[:10]
        grouped_work = df_work_hist.groupby('date_str', sort=False)
        dates_sorted = sorted(grouped_work.groups.keys(), reverse=True)
        
        for date in dates_sorted:
            group = grouped_work.get_group(date)
            day_types = ", ".join(group['dayType'].unique())
            with st.expander(f"📅 {date} | {day_types}"):
                for ex, ex_group in group.groupby('exercise'):
                    st.write(f"**{ex}**")
                    for _, row in ex_group.iterrows():
                        col_x, col_y = st.columns([4, 1])
                        with col_x:
                            if row.get("duration") is not None:
                                notes = f" ({row['notes']})" if row.get('notes') else ""
                                st.write(f"- ⏱️ {row['duration']:.0f} 分鐘{notes}")
                            else:
                                st.write(f"- 🏋️ {row['weight']:.1f} kg | {int(row['sets'])} 組 x {int(row['reps'])} 下")
                        with col_y:
                            if st.button("❌", key=f"del_h_w_{row['id']}"):
                                st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                                with st.spinner("同步至雲端中..."): save_data()
                                st.rerun()

# ==========================================
# 9. 數據分析
# ==========================================
with tab_analytics:
    st.header("訓練總容量趨勢 (Total Volume)")
    
    if st.session_state.workout_entries:
        df_w = pd.DataFrame(st.session_state.workout_entries)
        if 'weight' in df_w.columns:
            df_weights = df_w[df_w['weight'] > 0].copy()
            
            if not df_weights.empty:
                time_interval = st.radio("選擇檢視區間：", ["日 (Daily)", "週 (Weekly)", "月 (Monthly)"], horizontal=True)
                
                df_weights['date_obj'] = pd.to_datetime(df_weights['date'].str[:10])
                df_weights['volume'] = df_weights['weight'] * df_weights['sets'] * df_weights['reps']
                
                if time_interval == "日 (Daily)":
                    df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m-%d')
                    x_title = "日期"
                elif time_interval == "週 (Weekly)":
                    df_weights['period'] = df_weights['date_obj'] - pd.to_timedelta(df_weights['date_obj'].dt.dayofweek, unit='d')
                    df_weights['period'] = df_weights['period'].dt.strftime('%Y-%m-%d (週一)')
                    x_title = "週度 (以週一為起點)"
                else: 
                    df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m')
                    x_title = "月份"
                
                vol_trend = df_weights.groupby('period')['volume'].sum().reset_index()
                
                chart = alt.Chart(vol_trend).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('period:O', title=x_title, sort=None), 
                    y=alt.Y('volume:Q', title='總容量 (kg)'),
                    tooltip=[alt.Tooltip('period', title=x_title), alt.Tooltip('volume', title='總容量')]
                ).properties(width=alt.Step(60))
                
                st.altair_chart(chart, use_container_width=True)
                st.caption("觀察重點：確保圖表呈現『漸進性超負荷』的緩步上升趨勢。")
            else:
                st.write("目前尚無重量訓練數據可供分析。")
    else:
        st.write("目前尚無任何訓練數據。")
