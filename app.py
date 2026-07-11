# app.py

import streamlit as st

# ==========================================
# 1. 網頁初始設定 (必須在最上方，防止 APIException)
# ==========================================
st.set_page_config(page_title="We Go GYM", page_icon="🏋️", layout="centered")

import pandas as pd
import json
import os
from datetime import datetime
import uuid
import altair as alt
from collections import defaultdict

# 匯入自訂解耦模組
from config import MEAL_TYPES, ROUTINE_PLANS, MUSCLE_GROUPS, WORKOUT_MUSCLE_MAPPING
import services

# 狀態安全初始化
if "nutrition_entries" not in st.session_state: st.session_state.nutrition_entries = []
if "workout_entries" not in st.session_state: st.session_state.workout_entries = []
if "body_entries" not in st.session_state: st.session_state.body_entries = []
if "custom_exercises" not in st.session_state: st.session_state.custom_exercises = {}
if "active_routine" not in st.session_state: st.session_state.active_routine = "4日力量與有氧 (目前)"

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
        st.session_state.nutrition_entries,
        st.session_state.workout_entries,
        st.session_state.body_entries,
        st.session_state.custom_exercises
    )

if "show_pr_balloons" in st.session_state and st.session_state.show_pr_balloons:
    st.balloons()
    st.success(st.session_state.new_pr_msg)
    st.session_state.show_pr_balloons = False

st.title("We Go GYM ☁️")

tab_nutri, tab_work, tab_body, tab_recover, tab_hist, tab_analytics = st.tabs([
    "🍃 飲食", "🏋️ 課表", "⚖️ 體重", "💪 恢復", "🕒 歷史", "📈 數據"
])

# ==========================================
# 標籤頁：🍃 飲食
# ==========================================
with tab_nutri:
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
            with st.spinner("同步至雲端中..."): trigger_save()
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
                "id": str(uuid.uuid4()), "date": entry_date, "type": selected_meal, "foodName": input_food_name if input_food_name else None, "protein": input_protein, "carbs": input_carbs, "fat": input_fat, "calories": input_calories
            })
            with st.spinner("同步至雲端中..."): trigger_save()
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
            with col_a: st.info(entry["type"])
            with col_b:
                if entry.get("foodName"): st.write(f"**{entry['foodName']}**")
                st.caption(f"碳水: {entry['carbs']:.1f}g | 蛋白質: {entry['protein']:.1f}g | 脂肪: {entry['fat']:.1f}g")
            with col_c:
                st.write(f"**{entry['calories']:.0f} kcal**")
                if st.button("❌", key=f"del_nutri_{entry['id']}"):
                    st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != entry["id"]]
                    with st.spinner("同步至雲端中..."): trigger_save()
                    st.rerun()

