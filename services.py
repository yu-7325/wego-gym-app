# services.py

import streamlit as st
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_NAME, MUSCLE_GROUPS, WORKOUT_MUSCLE_MAPPING

# 現代運動科學：黃金動作輪替資料庫
ROTATION_SUGGESTIONS = {
    "槓鈴臥推": ["啞鈴臥推", "機械胸推", "雙槓撐體"],
    "上斜臥推": ["啞鈴上斜臥推", "機械上斜胸推"],
    "機械胸推": ["槓鈴臥推", "啞鈴飛鳥"],
    "肩推": ["啞鈴肩推", "機械肩推", "側平舉"],
    "引體向上": ["滑輪下拉", "機械寬距下拉", "啞鈴划船"],
    "深蹲": ["腿推機", "保加利亞單腿蹲", "六角槓硬舉"],
    "腿推機": ["深蹲", "保加利亞單腿蹲", "坐姿腿伸展"],
    "RDL": ["六角槓硬舉", "俯臥腿彎舉", "傳統硬舉"],
    "六角槓硬舉": ["RDL", "傳統硬舉", "深蹲"],
    "Clean": ["六角槓硬舉", "壺鈴Swing", "抓舉 (Snatch)"],
    "二頭彎舉": ["牧師凳彎舉", "搥式彎舉", "上斜啞鈴彎舉"],
    "繩索下拉": ["碎顱式 (Skull Crusher)", "雙槓撐體", "啞鈴頭後三頭伸展"]
}

@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def ensure_worksheets(sh):
    expected_sheets = ["Nutrition", "Workout", "CustomExercises", "BodyMetrics"]
    existing_sheets = [ws.title for ws in sh.worksheets()]
    for ws_name in expected_sheets:
        if ws_name not in existing_sheets:
            sh.add_worksheet(title=ws_name, rows="1000", cols="20")

def load_data():
    gc = get_gsheet_client()
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"找不到名為 '{SHEET_NAME}' 的試算表。請確認金鑰權限設定正確！")
        st.stop()
        
    ensure_worksheets(sh)
    
    nutri_records = sh.worksheet("Nutrition").get_all_records()
    for r in nutri_records: r["foodName"] = r["foodName"] if r["foodName"] != "" else None
        
    work_records = sh.worksheet("Workout").get_all_records()
    for r in work_records:
        r["duration"] = float(r["duration"]) if r["duration"] != "" else None
        r["distance"] = float(r["distance"]) if r["distance"] != "" else None
        r["notes"] = str(r["notes"]) if r["notes"] != "" else None
        r["rpe"] = float(r["rpe"]) if ("rpe" in r and r["rpe"] != "") else 8.0

    body_records = sh.worksheet("BodyMetrics").get_all_records()
    for r in body_records:
         r["weight"] = float(r["weight"]) if r["weight"] != "" else None
         r["body_fat"] = float(r["body_fat"]) if r["body_fat"] != "" else None
        
    custom_records = sh.worksheet("CustomExercises").get_all_records()
    custom_dict = {}
    for r in custom_records:
        plan_day = r.get("plan_day")
        ex = r.get("exercise_name")
        if plan_day not in custom_dict: custom_dict[plan_day] = []
        custom_dict[plan_day].append(ex)

    return {"nutrition": nutri_records, "workout": work_records, "body_metrics": body_records, "custom_exercises": custom_dict}

def update_worksheet(ws, data_list, default_headers):
    ws.clear()
    if not data_list:
        ws.update([default_headers])
        return
    headers = list(data_list[0].keys())
    rows = []
    for row_dict in data_list:
        row = [row_dict.get(h) if row_dict.get(h) is not None else "" for h in headers]
        rows.append(row)
    ws.update([headers] + rows)

def save_data(nutrition_entries, workout_entries, body_entries, custom_exercises):
    gc = get_gsheet_client()
    sh = gc.open(SHEET_NAME)
    update_worksheet(sh.worksheet("Nutrition"), nutrition_entries, ["id", "date", "type", "foodName", "protein", "carbs", "fat", "calories"])
    update_worksheet(sh.worksheet("Workout"), workout_entries, ["id", "date", "dayType", "exercise", "weight", "sets", "reps", "distance", "duration", "notes", "rpe"])
    update_worksheet(sh.worksheet("BodyMetrics"), body_entries, ["id", "date", "weight", "body_fat"])
    custom_list = [{"plan_day": pd, "exercise_name": ex} for pd, ex_list in custom_exercises.items() for ex in ex_list]
    update_worksheet(sh.worksheet("CustomExercises"), custom_list, ["plan_day", "exercise_name"])

def get_last_workout_data(workout_entries, exercise_name):
    sorted_workouts = sorted(workout_entries, key=lambda x: x["date"], reverse=True) if workout_entries else []
    for w in sorted_workouts:
        if w.get("exercise") == exercise_name and w.get("dayType") != "Cardio":
            return w.get("weight", 0.0), w.get("sets", 0), w.get("reps", 0)
    return 0.0, 0, 0 

