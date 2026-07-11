import streamlit as st
import uuid
from datetime import datetime
import services

def trigger_save():
    services.save_data(
        st.session_state.nutrition_entries, st.session_state.workout_entries,
        st.session_state.body_entries, st.session_state.custom_exercises
    )

def render():
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
            st.session_state.unsynced = True
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
