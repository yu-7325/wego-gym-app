import streamlit as st
from collections import defaultdict
import services

def trigger_save():
    services.save_data(
        st.session_state.nutrition_entries, st.session_state.workout_entries,
        st.session_state.body_entries, st.session_state.custom_exercises
    )

def render():
    hist_type = st.radio("選擇檢視歷史：", ["飲食紀錄", "重訓紀錄"], horizontal=True)
    
    if hist_type == "飲食紀錄":
        if not st.session_state.nutrition_entries: st.write("尚未有任何飲食紀錄")
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
                                st.session_state.unsynced = True
                                st.rerun()
    else:
        if not st.session_state.workout_entries: st.write("尚未有任何訓練紀錄")
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
                                rpe_str = f" | RPE: {row.get('rpe', 8.0)}" if row.get('weight', 0) > 0 else ""
                                if row.get("duration") is not None: st.write(f"- ⏱️ {row['duration']:.0f} 分鐘" + (f" ({row['notes']})" if row.get('notes') else ""))
                                else: st.write(f"- 🏋️ {row.get('weight',0.0):.1f} kg | {int(row.get('sets',0))} 組 x {int(row.get('reps',0))} 下{rpe_str}")
                            with col_y:
                                if st.button("❌", key=f"del_h_w_{row['id']}"):
                                    st.session_state.workout_entries = [e for e in st.session_state.workout_entries if e["id"] != row["id"]]
                                    st.session_state.unsynced = True
                                    st.rerun()
