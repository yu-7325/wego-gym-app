# views/analytics.py

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from collections import defaultdict  # 確保核心分類字典載入正確
from config import MUSCLE_GROUPS, WORKOUT_MUSCLE_MAPPING
import services

def render():
    st.header("📈 量化訓練大數據中樞")
    
    # 讀取全域大週期目標狀態
    current_goal = st.session_state.get("current_goal", "🥩 增肌期 (Hypertrophy)")
    st.caption(f"📊 當前主戰術目標連動中：`{current_goal}`")
    
    # ─── 7 大硬核重訓科學視角選單 ───
    analysis_option = st.selectbox(
        "🔮 切換數據分析視角", 
        [
            "⚖️ 體態與熱量分析 (含 7 日均線)", 
            "📊 肌肉部位容量與有效組數 (肌肥大指標)", 
            "🏆 1RM 成長斜率與均線預測", 
            "🏋️ 訓練總容量趨勢", 
            "✨ 個體化黃金動作 (SFR 評分)",
            "🔄 結構推拉平衡分析 (黃金結構比)",
            "📉 組間表現衰退率追蹤 (神經續航力)"
        ]
    )
    st.divider()

    # 特定容量圖表專用的高強度過濾器
    only_effective = False
    if analysis_option in ["📊 肌肉部位容量與有效組數 (肌肥大指標)", "🏋️ 訓練總容量趨勢"]:
        only_effective = st.checkbox("🎯 僅篩選高強度有效組 (RPE ≥ 8.0) 進行總量計算", value=False)

    # ==========================================
    # 視角一：⚖️ 體態與熱量分析 (含 7 日均線)
    # ==========================================
    if analysis_option == "⚖️ 體態與熱量分析 (含 7 日均線)":
        if st.session_state.nutrition_entries and st.session_state.body_entries:
            df_n = pd.DataFrame(st.session_state.nutrition_entries)
            df_n['date_str'] = df_n['date'].str[:10]
            daily_cal = df_n.groupby('date_str')['calories'].sum().reset_index()
            
            df_b = pd.DataFrame(st.session_state.body_entries)
            df_b['date_str'] = df_b['date'].str[:10]
            
            merged_df = pd.merge(daily_cal, df_b[['date_str', 'weight']], on='date_str', how='outer')
            merged_df = merged_df.sort_values('date_str')
            
            merged_df['weight'] = pd.to_numeric(merged_df['weight'], errors='coerce').bfill().ffill().fillna(0.0)
            merged_df['calories'] = pd.to_numeric(merged_df['calories'], errors='coerce').fillna(0.0)
            
            merged_df['weight_7d'] = merged_df['weight'].replace(0.0, float('nan')).rolling(window=7, min_periods=1).mean()
            merged_df['cal_7d'] = merged_df['calories'].replace(0.0, float('nan')).rolling(window=7, min_periods=1).mean()
            
            chart_df = pd.DataFrame({
                "date_str": merged_df["date_str"].astype(str),
                "單日熱量": merged_df["calories"].fillna(0).astype(float),
                "7日平均熱量": merged_df["cal_7d"].fillna(0).astype(float),
                "單日體重": merged_df["weight"].fillna(0).astype(float),
                "7日平均體重": merged_df["weight_7d"].fillna(0).astype(float)
            })
            
            st.markdown("#### 🥦 攝取熱量滾動趨勢 (kcal)")
            cal_bar = alt.Chart(chart_df).mark_bar(color='#5C9DF5', opacity=0.4).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('單日熱量:Q', title='熱量 (kcal)'),
                tooltip=['date_str', '單日熱量']
            )
            cal_line = alt.Chart(chart_df).mark_line(color='#FFA500', strokeWidth=3).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('7日平均熱量:Q', title='7日MA熱量'),
                tooltip=['date_str', alt.Tooltip('7日平均熱量', format='.0f')]
            )
            st.altair_chart(cal_bar + cal_line, use_container_width=True)
            
            st.markdown("#### ⚖️ 體重滾動均線趨勢 (kg)")
            wt_point = alt.Chart(chart_df).mark_circle(color='#FF4B4B', opacity=0.3, size=50).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('單日體重:Q', title='體重 (kg)', scale=alt.Scale(zero=False)),
                tooltip=['date_str', '單日體重']
            )
            wt_line = alt.Chart(chart_df).mark_line(color='#FF4B4B', strokeWidth=3).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('7日平均體重:Q', title='7日MA體重', scale=alt.Scale(zero=False)),
                tooltip=['date_str', alt.Tooltip('7日平均體重', format='.1f')]
            )
            st.altair_chart(wt_point + wt_line, use_container_width=True)
        else:
            st.info("💡 需要同時擁有「飲食紀錄」與「體重紀錄」才能解鎖分析圖表！")

    # ==========================================
    # 視角二：📊 肌肉部位容量與有效組數 (肌肥大指標)
    # ==========================================
    elif analysis_option == "📊 肌肉部位容量與有效組數 (肌肥大指標)":
        if st.session_state.workout_entries:
            muscle_vol_data = {m: 0.0 for m in MUSCLE_GROUPS.keys()}
            hard_sets_data = {m: 0 for m in MUSCLE_GROUPS.keys()}
            today = pd.to_datetime(datetime.now().date())
            seven_days_ago = today - pd.Timedelta(days=7)
            has_valid_data = False
            
            for w in st.session_state.workout_entries:
                if w.get("weight", 0) > 0 and w.get("sets", 0) > 0 and w.get("reps", 0) > 0:
                    rpe = w.get("rpe", 8.0)
                    vol = w["weight"] * w["sets"] * w["reps"]
                    day_type = w.get("dayType", "Other")
                    w_date = pd.to_datetime(w["date"][:10])
                    
                    if not (only_effective and rpe < 8.0):
                        for muscle in WORKOUT_MUSCLE_MAPPING.get(day_type, []):
                            if muscle in muscle_vol_data:
                                muscle_vol_data[muscle] += vol
                                has_valid_data = True
                    
                    if rpe >= 8.0 and seven_days_ago <= w_date <= today:
                        for muscle in WORKOUT_MUSCLE_MAPPING.get(day_type, []):
                            if muscle in hard_sets_data:
                                hard_sets_data[muscle] += w["sets"]
            
            if has_valid_data:
                st.markdown("#### 🔥 近 7 日單部位有效組數 (Hard Sets)")
                
                sets_list = []
                for m, s in hard_sets_data.items():
                    # 傳入全域大週期目標動態精算個人恢復上限
                    dynamic_mrv = services.calculate_dynamic_mrv(st.session_state.workout_entries, m, current_goal)
                    
                    if s < 8: status = "維持期 (不足 8 組)"
                    elif s <= dynamic_mrv: status = "黃金生長期 (適當)"
                    else: status = "疲勞警戒 (超量)"
                    
                    sets_list.append({
                        "部位": m, 
                        "有效組數": s, 
                        "狀態": status, 
                        "當前MRV上限": dynamic_mrv
                    })
                
                df_sets = pd.DataFrame(sets_list)
                st.caption("長條圖顏色代表您的當前狀態。若您的個人 MRV 因週期目標或疲勞下修，柱子將會提早轉為紅色警戒。")
                
                color_scale = alt.Scale(
                    domain=["維持期 (不足 8 組)", "黃金生長期 (適當)", "疲勞警戒 (超量)"], 
                    range=["#5C9DF5", "#2e7d32", "#FF4B4B"]
                )
                
                sets_chart = alt.Chart(df_sets).mark_bar(opacity=0.85).encode(
                    x=alt.X('部位:O', title='肌肉部位', sort='-y'),
                    y=alt.Y('有效組數:Q', title='有效組數 (組)'),
                    color=alt.Color('狀態:N', scale=color_scale, title="生長狀態"),
                    tooltip=['部位', '有效組數', '狀態', alt.Tooltip('當前MRV上限', title="專屬過度訓練界線")]
                )
                
                # 根據當前目標動態決定全域紅色虛線基準落點
                if "力量" in current_goal: line_mrv = 14
                elif "減脂" in current_goal: line_mrv = 15
                elif "復健" in current_goal: line_mrv = 8
                else: line_mrv = 18
                
                rule_8 = alt.Chart(pd.DataFrame({'y': [8]})).mark_rule(color='#FFA500', strokeDash=[5, 5], strokeWidth=2).encode(y='y:Q')
                rule_mrv = alt.Chart(pd.DataFrame({'y': [line_mrv]})).mark_rule(color='#FF4B4B', strokeDash=[5, 5], strokeWidth=2).encode(y='y:Q')
                
                st.altair_chart(sets_chart + rule_8 + rule_mrv, use_container_width=True)
                
                # 下方累積容量圖
                st.markdown("#### 📦 歷史累積總訓練容量 (Tonnage)")
                df_muscle = pd.DataFrame(list(muscle_vol_data.items()), columns=['部位', '累積總容量 (kg)'])
                chart_df = pd.DataFrame({"部位": df_muscle["部位"].astype(str), "累積總容量": df_muscle["累積總容量 (kg)"].astype(float)})
                
                muscle_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('部位:O', title='肌肉部位', sort='-y'),
                    y=alt.Y('累積總容量:Q', title='累積容量 (kg)'),
                    tooltip=[alt.Tooltip('部位:O', title='部位'), alt.Tooltip('累積總容量:Q', title='總容量 (kg)', format='.1f')]
                )
                st.altair_chart(muscle_chart, use_container_width=True)
            else:
                st.info("尚無符合條件的重量訓練數據。")
        else:
            st.info("尚無任何訓練數據。")

    # ==========================================
    # 視角三：🏆 1RM 成長斜率與均線預測
    # ==========================================
    elif analysis_option == "🏆 1RM 成長斜率與均線預測":
        if st.session_state.workout_entries:
            df_all = pd.DataFrame(st.session_state.workout_entries)
            for col in ['weight', 'sets', 'reps', 'exercise', 'date']:
                if col not in df_all.columns: df_all[col] = 0.0 if col in ['weight', 'sets', 'reps'] else ""
            df_weight_only = df_all[df_all['weight'] > 0].copy()
            
            if not df_weight_only.empty:
                df_weight_only['estimated_1rm'] = df_weight_only.apply(lambda row: services.estimate_1rm(row['weight'], row['reps']), axis=1)
                unique_exercises = sorted(df_weight_only['exercise'].unique())
                selected_track_ex = st.selectbox("🎯 選擇動作計算斜率", unique_exercises)
                
                df_track = df_weight_only[df_weight_only['exercise'] == selected_track_ex].copy()
                df_track['date_str'] = df_track['date'].str[:10]
                df_daily_1rm = df_track.groupby('date_str')['estimated_1rm'].max().reset_index().sort_values('date_str')
                
                if not df_daily_1rm.empty:
                    df_daily_1rm['estimated_1rm'] = pd.to_numeric(df_daily_1rm['estimated_1rm'], errors='coerce')
                    df_daily_1rm['EMA (短期趨勢)'] = df_daily_1rm['estimated_1rm'].ewm(span=3, adjust=False).mean()
                    
                    df_daily_1rm['x_index'] = range(len(df_daily_1rm))
                    slope = 0.0
                    if len(df_daily_1rm) > 1:
                        cov = df_daily_1rm['estimated_1rm'].astype(float).cov(df_daily_1rm['x_index'].astype(float))
                        var = df_daily_1rm['x_index'].astype(float).var()
                        slope = cov / var if var != 0 else 0.0
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric(label="最高估算 1RM", value=f"{df_daily_1rm['estimated_1rm'].max():.1f} kg")
                    col_m2.metric(label="近期神經實力 (EMA)", value=f"{df_daily_1rm['EMA (短期趨勢)'].iloc[-1]:.1f} kg")
                    col_m3.metric(label="🚀 成長動能斜率", value=f"{slope:.2f} kg/次", delta="上升期" if slope > 0.2 else ("停滯期" if slope < -0.2 else "穩定"))
                    st.divider()
                    
                    df_daily_1rm.rename(columns={'estimated_1rm': '當日估算 1RM'}, inplace=True)
                    df_melted = df_daily_1rm.melt(id_vars=['date_str'], value_vars=['當日估算 1RM', 'EMA (短期趨勢)'], var_name='指標', value_name='重量 (kg)')
                    chart_df = pd.DataFrame({"date_str": df_melted["date_str"].astype(str), "指標": df_melted["指標"].astype(str), "重量 (kg)": df_melted["重量 (kg)"].astype(float)})
                    
                    track_chart = alt.Chart(chart_df).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('date_str:O', title='日期'),
                        y=alt.Y('重量 (kg):Q', title='重量 (kg)', scale=alt.Scale(zero=False)),
                        color=alt.Color('指標:N', scale=alt.Scale(domain=['當日估算 1RM', 'EMA (短期趨勢)'], range=['#5C9DF5', '#FFA500'])),
                        tooltip=['date_str', '指標', alt.Tooltip('重量 (kg)', format='.1f')]
                    )
                    st.altair_chart(track_chart, use_container_width=True)
            else:
                st.info("尚無重訓數據。")
        else:
            st.info("尚無任何訓練數據。")

    # ==========================================
    # 視角四：🏋️ 訓練總容量趨勢
    # ==========================================
    elif analysis_option == "🏋️ 訓練總容量趨勢":
        if st.session_state.workout_entries:
            df_w = pd.DataFrame(st.session_state.workout_entries)
            for col in ['weight', 'sets', 'reps', 'date', 'rpe']:
                if col not in df_w.columns: df_w[col] = 0.0 if col in ['weight', 'sets', 'reps', 'rpe'] else ""
            if only_effective: df_w = df_w[df_w['rpe'] >= 8.0]
                    
            if not df_w.empty and 'weight' in df_w.columns and not df_w[df_w['weight'] > 0].empty:
                df_weights = df_w[df_w['weight'] > 0].copy()
                time_interval = st.radio("時間檢視區間", ["日 (Daily)", "週 (Weekly)", "月 (Monthly)"], horizontal=True)
                df_weights['date_obj'] = pd.to_datetime(df_weights['date'].str[:10])
                df_weights['volume'] = df_weights['weight'] * df_weights['sets'] * df_weights['reps']
                
                if time_interval == "日 (Daily)": df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m-%d'); x_title = "日期"
                elif time_interval == "週 (Weekly)": df_weights['period'] = (df_weights['date_obj'] - pd.to_timedelta(df_weights['date_obj'].dt.dayofweek, unit='d')).dt.strftime('%Y-%m-%d (週一)'); x_title = "週度"
                else: df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m'); x_title = "月份"
                
                vol_trend = df_weights.groupby('period')['volume'].sum().reset_index()
                chart_df = pd.DataFrame({"period": vol_trend["period"].astype(str), "volume": vol_trend["volume"].astype(float)})
                
                vol_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('period:O', title=x_title, sort=None),
                    y=alt.Y('volume:Q', title='總訓練量 (kg)'),
                    tooltip=['period', alt.Tooltip('volume', format='.1f')]
                )
                st.altair_chart(vol_chart, use_container_width=True)
            else:
                st.info("尚無符合篩選條件的重訓數據。")

    # ==========================================
    # 視角五：✨ 個體化黃金動作 (SFR 評分)
    # ==========================================
    elif analysis_option == "✨ 個體化黃金動作 (SFR 評分)":
        st.markdown("#### ✨ 我的黃金 SFR 動作榜單")
        if st.session_state.workout_entries:
            top_sfr = services.get_top_sfr_exercises(st.session_state.workout_entries)
            if top_sfr:
                sfr_list = [{"排名": i+1, "訓練動作": ex, "平均 SFR 效益分數": round(score, 2)} for i, (ex, score) in enumerate(top_sfr)]
                st.table(pd.DataFrame(sfr_list).set_index("排名"))
                st.info("💡 數據解讀：平均 SFR 分數越高，代表該動作能為你帶來最高的肌肉泵感，且關節幾乎沒有不適感。")
            else:
                st.info("尚無足夠的 SFR 自評數據。")
        else:
            st.info("尚無任何訓練數據。")

    # ==========================================
    # 視角六：🔄 結構推拉平衡分析 (黃金結構比)
    # ==========================================
    elif analysis_option == "🔄 結構推拉平衡分析 (黃金結構比)":
        st.markdown("#### 🔄 近期結構推拉動作容量平衡圖")
        st.caption("科學健美建議：為了長線力量突破與預防圓肩受傷，【水平/垂直拉】的累積總量應大於或等於【水平/垂直推】。")
        if st.session_state.workout_entries:
            pattern_data = defaultdict(float)
            has_data = False
            for w in st.session_state.workout_entries:
                ex = w.get('exercise')
                if ex in services.MOVEMENT_PATTERNS and w.get('weight', 0) > 0:
                    vol = w['weight'] * w['sets'] * w['reps']
                    pattern = services.MOVEMENT_PATTERNS[ex]
                    pattern_data[pattern] += vol
                    has_data = True
            
            if has_data:
                df_pattern = pd.DataFrame(list(pattern_data.items()), columns=["動作模式", "累積訓練量(kg)"])
                pattern_chart = alt.Chart(df_pattern).mark_bar().encode(
                    x=alt.X('累積訓練量(kg):Q', title="總容量 (kg)"),
                    y=alt.Y('動作模式:N', sort='-x', title="動作模式"),
                    color=alt.Color('動作模式:N', legend=None),
                    tooltip=['動作模式', alt.Tooltip('累積訓練量(kg)', format='.1f')]
                )
                st.altair_chart(pattern_chart, use_container_width=True)
            else:
                st.info("尚無足夠的重訓容量數據來計算推拉比。")
        else:
            st.info("尚無訓練數據。")

    # ==========================================
    # 視角七：📉 組間表現衰退率追蹤 (神經續航力)
    # ==========================================
    elif analysis_option == "📉 組間表現衰退率追蹤 (神經續航力)":
        st.markdown("#### 📉 當日單一動作「組間表現衰退」追蹤")
        st.caption("追蹤您在同一個訓練日中，隨著組數增加，神經傳導與力量輸出的衰退幅度。衰退率過快代表該重量超出了你當前的神經工作容量（Work Capacity）。")
        if st.session_state.workout_entries:
            df_w = pd.DataFrame(st.session_state.workout_entries)
            df_w = df_w[df_w['weight'] > 0]
            if not df_w.empty:
                ex_options = sorted(df_w['exercise'].unique())
                selected_decay_ex = st.selectbox("🎯 選擇要檢視衰退率的核心動作：", ex_options, key="decay_ex_sel")
                
                df_ex = df_w[df_w['exercise'] == selected_decay_ex].copy()
                df_ex['date_str'] = df_ex['date'].str[:10]
                latest_date = df_ex['date_str'].max()
                
                # 撈出最近這一天該動作的所有組數細節
                df_today_sets = df_ex[df_ex['date_str'] == latest_date].copy()
                df_today_sets = df_today_sets.sort_values('date') # 依輸入時間排序組數
                df_today_sets['組序'] = range(1, len(df_today_sets) + 1)
                df_today_sets['估算1RM'] = df_today_sets.apply(lambda r: services.estimate_1rm(r['weight'], r['reps']), axis=1)
                
                if len(df_today_sets) >= 1:
                    first_1rm = df_today_sets['估算1RM'].iloc[0]
                    last_1rm = df_today_sets['估算1RM'].iloc[-1]
                    decay_pct = ((last_1rm - first_1rm) / first_1rm * 100) if first_1rm > 0 else 0
                    
                    col_d1, col_d2 = st.columns(2)
                    col_d1.metric("最近訓練日期", latest_date)
                    col_d2.metric("組間力量衰退率 (首組 vs 末組)", f"{decay_pct:.1f} %", delta="神經續航力優異" if decay_pct > -5 else "神經累積疲勞快", delta_color="inverse")
                    
                    st.divider()
                    
                    decay_chart = alt.Chart(df_today_sets).mark_line(point=True, strokeWidth=3, color='#FF4B4B').encode(
                        x=alt.X('組序:O', title="正式組順序 (Set)"),
                        y=alt.Y('估算1RM:Q', title="當組估算 1RM (kg)", scale=alt.Scale(zero=False)),
                        tooltip=['組序', 'weight', 'reps', 'rpe', alt.Tooltip('估算1RM', format='.1f')]
                    )
                    st.altair_chart(decay_chart, use_container_width=True)
            else:
                st.info("尚無重訓數據。")
        else:
            st.info("尚無任何訓練數據。")
