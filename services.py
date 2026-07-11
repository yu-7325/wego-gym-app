# services.py

import streamlit as st
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_NAME, MUSCLE_GROUPS, WORKOUT_MUSCLE_MAPPING

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
        # 安全讀取 rpe 欄位，賦予預設值 8.0
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
    # 確保寫入時包含 rpe 欄位
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
