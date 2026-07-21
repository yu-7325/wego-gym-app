# views/gallery.py

import streamlit as st
import uuid
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO
from collections import defaultdict  # 🔥 新增：用來分組的字典工具

def process_image(uploaded_file):
    try:
        # 開啟圖片並轉換為標準 RGB
        img = Image.open(uploaded_file)
        img = img.convert("RGB")
        
        # 黑科技壓縮：將長寬限制在 400px，畫質降低至 50
        img.thumbnail((400, 400))
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=50)
        
        # 將二進位圖片轉換為 Base64 文字編碼
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        st.error(f"圖片處理失敗: {e}")
        return None

def render():
    st.header("📷 影像與備忘圖庫")
    st.caption("上傳您的課表截圖、飲食照片或體態紀錄。系統會自動壓縮成輕量化編碼並儲存至雲端。")
    
    with st.form("gallery_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("選擇圖片上傳", type=["jpg", "jpeg", "png", "webp"])
        with col2:
            img_category = st.selectbox("標籤分類", ["🏋️ 動作與課表", "🥗 飲食紀錄", "💪 體態與其他"])
            
        img_notes = st.text_input("簡單備註 (例如：深蹲站距微調、新買的高蛋白)")
        
        if st.form_submit_button("💾 上傳並儲存圖片", type="primary", use_container_width=True):
            if uploaded_file is not None:
                with st.spinner("正在壓縮並將影像轉換為安全編碼..."):
                    b64_str = process_image(uploaded_file)
                    if b64_str:
                        entry_date = datetime.now().isoformat()
                        st.session_state.gallery_entries.append({
                            "id": str(uuid.uuid4()),
                            "date": entry_date,
                            "category": img_category,
                            "image_base64": b64_str,
                            "notes": img_notes
                        })
                        st.session_state.unsynced = True
                        st.success("圖片上傳成功！")
                        st.rerun()
            else:
                st.error("請先選擇一張圖片！")
                
    st.divider()
    st.subheader("🖼️ 我的隨身圖庫")
    
    if not st.session_state.gallery_entries:
        st.info("尚無影像紀錄。")
    else:
        sorted_gallery = sorted(st.session_state.gallery_entries, key=lambda x: x["date"], reverse=True)
        
        # 篩選過濾器
        filter_cat = st.radio("篩選分類", ["全部", "🏋️ 動作與課表", "🥗 飲食紀錄", "💪 體態與其他"], horizontal=True)
        if filter_cat != "全部":
            sorted_gallery = [e for e in sorted_gallery if e.get("category") == filter_cat]
            
        if not sorted_gallery:
            st.caption(f"尚無「{filter_cat}」的影像紀錄。")
        else:
            # 🔥 核心優化：按照日期分組 (Grouping)
            grouped_gallery = defaultdict(list)
            for entry in sorted_gallery:
                date_str = entry["date"][:10]  # 只取 YYYY-MM-DD
                grouped_gallery[date_str].append(entry)
                
            # 將分組後的資料用 Expander 摺疊顯示
            for date_str in sorted(grouped_gallery.keys(), reverse=True):
                images_in_date = grouped_gallery[date_str]
                
                # 摺疊標題顯示日期與該日期的照片數量
                with st.expander(f"📅 {date_str} (共 {len(images_in_date)} 張)", expanded=False):
                    
                    # 展開後依然保持雙欄位顯示，節省空間
                    cols = st.columns(2)
                    for idx, entry in enumerate(images_in_date):
                        col = cols[idx % 2]
                        with col:
                            st.markdown(f"**{entry.get('category')}**")
                            
                            try:
                                # 將 Base64 文字解碼回圖片顯示
                                img_bytes = base64.b64decode(entry["image_base64"])
                                st.image(img_bytes, use_column_width=True)
                            except:
                                st.error("圖片載入失敗")
                                
                            if entry.get("notes"):
                                st.caption(f"📝 {entry['notes']}")
                            
                            if st.button("❌ 刪除", key=f"del_img_{entry['id']}", use_container_width=True):
                                st.session_state.gallery_entries = [e for e in st.session_state.gallery_entries if e["id"] != entry["id"]]
                                st.session_state.unsynced = True
                                st.rerun()
                            
                            st.divider() # 在同一欄位內的照片之間加上分隔線