# ==========================================
# 標籤頁：🏋️ 課表
# ==========================================
with tab_work:
    st.header("新增訓練動作")
    selected_date_w = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="work_date")
    
    st.session_state.active_routine = st.selectbox("當前執行課表", list(ROUTINE_PLANS.keys()), index=list(ROUTINE_PLANS.keys()).index(st.session_state.active_routine))
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
            if custom_key not in st.session_state.custom_exercises: st.session_state.custom_exercises[custom_key] = []
            if new_ex not in st.session_state.custom_exercises[custom_key] and new_ex not in base_exercises:
                st.session_state.custom_exercises[custom_key].append(new_ex)
                with st.spinner("同步至雲端中..."): trigger_save()
                st.rerun()

    last_w, last_s, last_r = services.get_last_workout_data(st.session_state.workout_entries, selected_ex)

    with st.form("workout_form", clear_on_submit=False):
        if selected_day == "Cardio" or selected_ex in ["跑步機", "戶外跑", "飛輪", "滑步機", "登階機", "跳繩"]:
            col1, col2 = st.columns(2)
            with col1: input_dist = st.number_input("距離 (km)", min_value=0.0, step=0.5, value=42.195)
            with col2: input_dur = st.number_input("時長 (分鐘)", min_value=0.0, step=1.0, value=170.0)
            if input_dist > 0 and input_dur > 0:
                pace = input_dur / input_dist
                st.info(f"🏃 目標均速約為 {int(pace)}'{int((pace - int(pace)) * 60):02d}\"/km")
            input_notes = st.text_input("備註 (例如：心率區間或次數)")
            
            if st.form_submit_button("加入課表") and input_dur > 0 and selected_ex != "➕ 新增動作...":
                entry_date = datetime.combine(selected_date_w, datetime.now().time()).isoformat()
                st.session_state.workout_entries.append({
                    "id": str(uuid.uuid4()), "date": entry_date, "dayType": selected_day, "exercise": selected_ex, "distance": input_dist, "duration": input_dur, "notes": input_notes, "weight": 0.0, "sets": 0, "reps": 0
                })
                with st.spinner("同步至雲端中..."): trigger_save()
                st.success("已加入有氧紀錄！")
                st.rerun()
        else:
            if last_s > 0: st.caption(f"💡 上次紀錄：{last_w}kg | {last_s}組 x {last_r}下")
            col1, col2, col3 = st.columns(3)
            with col1: input_weight = st.number_input("重量 (kg)", min_value=0.0, step=2.5, value=float(last_w))
            with col2: input_sets = st.number_input("組數", min_value=0, step=1, value=int(last_s) if last_s > 0 else 4)
            with col3: input_reps = st.number_input("次數 (下)", min_value=0, step=1, value=int(last_r) if last_r > 0 else 8)
                
            if st.form_submit_button("加入課表") and input_sets > 0 and input_reps > 0 and selected_ex != "➕ 新增動作...":
                entry_date = datetime.combine(selected_date_w, datetime.now().time()).isoformat()
                
                highest_prev_1rm = 0.0
                valid_history = [w for w in st.session_state.workout_entries if w.get('exercise') == selected_ex and w.get('weight', 0) > 0]
                if valid_history:
                    highest_prev_1rm = max([services.estimate_1rm(w.get('weight', 0), w.get('reps', 0)) for w in valid_history])
                
                current_estimated_1rm = services.estimate_1rm(input_weight, input_reps)
                
                if highest_prev_1rm > 0.0 and current_estimated_1rm > highest_prev_1rm:
                    st.session_state.show_pr_balloons = True
                    st.session_state.new_pr_msg = f"🏋️‍♂️ 突破天際！{selected_ex} 創下全新個人 PR！估算 1RM 達到 {current_estimated_1rm:.1f} kg (進步 {current_estimated_1rm - highest_prev_1rm:.1f} kg)！"

                st.session_state.workout_entries.append({
                    "id": str(uuid.uuid4()), "date": entry_date, "dayType": selected_day, "exercise": selected_ex, "weight": input_weight, "sets": input_sets, "reps": input_reps, "duration": None, "distance": None, "notes": None
                })
                with st.spinner("同步至雲端中..."): trigger_save()
                st.rerun()

    st.divider()
    target_date_w_str = selected_date_w.strftime("%Y-%m-%d")
    today_work = [e for e in st.session_state.workout_entries if e["date"].startswith(target_date_w_str)]
    st.subheader(f"課表清單 ({target_date_w_str})")
    
    if not today_work:
        st.write("尚未新增動作")
    else:
        grouped_work = defaultdict(list)
        for w in today_work: grouped_work[w.get('dayType', 'Other')].append(w)
        
        for day, group in grouped_work.items():
            st.markdown(f"#### {day}")
            grouped_ex = defaultdict(list)
            for w in group: grouped_ex[w.get('exercise', 'Unknown')].append(w)
            
            for ex, ex_group in grouped_ex.items():
                st.markdown(f"**{ex}**")
                for row in ex_group:
                    col_x, col_y, col_z = st.columns([3, 2, 1])
                    with col_x:
                        if row.get("duration") is not None: st.write(f"⏱️ {row['duration']:.0f} 分鐘" + (f" ({row['notes']})" if row.get('notes') else ""))
                        else: st.write(f"🏋️ {row.get('weight', 0.0):.1f} kg")
                    with col_y:
                        if row.get("duration") is not None: st.write(f"{row['distance']:.1f} km" if row.get('distance', 0) > 0 else "")
                        else: st.write(f"**{int(row.get('sets', 0))} 組 x {int(row.get('reps', 0))} 下**")
                    with col_z:
                        if st.button("❌", key=f"del_work_{row['id']}"):
                            st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                            with st.spinner("同步至雲端中..."): trigger_save()
                            st.rerun()