def estimate_1rm(weight, reps):
    if reps <= 0 or weight <= 0: return 0.0
    if reps == 1: return weight
    return weight / (1.0278 - 0.0278 * reps) if reps < 37 else weight

def calculate_muscle_statuses(workout_entries):
    now = datetime.now()
    statuses = []
    sorted_workouts = sorted(workout_entries, key=lambda x: x["date"], reverse=True) if workout_entries else []
    
    for muscle, info in MUSCLE_GROUPS.items():
        latest_date = None
        for w in sorted_workouts:
            day_type = w.get("dayType", "")
            if muscle in WORKOUT_MUSCLE_MAPPING.get(day_type, []):
                latest_date = datetime.fromisoformat(w["date"])
                break
        
        hours_needed = info["recovery_hours"]
        if latest_date is None:
            progress = 1.0; remaining = 0.0; color = "green"
        else:
            elapsed_hours = (now - latest_date).total_seconds() / 3600.0
            progress = min(elapsed_hours / hours_needed, 1.0)
            remaining = max(hours_needed - elapsed_hours, 0.0)
            if progress >= 0.75: color = "green"
            elif progress >= 0.25: color = "orange"
            else: color = "red"
                
        statuses.append({"muscle": muscle, "latest_date": latest_date, "progress": progress, "remaining": remaining, "color": color})
    return statuses

# 🔥 擴充自調控引擎：加入長期適應性停滯（動作輪替）預測訊號
def get_auto_regulation_signals(workout_entries, exercise_name):
    history = [w for w in workout_entries if w.get('exercise') == exercise_name and w.get('weight', 0) > 0]
    if not history:
        return None, None, None
    
    daily_records = {}
    for w in history:
        d = w['date'][:10]
        if d not in daily_records: daily_records[d] = []
        daily_records[d].append(w)
    
    sorted_dates = sorted(daily_records.keys())
    
    # 1. 漸進性超負荷標竿
    last_day_sets = daily_records[sorted_dates[-1]]
    best_set = max(last_day_sets, key=lambda x: x['weight'])
    last_w = best_set['weight']
    last_r = best_set['reps']
    target_str = f"🎯 今日超負荷標竿：維持 **{last_w:.1f}kg 推 {int(last_r) + 1} 下**，或加重至 **{last_w + 2.5:.1f}kg**"
    
    fatigue_str = None
    rotation_str = None
    
    # 2. 短期中樞神經疲勞監控 (近 3 次訓練)
    if len(sorted_dates) >= 3:
        recent_dates = sorted_dates[-3:]
        recent_rpes = []
        recent_1rms = []
        for d in recent_dates:
            day_sets = daily_records[d]
            recent_rpes.extend([s.get('rpe', 8.0) for s in day_sets])
            day_max_1rm = max([estimate_1rm(s['weight'], s['reps']) for s in day_sets])
            recent_1rms.append(day_max_1rm)
            
        avg_rpe = sum(recent_rpes) / len(recent_rpes) if recent_rpes else 0
        short_slope = recent_1rms[-1] - recent_1rms[0]
        if avg_rpe >= 8.5 and short_slope <= 0:
            fatigue_str = f"系統偵測到短期中樞神經累積疲勞 (近期 RPE 高達 {avg_rpe:.1f} 且力量卡關)。建議本動作安排【減量 Deload】，降重 15% 以利神經恢復！"

    # 3. 長期適應性停滯監控 (近 4 次訓練線性迴歸斜率預測)
    if len(sorted_dates) >= 4:
        long_dates = sorted_dates[-4:]
        long_1rms = []
        for d in long_dates:
            day_sets = daily_records[d]
            day_max_1rm = max([estimate_1rm(s['weight'], s['reps']) for s in day_sets])
            long_1rms.append(day_max_1rm)
            
        # 純原生無當機線性迴歸斜率計算
        n = len(long_1rms)
        x_mean = 1.5
        y_mean = sum(long_1rms) / n
        num = sum((i - x_mean) * (long_1rms[i] - y_mean) for i in range(n))
        den = sum((i - x_mean)**2 for i in range(n))
        long_slope = num / den if den != 0 else 0
        
        # 如果長期成長斜率平躺或下滑 (<= 0)，觸發動作更換建議
        if long_slope <= 0:
            alt_list = ROTATION_SUGGESTIONS.get(exercise_name, ["同肌群的其他變化動作（如切換啞鈴或機械角度）"])
            rotation_str = f"🔄 動作輪替建議：該動作的 1RM 成長動能已連續 4 次訓練陷入停滯或下滑（長期斜率: {long_slope:.2f}）。肌肉可能已產生神經適應，建議在下個小週期（Mesocycle）將此動作暫時替換為：**【{ '、'.join(alt_list) }】**，給予肌肉全新角度的機械張力刺激！"
            
    return target_str, fatigue_str, rotation_str
