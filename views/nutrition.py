# views/nutrition.py

import streamlit as st
import uuid
from datetime import datetime
from config import MEAL_TYPES
import services

def render():
    st.header("🍃 今日飲食攝取")
    selected_date_n = st.date_input("📅 選擇紀錄日期", datetime.now().date(), key="nutri_date")
    
    # 計算今日總計數據
    target_date_str = selected_date_n.strftime("%Y-%m-%d")
    today_nutri = [e for e in st.session_state.nutrition_entries if e["date"].startswith(target_date_str)]
    
    total_cal = sum(e["calories"] for e in today_nutri)
    total_p = sum(e["protein"] for e in today_nutri)
    total_c = sum(e["carbs"] for e in today_nutri)
    total_f = sum(e["fat"] for e in today_nutri)
    
    # ─── 🔥 UI 優化一：高質感橫向數據儀表板 ───
    st.markdown("### 📊 今日攝取總計")
    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
    meta_col1.metric("總熱量", f"{total_cal:.0f} kcal")
    meta_col2.metric("蛋白質", f"{total_p:.1f} g")
    meta_col3.metric("碳水", f"{total_c:.1f} g")
    meta_col4.metric("脂肪", f"{total_f:.1f} g")
    st.divider()
    
    # ─── 收納輸入表單 ───
    st.subheader("✍️ 記錄餐點")
    col_q1, col_q2 = st.columns([1, 2])
    with col_q1: quick_meal = st.selectbox("快速時段", MEAL_TYPES, index=3, label_visibility="collapsed", key="q_meal_sel")
    with col_q2:
        if st.button("➕ 快速加入乳清蛋白 (120 kcal)", use_container_width=True):
            entry_date = datetime.combine(selected_date_n, datetime.now().time()).isoformat()
            st.session_state.nutrition_entries.append({
                "id": str(uuid.uuid4()), "date": entry_date, "type": quick_meal, "foodName": "乳清蛋白", "protein": 25.0, "carbs": 2.0, "fat": 1.5, "calories": 120.0
            })
            st.session_state.unsynced = True
            st.rerun()
            
    with st.form("nutrition_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_meal = st.selectbox("餐點時段", MEAL_TYPES)
            input_food_name = st.text_input("食物名稱 (例如：雞胸肉便當)")
            input_calories = st.number_input("熱量 (kcal)", min_value=0.0, step=10.0)
        with col2:
            input_protein = st.number_input("蛋白質 (g)", min_value=0.0, step=1.0)
            input_carbs = st.number_input("碳水化合物 (g)", min_value=0.0, step=1.0)
            input_fat = st.number_input("脂肪 (g)", min_value=0.0, step=1.0)
            
        if st.form_submit_button("手動加入餐點紀錄", type="secondary", use_container_width=True) and input_calories > 0:
            entry_date = datetime.combine(selected_date_n, datetime.now().time()).isoformat()
            st.session_state.nutrition_entries.append({
                "id": str(uuid.uuid4()), "date": entry_date, "type": selected_meal, "foodName": input_food_name if input_food_name else None, "protein": input_protein, "carbs": input_carbs, "fat": input_fat, "calories": input_calories
            })
            st.session_state.unsynced = True
            st.rerun()

    # ─── 緊湊化歷史清單 ───
    st.divider()
    st.subheader("📋 今日已存清單")
    if not today_nutri:
        st.caption("目前尚無餐點紀錄。")
    else:
        for entry in today_nutri:
            with st.container():
                col_a, col_b, col_c = st.columns([1.2, 3, 0.8])
                with col_a: st.info(entry["type"])
                with col_b:
                    name = entry['foodName'] if entry.get('foodName') else '未命名食物'
                    st.markdown(f"**{name}** · `{entry['calories']:.0f} kcal`")
                    st.caption(f"碳: {entry['carbs']:.1f}g | 蛋: {entry['protein']:.1f}g | 脂: {entry['fat']:.1f}g")
                with col_c:
                    if st.button("❌", key=f"del_nutri_{entry['id']}", use_container_width=True):
                        st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != entry["id"]]
                        st.session_state.unsynced = True
                        st.rerun()
