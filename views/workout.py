# views/workout.py

import streamlit as st
import uuid
from datetime import datetime
from collections import defaultdict
from config import ROUTINE_PLANS
import services

def trigger_save():
    services.save_data(
        st.session_state.nutrition_entries, st.session_state.workout_entries,
        st.session_state.body_entries, st.session_state.custom_exercises
    )

# ─── 🔥 終極加速：將高頻互動區塊封裝為 Fragment，拉動滑桿不再重跑全局 ───
@st.fragment
def interactive_workout_panel(selected_ex, selected_day, selected_date_w, last_w, last_s, last_r):
    recommended_weight_val = float(last_w)
    is_strength_workout = selected_day != "Cardio" and selected_ex not in ["跑步機", "戶外跑", "飛輪", "滑步機", "登階機", "跳繩"] and selected_ex != "➕ 新增動作..."
    
    if is_strength_workout:
        max_1rm = 0.0
        valid_history = [w for w in st.session_state.workout_entries if w.get('exercise') == selected_ex and w.get('weight', 0) > 0]
        if valid_history:
            max_1rm = max([services.estimate_1rm(w.get('weight', 0), w.get('reps', 0)) for w in valid_history])
        
        if max_1rm > 0:
            with st.expander("🧮 展開 %1RM 智慧配重試算機", expanded=False):
                col_pct, col_calc = st.columns([2, 1])
                with col_pct:
                    # 在這裡拉動滑桿，只有這個 Panel 會重繪，系統極度流暢！
                    target_pct = st.slider("今日目標強度 (% 1RM)", min_value=40, max_value=100, value=80, step=5)
                with col_calc:
                    recommended_weight_val = round((max_1rm * (target_pct / 100)) / 2.5) * 2.5
                    st.metric(label="建議重量", value=f"{recommended_weight_val:.1f} kg")

    with st.form("workout_form", clear_on_submit=False):
        if selected_day == "Cardio" or selected_ex in ["跑步機", "戶外跑", "飛輪", "滑步機", "登階機", "跳繩"]:
            col1, col2 = st.columns(2)
            with col1: input_dist = st.number_input("距離 (km)", min_value=0.0, step=0.5, value=5.0)
            with col2: input_dur = st.number_input("時長 (分鐘)", min_value=0.0, step=1.0, value=30.0)
            if input_dist > 0 and input_dur > 0:
                pace = input_dur / input_dist
                st.caption(f"🏃 預估均速: {int(pace)}'{int((pace - int(pace)) * 60):02d}\"/km")
            input_notes = st.text_input("備註 (例如: 心率或體感)")
            
            if st.form_submit_button("紀錄有氧課表", type="primary", use_container_width=True) and input_dur > 0 and selected_ex != "➕ 新增動作...":
                entry_date = datetime.combine(selected_date_w, datetime.now().time()).isoformat()
                st.session_state.workout_entries.append({
                    "id": str(uuid.uuid4()), "date": entry_date, "dayType": selected_day, "exercise": selected_ex, "distance": input_dist, "duration": input_dur, "notes": input_notes, "weight": 0.0, "sets": 0, "reps": 0, "rpe": 0.0, "pump": 3.0, "joint_pain": 1.0
                })
                st.session_state.unsynced = True
                st.rerun() # 送出表單後，主動觸發全局更新以同步歷史清單
        else:
            if last_s > 0: st.caption(f"💡 上次歷史數據：{last_w}kg | {last_s}組 x {last_r}下")
            col1, col2, col3 = st.columns(3)
            with col1: input_weight = st.number_input("重量 (kg)", min_value=0.0, step=2.5, value=float(recommended_weight_val))
            with col2: input_sets = st.number_input("組數", min_value=0, step=1, value=int(last_s) if last_s > 0 else 4)
            with col3: input_reps = st.number_input("次數 (下)", min_value=0, step=1, value=int(last_r) if last_r > 0 else 8)
            
            input_rpe = st.select_slider("🎯 強度自評 (RPE)", options=[6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0], value=8.0)
            
            with st.expander("📝 動作適應性評分 (SFR 選填)", expanded=False):
                col_p1, col_p2 = st.columns(2)
                with col_p1: input_pump = st.slider("肌肉充血泵感", min_value=1.0, max_value=5.0, value=3.0, step=1.0)
                with col_p2: input_pain = st.slider("關節不適/疼痛感", min_value=1.0, max_value=5.0, value=1.0, step=1.0)
                
            if st.form_submit_button("送出紀錄本組數據", type="primary", use_container_width=True) and input_sets > 0 and input_reps > 0 and selected_ex != "➕ 新增動作...":
                entry_date = datetime.combine(selected_date_w, datetime.now().time()).isoformat()
                
                highest_prev_1rm = 0.0
                valid_history = [w for w in st.session_state.workout_entries if w.get('exercise') == selected_ex and w.get('weight', 0) > 0]
                if valid_history:
                    highest_prev_1rm = max([services.estimate_1rm(w.get('weight', 0), w.get('reps', 0)) for w in valid_history])
                
                current_estimated_1rm = services.estimate_1rm(input_weight, input_reps)
                if highest_prev_1rm > 0.0 and current_estimated_1rm > highest_prev_1rm:
                    st.session_state.show_pr_balloons = True
                    st.session_state.new_pr_msg = f"🏋️‍♂️ 突破天際！{selected_ex} 創下個人新 PR！預估 1RM 達 {current_estimated_1rm:.1f} kg！"

                st.session_state.workout_entries.append({
                    "id": str(uuid.uuid4()), "date": entry_date, "dayType": selected_day, "exercise": selected_ex, "weight": input_weight, "sets": input_sets, "reps": input_reps, "duration": None, "distance": None, "notes": None, "rpe": input_rpe, "pump": input_pump, "joint_pain": input_pain
                })
                st.session_state.unsynced = True
                st.rerun()