# ==========================================
# 標籤頁：⚖️ 體重
# ==========================================
with tab_body:
    st.header("記錄身體數據")
    selected_date_b = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="body_date")
    
    last_w_body, last_bf = 70.0, 15.0
    if st.session_state.body_entries:
        sorted_body = sorted(st.session_state.body_entries, key=lambda x: x["date"], reverse=True)
        if sorted_body:
            last_w_body = sorted_body[0].get("weight", 70.0)
            last_bf = sorted_body[0].get("body_fat", 15.0)

    with st.form("body_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: input_bw = st.number_input("體重 (kg)", min_value=30.0, max_value=200.0, step=0.1, value=float(last_w_body))
        with col2: input_bf = st.number_input("體脂率 (%) [選填]", min_value=0.0, max_value=60.0, step=0.1, value=float(last_bf))
            
        if st.form_submit_button("儲存數據"):
            entry_date = datetime.combine(selected_date_b, datetime.now().time()).isoformat()
            target_date_str = selected_date_b.strftime("%Y-%m-%d")
            st.session_state.body_entries = [e for e in st.session_state.body_entries if not e["date"].startswith(target_date_str)]
            
            st.session_state.body_entries.append({"id": str(uuid.uuid4()), "date": entry_date, "weight": input_bw, "body_fat": input_bf})
            with st.spinner("同步至雲端中..."): trigger_save()
            st.success("身體數據已更新！")
            st.rerun()
            
    st.divider()
    st.subheader("近期體態變化")
    if st.session_state.body_entries:
        sorted_body = sorted(st.session_state.body_entries, key=lambda x: x["date"], reverse=True)[:5]
        for row in sorted_body:
            date_str = row['date'][:10]
            bf_str = f" | {row['body_fat']}%" if row.get('body_fat') else ""
            st.markdown(f"- **{date_str}**: {row['weight']} kg{bf_str}")
    else:
        st.write("尚未有身體紀錄。")

# ==========================================
# 標籤頁：💪 恢復
# ==========================================
with tab_recover:
    st.header("人體恢復狀態儀表板")
    color_map = {"red": "🔴", "orange": "🟠", "green": "🟢"}
    statuses = services.calculate_muscle_statuses(st.session_state.workout_entries)
    for status in statuses:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"### {color_map[status['color']]} {status['muscle']}")
            if status['latest_date']: st.caption(f"上次訓練: {status['latest_date'].strftime('%Y-%m-%d %H:%M')}")
            else: st.caption("無訓練紀錄")
        with col2:
            if status['remaining'] <= 0: st.write("**已恢復**")
            else: st.write(f"**剩餘: {int(status['remaining'])}時{int((status['remaining'] - int(status['remaining'])) * 60)}分**")
        st.progress(status['progress'])
        st.write("---")

