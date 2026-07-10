import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import uuid

# ==========================================
# 1. 常數與資料設定 (對應 Models)
# ==========================================
DATA_FILE = "health_data.json"

MEAL_TYPES = ["早餐", "午餐", "練前餐", "練後餐", "晚餐", "宵夜"]
WORKOUT_DAYS = ["Chest Day", "Back Day", "Leg Day", "Power Day", "Cardio"]

MUSCLE_GROUPS = {
    "Chest": {"recovery_hours": 48},
    "Back": {"recovery_hours": 72},
    "Legs": {"recovery_hours": 72},
    "Abs": {"recovery_hours": 24},
    "Biceps": {"recovery_hours": 24},
    "Shoulders": {"recovery_hours": 48},
    "Triceps": {"recovery_hours": 48},
    "Forearms": {"recovery_hours": 24}
}

WORKOUT_MUSCLE_MAPPING = {
    "Chest Day": ["Chest", "Triceps", "Shoulders"],
    "Back Day": ["Back", "Biceps", "Forearms"],
    "Leg Day": ["Legs", "Abs"],
    "Power Day": ["Abs", "Back"],
    "Cardio": []
}

DEFAULT_EXERCISE_DICT = {
    "Chest Day": ["槓鈴臥推", "機械胸推", "上斜臥推", "肩推", "側平舉&飛鳥", "機械夾胸", "繩索下拉", "壺鈴三頭", "機械卷腹", "Cardio"],
    "Back Day": ["引體向上", "機械上背", "機械下背", "機械下拉", "直臂下拉", "繩索面拉", "反式飛鳥", "二頭彎舉", "機械卷腹", "Cardio"],
    "Leg Day": ["深蹲", "腿推機", "保加利亞", "RDL", "北歐彎舉", "負重提踵", "機械卷腹"],
    "Power Day": ["Clean", "Snatch", "六角槓硬舉", "壺鈴swing", "藥球下砸", "機械卷腹"],
    "Cardio": ["跑步機", "飛輪", "滑步機", "登階機", "跳繩"]
}

# ==========================================
# 2. 系統初始化與資料庫操作 (對應 HealthStore)
# ==========================================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nutrition": [], "workout": [], "exercise_dict": DEFAULT_EXERCISE_DICT}

def save_data():
    data_to_save = {
        "nutrition": st.session_state.nutrition_entries,
        "workout": st.session_state.workout_entries,
        "exercise_dict": st.session_state.exercise_dict
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)

if "data_loaded" not in st.session_state:
    data = load_data()
    st.session_state.nutrition_entries = data["nutrition"]
    st.session_state.workout_entries = data["workout"]
    st.session_state.exercise_dict = data["exercise_dict"]
    st.session_state.data_loaded = True

# Helper: 取得今日日期字串
def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# ==========================================
# 3. 肌肉恢復計算邏輯
# ==========================================
def calculate_muscle_statuses():
    now = datetime.now()
    statuses = []
    
    # 將所有訓練紀錄依時間排序 (由新到舊)
    sorted_workouts = sorted(
        st.session_state.workout_entries, 
        key=lambda x: x["date"], 
        reverse=True
    )
    
    for muscle, info in MUSCLE_GROUPS.items():
        latest_date = None
        # 尋找最近一次練到該肌肉的紀錄
        for w in sorted_workouts:
            day_type = w["dayType"]
            if muscle in WORKOUT_MUSCLE_MAPPING.get(day_type, []):
                latest_date = datetime.fromisoformat(w["date"])
                break
        
        hours_needed = info["recovery_hours"]
        
        if latest_date is None:
            progress = 1.0
            remaining = 0.0
            color = "green"
        else:
            elapsed_hours = (now - latest_date).total_seconds() / 3600.0
            progress = min(elapsed_hours / hours_needed, 1.0)
            remaining = max(hours_needed - elapsed_hours, 0.0)
            
            if progress >= 0.75:
                color = "green"
            elif progress >= 0.25:
                color = "orange"
            else:
                color = "red"
                
        statuses.append({
            "muscle": muscle,
            "latest_date": latest_date,
            "progress": progress,
            "remaining": remaining,
            "color": color
        })
    return statuses

# ==========================================
# 主視圖 (對應 ContentView 的 TabView)
# ==========================================
st.set_page_config(page_title="We Go GYM", page_icon="🏋️", layout="centered")
st.title("We Go GYM")

