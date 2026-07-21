# views/gallery.py

import streamlit as st
import uuid
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO
from collections import defaultdict

def process_image(uploaded_file):
    try:
        img = Image.open(uploaded_file)
        img = img.convert("RGB")
        
        # 🔥 動態畫質榨取引擎 (Dynamic Compression)
        # 為了能在 Google Sheets 5萬字元限制下，保留最高的截圖/文字清晰度
        max_size = (1024, 1024)
        img.thumbnail(max_size)
        
        quality = 90
        while quality > 10:
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=quality)
            b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Google Sheets 單一儲存格極限約 50,000 字元，抓 45,000 當安全線
            if len(b64_str) < 45000:
                return b64_str
            quality -= 10 # 如果太大，降低一點畫質再試一次
            
        # 如果真的極限了還是塞不下，再降一階解析度保底
        img.thumbnail((600, 600))
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=50)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
        
    except Exception as e:
        st.error(f"圖片處理失敗: {e}")
        return None

def render():
    st.header("📷 影像與備忘圖庫")
    st.caption("上傳您的課表截圖、飲食照片或體態紀錄。系統會自動計算雲端安全極限以保留最高畫質。")
    
    with st.form("gallery_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("選擇圖片上傳", type=["jpg", "jpeg", "png", "webp"])
        with col2:
            img_category = st.selectbox("標籤分類", ["🏋️ 動作與課表", "🥗 飲食紀錄", "💪 體態與其他"])
            
        img_notes = st.text_input("簡單備註 (例如：深蹲站距微調、新買的高蛋白)")
        
        if st.form_submit_button("💾 上傳並儲存圖片", type="primary", use_container_width=True):
            if uploaded_file is not None:
                with st.spinner("正在進行動態無損極限壓縮..."):
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
        # 🔥 核心優化：按照「標籤分類 (Category)」分組
        grouped_gallery = defaultdict(list)
        for entry in st.session_state.gallery_entries:
            cat = entry.get("category", "未分類")
            grouped_gallery[cat].append(entry)
            
        # 顯示各個標籤的摺疊選單
        category_order = ["🏋️ 動作與課表", "🥗 飲食紀錄", "💪 體態與其他", "未分類"]
        sorted_categories = sorted(grouped_gallery.keys(), key=lambda x: category_order.index(x) if x in category_order else 99)

        for cat in sorted_categories:
            images_in_cat = grouped_gallery[cat]
            
            # 展開選單標題為標籤分類
            with st.expander(f"{cat} (共 {len(images_in_cat)} 張紀錄)", expanded=False):
                # 進入分類後，內部依照上傳時間(新->舊)排序
                sorted_images = sorted(images_in_cat, key=lambda x: x["date"], reverse=True)
                
                cols = st.columns(2)
                for idx, entry in enumerate(sorted_images):
                    col = cols[idx % 2]
                    with col:
                        st.markdown(f"**📅 {entry['date'][:10]}**") # 裡面改顯示日期
                        
                        try:
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
                        
                        st.divider()
