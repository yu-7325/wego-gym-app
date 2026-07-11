import streamlit as st
import services

def render():
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