# ==========================================
# 標籤頁：🕒 歷史
# ==========================================
with tab_hist:
    hist_type = st.radio("選擇檢視歷史：", ["飲食紀錄", "重訓紀錄"], horizontal=True)
    
    if hist_type == "飲食紀錄":
        if not st.session_state.nutrition_entries: st.write("Transient history is empty.")
        else:
            grouped_n_hist = defaultdict(list)
            for e in st.session_state.nutrition_entries: grouped_n_hist[e['date'][:10]].append(e)
            
            for date in sorted(grouped_n_hist.keys(), reverse=True):
                group = grouped_n_hist[date]
                total_c = sum(e.get('calories', 0) for e in group)
                with st.expander(f"📅 {date} | 總熱量: {total_c:.0f} kcal"):
                    st.markdown(f"**🔥 日總計 ➔ 碳水: {sum(e.get('carbs',0) for e in group):.1f}g | 蛋白質: {sum(e.get('protein',0) for e in group):.1f}g | 脂肪: {sum(e.get('fat',0) for e in group):.1f}g**")
                    st.divider()
                    for row in group:
                        col_x, col_y = st.columns([4, 1])
                        with col_x:
                            st.write(f"**{row['type']}**" + (f" - {row['foodName']}" if row.get('foodName') else "") + f" : {row.get('calories', 0):.0f} kcal")
                            st.caption(f"碳水: {row.get('carbs',0):.1f}g | 蛋白質: {row.get('protein',0):.1f}g | 脂肪: {row.get('fat',0):.1f}g")
                        with col_y:
                            if st.button("❌", key=f"del_h_n_{row['id']}"):
                                st.session_state.nutrition_entries = [e for e in st.session_state.nutrition_entries if e["id"] != row["id"]]
                                with st.spinner("同步至雲端中..."): trigger_save()
                                st.rerun()
    else:
        if not st.session_state.workout_entries: st.write("Transient history is empty.")
        else:
            grouped_w_hist = defaultdict(list)
            for e in st.session_state.workout_entries: grouped_w_hist[e['date'][:10]].append(e)
            
            for date in sorted(grouped_w_hist.keys(), reverse=True):
                group = grouped_w_hist[date]
                day_types = list(set(e.get('dayType', 'Workout') for e in group))
                with st.expander(f"📅 {date} | {', '.join(day_types)}"):
                    
                    grouped_ex = defaultdict(list)
                    for w in group: grouped_ex[w.get('exercise', 'Unknown')].append(w)
                    
                    for ex, ex_group in grouped_ex.items():
                        st.write(f"**{ex}**")
                        for row in ex_group:
                            col_x, col_y = st.columns([4, 1])
                            with col_x:
                                if row.get("duration") is not None: st.write(f"- ⏱️ {row['duration']:.0f} 分鐘" + (f" ({row['notes']})" if row.get('notes') else ""))
                                else: st.write(f"- 🏋️ {row.get('weight',0.0):.1f} kg | {int(row.get('sets',0))} 組 x {int(row.get('reps',0))} 下")
                            with col_y:
                                if st.button("❌", key=f"del_h_w_{row['id']}"):
                                    st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                                    with st.spinner("同步至雲端中..."): trigger_save()
                                    st.rerun()

