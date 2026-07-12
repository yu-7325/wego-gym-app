# views/body.py

import streamlit as st
import uuid
from datetime import datetime

def render():
    st.header("⚖️ 記錄身體數據")
    selected_date_b = st.date_input("📝 選擇紀錄日期", datetime.now().date(), key="body_date")
    
    last_w_body, last_bf = 70.0, 15.0
    if st.session_state.body_entries:
        sorted_body = sorted(st.session_state.body_entries, key=lambda x: x["date"], reverse=True)
        if sorted_body:
            last_w_body = sorted_body[0].get("weight", 70.0)
            last_bf = sorted_body[0].get("body_fat", 15.0)

    with st.form("body_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1: input_bw = st.number_input("體重 (kg)", min_value=30.0, max_value=200.0, step=0.1, value=float(last_w_body))
        with col2: input_bf = st.number_input("體脂率 (%) [選填]", min_value=0.0, max_value=60.0, step=0.1, value=float(last_bf))
            
        if st.form_submit_button("儲存今日數據", type="primary", use_container_width=True):
            entry_date = datetime.combine(selected_date_b, datetime.now().time()).isoformat()
            target_date_str = selected_date_b.strftime("%Y-%m-%d")
            
            # 覆蓋同一天的舊紀錄
            st.session_state.body_entries = [e for e in st.session_state.body_entries if not e["date"].startswith(target_date_str)]
            
            st.session_state.body_entries.append({"id": str(uuid.uuid4()), "date": entry_date, "weight": input_bw, "body_fat": input_bf})
            st.session_state.unsynced = True
            st.success("身體數據已更新！")
            st.rerun()
            
    st.divider()
    st.subheader("📋 近期體態紀錄清單")
    
    # 🔥 新增：支援編輯刪除的列表管理 UI
    if st.session_state.body_entries:
        sorted_body = sorted(st.session_state.body_entries, key=lambda x: x["date"], reverse=True)
        for row in sorted_body:
            with st.container():
                col_a, col_b, col_c = st.columns([1.5, 2, 1])
                date_str = row['date'][:10]
                bf_str = f" | {row['body_fat']}% 體脂" if row.get('body_fat') else ""
                
                with col_a:
                    st.markdown(f"**📅 {date_str}**")
                with col_b:
                    st.markdown(f"⚖️ `{row['weight']} kg`{bf_str}")
                with col_c:
                    if st.button("❌ 刪除", key=f"del_body_{row['id']}", use_container_width=True):
                        st.session_state.body_entries = [e for e in st.session_state.body_entries if e["id"] != row["id"]]
                        st.session_state.unsynced = True
                        st.rerun()
    else:
        st.caption("尚未有身體紀錄。")
