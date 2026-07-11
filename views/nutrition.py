import streamlit as st
import uuid
from datetime import datetime
from config import MEAL_TYPES
import services

def trigger_save():
    services.save_data(
        st.session_state.nutrition_entries, st.session_state.workout_entries,
        st.session_state.body_entries, st.session_state.custom_exercises
    )

def render():
    st.header("新增攝取")
    selected_date_n = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="nutri_date")
    
    st.subheader("⚡ 快速加入")
    col_q1, col_q2 = st.columns([1, 2])
    with col_q1: quick_meal = st.selectbox("快速加入時段", MEAL_TYPES, index=3, label_visibility="collapsed")
    with col_q2:
        if st.button("➕ 加入乳清蛋白 (120 kcal)"):
            entry_date = datetime.combine(selected_date_n, datetime.now().time()).isoformat()
            st.session_state.nutrition_entries.append({
                "id": str(uuid.uuid4()), "date": entry_date, "type": quick_meal, "foodName": "乳清蛋白", "protein": 25.0, "carbs": 2.0, "fat": 1.5, "calories": 120.0
            })
            st.session_state.unsynced = True
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
                "id": str(uuid.uuid4()), "date": entry_date, "type": selected_meal, "foodName": input_food_name if input_food_name else None, "protein": input_protein, "carbs": input_carbs, "fat": input_fat, "calories": input_calories
            })
            st.session_state.unsynced = True
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
            with col_a: st.info(entry["type"])
            with col_b:
                if entry.get("foodName"): st.write(f"**{entry['foodName']}**")
                st.caption(f"碳水: {entry['carbs']:.1f}g | 蛋白質: {entry['protein']:.1f}g | 脂肪: {entry['fat']:.1f}g")
            with col_c:
                st.write(f"**{entry['calories']:.0f} kcal**")
                if st.button("❌", key=f"del_nutri_{entry['id']}"):
                    st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != entry["id"]]
                    st.session_state.unsynced = True
                    st.rerun()