# 主渲染函數
def render():
    st.header("🏋️ 訓練課表紀錄")
    selected_date_w = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="work_date")
    
    routine_options = list(ROUTINE_PLANS.keys())
    default_index = routine_options.index(st.session_state.active_routine) if st.session_state.active_routine in routine_options else 0
    
    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        selected_routine = st.selectbox("選擇課表", routine_options, index=default_index, key="routine_selector")
        st.session_state.active_routine = selected_routine
        current_plan = ROUTINE_PLANS[selected_routine]
    with sel_col2:
        selected_day = st.selectbox("訓練日分化", current_plan["days"])
    
    base_exercises = current_plan["exercises"].get(selected_day, [])
    custom_key = f"{st.session_state.active_routine}_{selected_day}"
    custom_exercises = st.session_state.custom_exercises.get(custom_key, [])
    exercise_options = base_exercises + custom_exercises + ["➕ 新增動作..."]
    selected_ex = st.selectbox("選擇訓練動作", exercise_options)
    
    if selected_ex == "➕ 新增動作...":
        new_ex = st.text_input("輸入新動作名稱")
        if st.button("確認新增動作", use_container_width=True) and new_ex:
            if custom_key not in st.session_state.custom_exercises: st.session_state.custom_exercises[custom_key] = []
            if new_ex not in st.session_state.custom_exercises[custom_key] and new_ex not in base_exercises:
                st.session_state.custom_exercises[custom_key].append(new_ex)
                st.session_state.unsynced = True
                st.rerun()

    if selected_ex != "➕ 新增動作...":
        target_msg, fatigue_msg, rotation_msg = services.get_auto_regulation_signals(st.session_state.workout_entries, selected_ex)
        if fatigue_msg: st.error(fatigue_msg, icon="🚨")
        if rotation_msg: st.warning(rotation_msg, icon="🔄")
        if target_msg and not fatigue_msg and not rotation_msg: st.info(target_msg, icon="📈")

    last_w, last_s, last_r = services.get_last_workout_data(st.session_state.workout_entries, selected_ex)

    # 呼叫 Fragment 區域 (此區塊具備獨立運算的防卡頓護盾)
    if selected_ex != "➕ 新增動作...":
        interactive_workout_panel(selected_ex, selected_day, selected_date_w, last_w, last_s, last_r)

    st.divider()
    target_date_w_str = selected_date_w.strftime("%Y-%m-%d")
    today_work = [e for e in st.session_state.workout_entries if e["date"].startswith(target_date_w_str)]
    st.subheader(f"📋 今日已存課表清單")
    
    if not today_work:
        st.caption("今日尚未有動作紀錄。")
    else:
        grouped_work = defaultdict(list)
        for w in today_work: grouped_work[w.get('dayType', 'Other')].append(w)
        for day, group in grouped_work.items():
            st.markdown(f"##### 🧱 {day}")
            grouped_ex = defaultdict(list)
            for w in group: grouped_ex[w.get('exercise', 'Unknown')].append(w)
            for ex, ex_group in grouped_ex.items():
                with st.container():
                    col_x, col_y, col_z = st.columns([3, 2, 0.8])
                    with col_x:
                        st.markdown(f"**{ex}**")
                        row = ex_group[0]
                        if row.get("duration") is not None: st.caption(f"⏱️ {row['duration']:.0f} 分鐘" + (f" ({row['notes']})" if row.get('notes') else ""))
                        else: st.caption(f"🏋️ {row.get('weight', 0.0):.1f} kg · `RPE: {row.get('rpe', 8.0)}`")
                    with col_y:
                        st.write("") 
                        if row.get("duration") is not None: st.write(f"{row['distance']:.1f} km" if row.get('distance', 0) > 0 else "")
                        else: st.markdown(f"`{int(row.get('sets', 0))}組` x `{int(row.get('reps', 0))}下`")
                    with col_z:
                        if st.button("❌", key=f"del_work_{row['id']}", use_container_width=True):
                            st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                            st.session_state.unsynced = True
                            st.rerun()
