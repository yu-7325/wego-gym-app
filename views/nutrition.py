# views/nutrition.py

import streamlit as st
import uuid
from datetime import datetime
from collections import defaultdict

def render():
    st.header("🍃 飲食紀錄")
    selected_date_n = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="nutri_date")
    
    meal_types = ["早餐", "午餐", "晚餐", "點心", "練前餐", "練後餐"]
    
    with st.form("nutrition_form", clear_on_submit=False):
        col_t, col_f = st.columns([1, 2])
        with col_t: input_type = st.selectbox("餐別", meal_types)
        with col_f: input_name = st.text_input("食物名稱 (必填)")
        
        col_c, col_p, col_f2, col_cal = st.columns(4)
        with col_c: input_carbs = st.number_input("碳水 (g)", min_value=0.0, step=1.0)
        with col_p: input_protein = st.number_input("蛋白質 (g)", min_value=0.0, step=1.0)
        with col_f2: input_fat = st.number_input("脂肪 (g)", min_value=0.0, step=1.0)
        with col_cal: input_calories = st.number_input("熱量 (kcal)", min_value=0.0, step=10.0)
        
        if st.form_submit_button("儲存飲食紀錄", type="primary", use_container_width=True):
            if input_name:
                entry_date = datetime.combine(selected_date_n, datetime.now().time()).isoformat()
                st.session_state.nutrition_entries.append({
                    "id": str(uuid.uuid4()), 
                    "date": entry_date, 
                    "type": input_type, 
                    "foodName": input_name, 
                    "protein": input_protein, 
                    "carbs": input_carbs, 
                    "fat": input_fat, 
                    "calories": input_calories
                })
                st.session_state.unsynced = True
                st.rerun()
            else:
                st.error("請輸入食物名稱！")
                
    st.divider()
    st.subheader("📋 今日已存清單")
    
    target_date_n_str = selected_date_n.strftime("%Y-%m-%d")
    today_nutri = [e for e in st.session_state.nutrition_entries if e["date"].startswith(target_date_n_str)]
    
    # 確保按照輸入的時間先後排序
    today_nutri = sorted(today_nutri, key=lambda x: x["date"]) 
    
    if not today_nutri:
        st.caption("所選日期尚未有飲食紀錄。")
    else:
        # ─── 🔥 核心優化：按「餐別」進行分組 (Grouping) ───
        grouped_nutri = defaultdict(list)
        for n in today_nutri:
            grouped_nutri[n.get('type', '未分類')].append(n)
            
        # 為了讓顯示順序符合邏輯 (早 -> 午 -> 晚)，給定一個權重字典
        meal_order = {"早餐": 1, "午餐": 2, "晚餐": 3, "點心": 4, "練前餐": 5, "練後餐": 6}
        sorted_meals = sorted(grouped_nutri.keys(), key=lambda x: meal_order.get(x, 99))
        
        for meal in sorted_meals:
            group = grouped_nutri[meal]
            st.markdown(f"##### 🍽️ {meal}")  # 統一顯示餐別大標題
            
            for row in group:
                with st.container():
                    col_x, col_y, col_z = st.columns([3, 3, 1])
                    with col_x:
                        # 顯示食物名稱與熱量
                        st.markdown(f"**{row.get('foodName', '未命名食物')}** · `{row.get('calories', 0):.0f} kcal`")
                    with col_y:
                        # 顯示三大營養素
                        st.caption(f"碳: {row.get('carbs', 0):.1f}g | 蛋: {row.get('protein', 0):.1f}g | 脂: {row.get('fat', 0):.1f}g")
                    with col_z:
                        # 保留專屬刪除按鈕
                        if st.button("❌", key=f"del_nutri_{row['id']}", use_container_width=True):
                            st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != row["id"]]
                            st.session_state.unsynced = True
                            st.rerun()
