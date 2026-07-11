import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from config import MUSCLE_GROUPS, WORKOUT_MUSCLE_MAPPING
import services

def render():
    analysis_option = st.selectbox(
        "📊 請選擇分析圖表", 
        ["⚖️ 體態與熱量分析 (含 7 日均線)", "📊 肌肉部位容量與有效組數 (肌肥大指標)", "🏆 1RM 成長斜率與均線預測", "🏋️ 訓練總容量趨勢"]
    )
    st.divider()

    only_effective = False
    if analysis_option in ["📊 肌肉部位容量與有效組數 (肌肥大指標)", "🏋️ 訓練總容量趨勢"]:
        only_effective = st.checkbox("🎯 容量計算僅篩選高強度組 (RPE ≥ 8.0)", value=False)

    if analysis_option == "⚖️ 體態與熱量分析 (含 7 日均線)":
        st.header("⚖️ 體態與熱量分析")
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
            
            st.markdown("#### 攝取熱量 (kcal)")
            cal_bar = alt.Chart(chart_df).mark_bar(color='#5C9DF5', opacity=0.5).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('單日熱量:Q', title='熱量 (kcal)'),
                tooltip=['date_str', '單日熱量']
            )
            cal_line = alt.Chart(chart_df).mark_line(color='#FFA500', strokeWidth=3).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('7日平均熱量:Q', title='熱量 (kcal)'),
                tooltip=['date_str', alt.Tooltip('7日平均熱量', format='.0f')]
            )
            st.altair_chart(cal_bar + cal_line, use_container_width=True)
            
            st.markdown("#### 體重變化 (kg)")
            wt_point = alt.Chart(chart_df).mark_circle(color='#FF4B4B', opacity=0.4, size=60).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('單日體重:Q', title='體重 (kg)', scale=alt.Scale(zero=False)),
                tooltip=['date_str', '單日體重']
            )
            wt_line = alt.Chart(chart_df).mark_line(color='#FF4B4B', strokeWidth=3).encode(
                x=alt.X('date_str:O', title='日期'),
                y=alt.Y('7日平均體重:Q', title='體重 (kg)', scale=alt.Scale(zero=False)),
                tooltip=['date_str', alt.Tooltip('7日平均體重', format='.1f')]
            )
            st.altair_chart(wt_point + wt_line, use_container_width=True)
        else:
            st.info("💡 需要同時擁有「飲食紀錄」與「體重紀錄」才能解鎖分析圖表！")

    elif analysis_option == "📊 肌肉部位容量與有效組數 (肌肥大指標)":
        st.header("📊 肌肉部位容量與有效組數")
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
                st.subheader("🔥 近 7 日單部位有效組數 (Hard Sets)")
                st.caption("肌肥大黃金區間：8~18組。超過 18 組可能進入垃圾容量並導致過度訓練。")
                
                sets_list = []
                for m, s in hard_sets_data.items():
                    status = "維持期 (<8組)" if s < 8 else ("黃金生長期 (8-18組)" if s <= 18 else "疲勞警戒 (>18組)")
                    sets_list.append({"部位": m, "有效組數": s, "狀態": status})
                
                df_sets = pd.DataFrame(sets_list)
                color_scale = alt.Scale(domain=["維持期 (<8組)", "黃金生長期 (8-18組)", "疲勞警戒 (>18組)"], range=["#5C9DF5", "#2e7d32", "#FF4B4B"])
                
                sets_chart = alt.Chart(df_sets).mark_bar().encode(
                    x=alt.X('部位:O', title='肌肉部位', sort='-y'),
                    y=alt.Y('有效組數:Q', title='近 7 日有效組數'),
                    color=alt.Color('狀態:N', scale=color_scale),
                    tooltip=['部位', '有效組數', '狀態']
                )
                
                rule_18 = alt.Chart(pd.DataFrame({'y': [18]})).mark_rule(color='red', strokeDash=[5,5]).encode(y='y:Q')
                rule_8 = alt.Chart(pd.DataFrame({'y': [8]})).mark_rule(color='orange', strokeDash=[5,5]).encode(y='y:Q')
                st.altair_chart(sets_chart + rule_18 + rule_8, use_container_width=True)
                
                st.divider()
                st.subheader("📦 歷史累積總容量 (Tonnage)")
                df_muscle = pd.DataFrame(list(muscle_vol_data.items()), columns=['部位', '累積總容量 (kg)'])
                chart_df = pd.DataFrame({"部位": df_muscle["部位"].astype(str), "累積總容量": df_muscle["累積總容量 (kg)"].astype(float)})
                
                muscle_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('部位:O', title='肌肉部位', sort='-y'),
                    y=alt.Y('累積總容量:Q', title='累積總容量 (kg)'),
                    tooltip=[alt.Tooltip('部位:O', title='部位'), alt.Tooltip('累積總容量:Q', title='總容量 (kg)', format='.1f')]
                )
                st.altair_chart(muscle_chart, use_container_width=True)
            else:
                st.write("目前尚無符合條件的重量訓練數據。")
        else:
            st.write("目前尚無任何訓練數據。")

    elif analysis_option == "🏆 1RM 成長斜率與均線預測":
        st.header("🏆 力量成長動能分析 (EMA & 迴歸斜率)")
        if st.session_state.workout_entries:
            df_all = pd.DataFrame(st.session_state.workout_entries)
            for col in ['weight', 'sets', 'reps', 'exercise', 'date']:
                if col not in df_all.columns: df_all[col] = 0.0 if col in ['weight', 'sets', 'reps'] else ""
            df_weight_only = df_all[df_all['weight'] > 0].copy()
            
            if not df_weight_only.empty:
                df_weight_only['estimated_1rm'] = df_weight_only.apply(lambda row: services.estimate_1rm(row['weight'], row['reps']), axis=1)
                unique_exercises = sorted(df_weight_only['exercise'].unique())
                selected_track_ex = st.selectbox("🎯 選擇要計算成長動能的動作：", unique_exercises)
                
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
                    col_m1.metric(label="目前估算最高 1RM", value=f"{df_daily_1rm['estimated_1rm'].max():.1f} kg")
                    col_m2.metric(label="近期力量底線 (EMA)", value=f"{df_daily_1rm['EMA (短期趨勢)'].iloc[-1]:.1f} kg")
                    col_m3.metric(label="🚀 成長動能 (預測斜率)", value=f"{slope:.2f} kg / 次", delta="力量上升期" if slope > 0.2 else ("陷入停滯" if slope < -0.2 else "持平穩定"))
                    st.divider()
                    
                    df_daily_1rm.rename(columns={'estimated_1rm': '當日估算 1RM'}, inplace=True)
                    df_melted = df_daily_1rm.melt(id_vars=['date_str'], value_vars=['當日估算 1RM', 'EMA (短期趨勢)'], var_name='指標類型', value_name='重量 (kg)')
                    chart_df = pd.DataFrame({"date_str": df_melted["date_str"].astype(str), "指標類型": df_melted["指標類型"].astype(str), "重量 (kg)": df_melted["重量 (kg)"].astype(float)})
                    
                    track_chart = alt.Chart(chart_df).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('date_str:O', title='日期'),
                        y=alt.Y('重量 (kg):Q', title='估算最大力量 (kg)', scale=alt.Scale(zero=False)),
                        color=alt.Color('指標類型:N', scale=alt.Scale(domain=['當日估算 1RM', 'EMA (短期趨勢)'], range=['#5C9DF5', '#FFA500'])),
                        tooltip=[alt.Tooltip('date_str:O', title='日期'), alt.Tooltip('指標類型:N', title='類型'), alt.Tooltip('重量 (kg):Q', title='重量 (kg)', format='.1f')]
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
            for col in ['weight', 'sets', 'reps', 'date', 'rpe']:
                if col not in df_w.columns: df_w[col] = 0.0 if col in ['weight', 'sets', 'reps', 'rpe'] else ""
            
            if only_effective:
                df_w = df_w[df_w['rpe'] >= 8.0]
                    
            if not df_w.empty and 'weight' in df_w.columns and not df_w[df_w['weight'] > 0].empty:
                df_weights = df_w[df_w['weight'] > 0].copy()
                time_interval = st.radio("選擇檢視區間：", ["日 (Daily)", "週 (Weekly)", "月 (Monthly)"], horizontal=True)
                df_weights['date_obj'] = pd.to_datetime(df_weights['date'].str[:10])
                df_weights['volume'] = df_weights['weight'] * df_weights['sets'] * df_weights['reps']
                
                if time_interval == "日 (Daily)": df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m-%d'); x_title = "日期"
                elif time_interval == "週 (Weekly)": df_weights['period'] = (df_weights['date_obj'] - pd.to_timedelta(df_weights['date_obj'].dt.dayofweek, unit='d')).dt.strftime('%Y-%m-%d (週一)'); x_title = "週度"
                else: df_weights['period'] = df_weights['date_obj'].dt.strftime('%Y-%m'); x_title = "月份"
                
                vol_trend = df_weights.groupby('period')['volume'].sum().reset_index()
                chart_df = pd.DataFrame({"period": vol_trend["period"].astype(str), "volume": vol_trend["volume"].astype(float)})
                
                vol_chart = alt.Chart(chart_df).mark_bar(color='#5C9DF5').encode(
                    x=alt.X('period:O', title=x_title, sort=None),
                    y=alt.Y('volume:Q', title='總容量 (kg)'),
                    tooltip=[alt.Tooltip('period:O', title=x_title), alt.Tooltip('volume:Q', title='總容量 (kg)', format='.1f')]
                )
                st.altair_chart(vol_chart, use_container_width=True)
            else:
                st.write("目前尚無符合篩選條件的重量訓練數據。")