tab_nutri, tab_work, tab_recover, tab_hist_nutri, tab_hist_work = st.tabs([
    "🍃 今日飲食", "🏋️ 今日課表", "💪 恢復圖", "📊 飲食記錄", "🕒 重訓課表"
])

# ==========================================
# 4. 今日飲食 (對應 NutritionView)
# ==========================================
with tab_nutri:
    st.header("新增今日攝取")
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
            
        submitted = st.form_submit_button("加入紀錄")
        if submitted and input_calories > 0:
            entry = {
                "id": str(uuid.uuid4()),
                "date": datetime.now().isoformat(),
                "type": selected_meal,
                "foodName": input_food_name if input_food_name else None,
                "protein": input_protein,
                "carbs": input_carbs,
                "fat": input_fat,
                "calories": input_calories
            }
            st.session_state.nutrition_entries.append(entry)
            save_data()
            st.success("已加入紀錄！")
            st.rerun()

    st.divider()
    
    # 今日清單顯示
    today_str = get_today_str()
    today_nutri = [e for e in st.session_state.nutrition_entries if e["date"].startswith(today_str)]
    total_cal = sum(e["calories"] for e in today_nutri)
    
    st.subheader(f"今日清單 (總熱量: {total_cal:.0f} kcal)")
    for entry in today_nutri:
        with st.container():
            col_a, col_b, col_c = st.columns([1, 3, 1])
            with col_a:
                st.info(entry["type"])
            with col_b:
                if entry.get("foodName"):
                    st.write(entry["foodName"])
            with col_c:
                st.write(f"**{entry['calories']:.0f} kcal**")
                if st.button("❌", key=f"del_nutri_{entry['id']}", help="刪除"):
                    st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != entry["id"]]
                    save_data()
                    st.rerun()

# ==========================================
# 5. 今日課表 (對應 WorkoutView)
# ==========================================
with tab_work:
    st.header("新增訓練動作")
    
    # 處理新增自訂動作的邏輯 (寫在 Form 外面以便動態更新 Selectbox)
    selected_day = st.selectbox("訓練日", WORKOUT_DAYS)
    exercise_options = st.session_state.exercise_dict.get(selected_day, []) + ["➕ 新增動作..."]
    selected_ex = st.selectbox("動作", exercise_options)
    
    if selected_ex == "➕ 新增動作...":
        new_ex = st.text_input("輸入新動作名稱")
        if st.button("新增動作") and new_ex:
            if new_ex not in st.session_state.exercise_dict[selected_day]:
                st.session_state.exercise_dict[selected_day].append(new_ex)
                save_data()
                st.rerun()
                
    with st.form("workout_form", clear_on_submit=True):
        if selected_day == "Cardio":
            input_duration = st.number_input("時長 (分鐘)", min_value=0.0, step=1.0)
            input_reps_cardio = st.number_input("次數 (選填)", min_value=0, step=1)
            input_notes = st.text_input("備註 (例如：坡度5)")
            submitted_work = st.form_submit_button("加入課表")
            
            if submitted_work and input_duration > 0 and selected_ex != "➕ 新增動作...":
                entry = {
                    "id": str(uuid.uuid4()),
                    "date": datetime.now().isoformat(),
                    "dayType": selected_day,
                    "exercise": selected_ex,
                    "weight": 0.0, "sets": 0, "reps": input_reps_cardio,
                    "duration": input_duration, "notes": input_notes
                }
                st.session_state.workout_entries.append(entry)
                save_data()
                st.success("已加入有氧紀錄！")
                st.rerun()
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                input_weight = st.number_input("重量 (kg)", min_value=0.0, step=0.5)
            with col2:
                input_sets = st.number_input("組數", min_value=0, step=1)
            with col3:
                input_reps = st.number_input("次數 (下)", min_value=0, step=1)
                
            submitted_work = st.form_submit_button("加入課表")
            if submitted_work and input_sets > 0 and input_reps > 0 and selected_ex != "➕ 新增動作...":
                entry = {
                    "id": str(uuid.uuid4()),
                    "date": datetime.now().isoformat(),
                    "dayType": selected_day,
                    "exercise": selected_ex,
                    "weight": input_weight, "sets": input_sets, "reps": input_reps,
                    "duration": None, "notes": None
                }
                st.session_state.workout_entries.append(entry)
                save_data()
                st.success("已加入重訓紀錄！")
                st.rerun()

    st.divider()
    
    # 今日課表顯示
    today_work = [e for e in st.session_state.workout_entries if e["date"].startswith(today_str)]
    st.subheader("今日課表")
    if not today_work:
        st.write("尚未新增動作")
    else:
        # 將今日紀錄轉為 DataFrame 方便群組化顯示
        df_work = pd.DataFrame(today_work)
        for day, group in df_work.groupby("dayType"):
            st.markdown(f"#### {day}")
            for ex, ex_group in group.groupby("exercise"):
                st.markdown(f"**{ex}**")
                for _, row in ex_group.iterrows():
                    col_x, col_y, col_z = st.columns([3, 2, 1])
                    with col_x:
                        if row["dayType"] == "Cardio":
                            notes = f" ({row['notes']})" if row['notes'] else ""
                            st.write(f"⏱️ {row['duration']:.0f} 分鐘{notes}")
                        else:
                            st.write(f"🏋️ {row['weight']:.1f} kg")
                    with col_y:
                        if row["dayType"] == "Cardio":
                            st.write(f"{int(row['reps'])} 次" if row['reps'] > 0 else "")
                        else:
                            st.write(f"**{int(row['sets'])} 組 x {int(row['reps'])} 下**")
                    with col_z:
                        if st.button("❌", key=f"del_work_{row['id']}"):
                            st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                            save_data()
                            st.rerun()