# ==========================================
# 9. 數據分析
# ==========================================
with tab_analytics:
    analysis_option = st.selectbox(
        "📊 請選擇分析圖表", 
        ["⚖️ 體態與熱量分析", "📊 肌肉部位容量佔比", "🏆 1RM PR 榮譽榜與力量趨勢", "🏋️ 訓練總容量趨勢"]
    )
    st.divider()

    if analysis_option == "⚖️ 體態與熱量分析":
        st.header("⚖️ 體態與熱量分析")
        if st.session_state.nutrition_entries and st.session_state.body_entries:
            df_n = pd.DataFrame(st.session_state.nutrition_entries)
            df_n['date_str'] = df_n['date'].str[:10]
            daily_cal = df_n.groupby('date_str')['calories'].sum().reset_index()
            
            df_b = pd.DataFrame(st.session_state.body_entries)
            df_b['date_str'] = df_b['date'].str[:10]
            
            merged_df = pd.merge(daily_cal, df_b[['date_str', 'weight']], on='date_str', how='outer')
            merged_df = merged_df.sort_values('date_str')
            merged_df['weight'] = merged_df['weight'].bfill().ffill().fillna(0)
            merged_df['calories'] = merged_df['calories'].fillna(0)
            
            chart_df = pd.DataFrame({
                "date_str": merged_df["date_str"].astype(str),
                "calories": merged_df["calories"].astype(float),
                "weight": merged_df["weight"].astype(float)
            })
            
            st.markdown("#### 攝取熱量 (kcal)")
            cal_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('calories:Q', title='熱量 (kcal)'),
                tooltip=[alt.Tooltip('date_str:O', title='日期'), alt.Tooltip('calories:Q', title='熱量 (kcal)')]
            )
            st.altair_chart(cal_chart, use_container_width=True)
            
            st.markdown("#### 體重變化 (kg)")
            weight_chart = alt.Chart(chart_df).mark_line(color='#FF4B4B', point=True, strokeWidth=3).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('weight:Q', title='體重 (kg)', scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip('date_str:O', title='日期'), alt.Tooltip('weight:Q', title='體重 (kg)')]
            )
            st.altair_chart(weight_chart, use_container_width=True)
        else:
            st.info("💡 需要同時擁有「飲食紀錄」與「體重紀錄」才能解鎖分析圖表！")

    elif analysis_option == "📊 肌肉部位容量佔比":
        st.header("📊 肌肉部位容量佔比")
        if st.session_state.workout_entries:
            muscle_data = {m: 0.0 for m in MUSCLE_GROUPS.keys()}
            has_valid_data = False
            
            for w in st.session_state.workout_entries:
                if w.get("weight", 0) > 0 and w.get("sets", 0) > 0 and w.get("reps", 0) > 0:
                    vol = w["weight"] * w["sets"] * w["reps"]
                    day_type = w.get("dayType", "Other")
                    for muscle in WORKOUT_MUSCLE_MAPPING.get(day_type, []):
                        if muscle in muscle_data:
                            muscle_data[muscle] += vol
                            has_valid_data = True
            
            if has_valid_data:
                df_muscle = pd.DataFrame(list(muscle_data.items()), columns=['部位', '累積總容量 (kg)'])
                chart_df = pd.DataFrame({
                    "部位": df_muscle["部位"].astype(str),
                    "累積總容量": df_muscle["累積總容量 (kg)"].astype(float)
                })
                
                muscle_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('部位:O', title='肌肉部位', sort='-y'),
                    y=alt.Y('累積總容量:Q', title='累積總容量 (kg)'),
                    tooltip=[alt.Tooltip('部位:O', title='部位'), alt.Tooltip('累積總容量:Q', title='總容量 (kg)', format='.1f')]
                )
                st.altair_chart(muscle_chart, use_container_width=True)
            else:
                st.write("目前尚無重量訓練數據可供分析。")
        else:
            st.write("目前尚無任何訓練數據。")

    elif analysis_option == "🏆 1RM PR 榮譽榜與力量趨勢":
        st.header("🏆 個人最高紀錄 (1RM PR 榮譽榜)")
        if st.session_state.workout_entries:
            df_all = pd.DataFrame(st.session_state.workout_entries)
            
            for col in ['weight', 'sets', 'reps', 'exercise', 'date']:
                if col not in df_all.columns:
                    df_all[col] = 0.0 if col in ['weight', 'sets', 'reps'] else ""
            
            df_weight_only = df_all[df_all['weight'] > 0].copy()
            
            if not df_weight_only.empty:
                df_weight_only['estimated_1rm'] = df_weight_only.apply(lambda row: services.estimate_1rm(row['weight'], row['reps']), axis=1)
                
                pr_summary = df_weight_only.groupby('exercise').agg(
                    最高極限重量=('weight', 'max'),
                    估算最大肌力_1RM=('estimated_1rm', 'max')
                ).reset_index()
                
                pr_display = pr_summary.copy()
                pr_display.rename(columns={'exercise': '訓練動作'}, inplace=True)
                pr_display['最高極限重量'] = pr_display['最高極限重量'].apply(lambda x: f"{x:.1f} kg")
                pr_display['估算最大肌力_1RM'] = pr_display['估算最大肌力_1RM'].apply(lambda x: f"{x:.1f} kg")
                st.table(pr_display.set_index('訓練動作'))
                
                st.write("---")
                st.subheader("📈 單一動作力量走勢與均線追蹤")
                
                unique_exercises = sorted(df_weight_only['exercise'].unique())
                selected_track_ex = st.selectbox("選擇要追蹤的力量動作：", unique_exercises)
                
                df_track = df_weight_only[df_weight_only['exercise'] == selected_track_ex].copy()
                df_track['date_str'] = df_track['date'].str[:10]
                df_daily_1rm = df_track.groupby('date_str')['estimated_1rm'].max().reset_index().sort_values('date_str')
                
                if not df_daily_1rm.empty:
                    df_daily_1rm['3站移動平均線'] = df_daily_1rm['estimated_1rm'].rolling(window=3, min_periods=1).mean()
                    df_daily_1rm.rename(columns={'estimated_1rm': '當日估算 1RM'}, inplace=True)
                    df_melted = df_daily_1rm.melt(id_vars=['date_str'], value_vars=['當日估算 1RM', '3站移動平均線'], var_name='指標類型', value_name='重量 (kg)')
                    
                    chart_df = pd.DataFrame({
                        "date_str": df_melted["date_str"].astype(str),
                        "指標類型": df_melted["指標類型"].astype(str),
                        "重量": df_melted["重量 (kg)"].astype(float)
                    })
                    
                    track_chart = alt.Chart(chart_df).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('date_str:O', title='日期'),
                        y=alt.Y('重量:Q', title='估算最大力量 (kg)', scale=alt.Scale(zero=False)),
                        color=alt.Color('指標類型:N', scale=alt.Scale(domain=['當日估算 1RM', '3站移動平均線'], range=['#5C9DF5', '#FFA500'])),
                        tooltip=[alt.Tooltip('date_str:O', title='日期'), alt.Tooltip('指標類型:N', title='類型'), alt.Tooltip('重量:Q', title='重量 (kg)', format='.1f')]
                    )
                    st.altair_chart(track_chart, use_container_width=True)
            else:
                st.write("目前尚無重量訓練數據，快去建立第一筆 PR 吧！")
        else:
            st.write("目前尚無任何訓練數據。")

    elif analysis_option == "🏋️ 訓練總容量趨勢":
        st.header("🏋️ 訓練總容量趨勢 (Total Volume)")
        if st.session_state.workout_entries:
            df_w = pd.DataFrame(st.session_state.workout_entries)
            
            for col in ['weight', 'sets', 'reps', 'date']:
                if col not in df_w.columns:
                    df_w[col] = 0.0 if col in ['weight', 'sets', 'reps'] else ""
                    
            if 'weight' in df_w.columns and not df_w[df_w['weight'] > 0].empty:
                df_weights = df_w[df_w['weight'] > 0].copy()
                time_interval = st.radio("選擇檢視區間：", ["日 (Daily)", "週 (Weekly)", "月 (Monthly)"], horizontal=True)
                df_weights['date_obj'] = pd.to_datetime(df_weights['date'].str[:10])
                df_weights['volume'] = df_weights['weight'] * df_weights['sets'] * df_weights['reps']
                
                if time_interval == "日 (Daily)":
                    df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m-%d')
                    x_title = "日期"
                elif time_interval == "週 (Weekly)":
                    df_weights['period'] = (df_weights['date_obj'] - pd.to_timedelta(df_weights['date_obj'].dt.dayofweek, unit='d')).dt.strftime('%Y-%m-%d (週一)')
                    x_title = "週度"
                else:
                    df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m')
                    x_title = "月份"
                
                vol_trend = df_weights.groupby('period')['volume'].sum().reset_index()
                
                chart_df = pd.DataFrame({
                    "period": vol_trend["period"].astype(str),
                    "volume": vol_trend["volume"].astype(float)
                })
                
                vol_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('period:O', title=x_title, sort=None),
                    y=alt.Y('volume:Q', title='總容量 (kg)'),
                    tooltip=[alt.Tooltip('period:O', title=x_title), alt.Tooltip('volume:Q', title='總容量 (kg)', format='.1f')]
                )
                st.altair_chart(vol_chart, use_container_width=True)
            else:
                st.write("目前尚無重量訓練數據可供分析。")