# ==========================================
# 6. 身體恢復圖 (對應 BodyMapRecoveryView)
# ==========================================
with tab_recover:
    st.header("人體恢復狀態儀表板")
    
    color_map = {"red": "🔴", "orange": "🟠", "green": "🟢"}
    
    statuses = calculate_muscle_statuses()
    for status in statuses:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"### {color_map[status['color']]} {status['muscle']}")
            if status['latest_date']:
                st.caption(f"上次訓練: {status['latest_date'].strftime('%Y-%m-%d %H:%M')}")
            else:
                st.caption("無訓練紀錄")
        with col2:
            if status['remaining'] <= 0:
                st.write("**已恢復**")
            else:
                h = int(status['remaining'])
                m = int((status['remaining'] - h) * 60)
                st.write(f"**剩餘: {h}時{m}分**")
        st.progress(status['progress'])
        st.write("---")
        
    st.caption("💡 顏色說明：🔴 剛練完 ｜ 🟠 恢復中 ｜ 🟢 已恢復")

# ==========================================
# 7. 飲食記錄 (對應 NutritionHistoryView)
# ==========================================
with tab_hist_nutri:
    st.header("歷史飲食記錄")
    if not st.session_state.nutrition_entries:
        st.write("尚未有任何飲食紀錄")
    else:
        df_nutri = pd.DataFrame(st.session_state.nutrition_entries)
        df_nutri['date_str'] = df_nutri['date'].str[:10]
        
        # 依日期由新到舊排序
        grouped_nutri = df_nutri.groupby('date_str', sort=False)
        dates_sorted = sorted(grouped_nutri.groups.keys(), reverse=True)
        
        for date in dates_sorted:
            group = grouped_nutri.get_group(date)
            total_c = group['calories'].sum()
            with st.expander(f"📅 {date} | 總熱量: {total_c:.0f} kcal", expanded=True):
                st.caption(f"碳水: {group['carbs'].sum():.0f}g | 蛋白: {group['protein'].sum():.0f}g | 脂肪: {group['fat'].sum():.0f}g")
                for _, row in group.iterrows():
                    food_desc = f" - {row['foodName']}" if row.get('foodName') else ""
                    st.write(f"**{row['type']}**{food_desc} : {row['calories']:.0f} kcal")
                    st.caption(f"碳{row['carbs']:.0f} 蛋{row['protein']:.0f} 脂{row['fat']:.0f}")

# ==========================================
# 8. 重訓課表記錄 (對應 HistoryView)
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
                        if row["dayType"] == "Cardio":
                            notes = f" ({row['notes']})" if row.get('notes') else ""
                            reps_str = f" | {int(row['reps'])} 次" if row['reps'] > 0 else ""
                            st.write(f"- {row['duration']:.0f} 分鐘{notes}{reps_str}")
                        else:
                            st.write(f"- {row['weight']:.1f} kg | {int(row['sets'])} 組 x {int(row['reps'])} 下")