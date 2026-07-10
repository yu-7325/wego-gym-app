# config.py

MEAL_TYPES = ["早餐", "午餐", "練前餐", "練後餐", "晚餐", "宵夜"]
SHEET_NAME = "WeGoGYM_Database"

WORKOUT_MUSCLE_MAPPING = {
    "Chest Day": ["Chest", "Triceps", "Shoulders"],
    "Back Day": ["Back", "Biceps", "Forearms"],
    "Leg Day": ["Legs", "Abs"],
    "Power Day": ["Abs", "Back", "Legs"],
    "Chest+Tricep": ["Chest", "Triceps"],
    "Back+Biceps": ["Back", "Biceps"],
    "Shoulder+Chest": ["Shoulders", "Chest"],
    "Hamstring+Back": ["Legs", "Back"],
    "Arm Day": ["Biceps", "Triceps", "Forearms"],
    "Cardio": []
}

MUSCLE_GROUPS = {
    "Chest": {"recovery_hours": 48}, 
    "Back": {"recovery_hours": 72},
    "Legs": {"recovery_hours": 72}, 
    "Abs": {"recovery_hours": 24},
    "Biceps": {"recovery_hours": 24}, 
    "Shoulders": {"recovery_hours": 48},
    "Triceps": {"recovery_hours": 48}, 
    "Forearms": {"recovery_hours": 24}
}

ROUTINE_PLANS = {
    "4日力量與有氧 (目前)": {
        "days": ["Chest Day", "Back Day", "Leg Day", "Power Day", "Cardio"],
        "exercises": {
            "Chest Day": ["槓鈴臥推", "機械胸推", "上斜臥推", "肩推", "側平舉&飛鳥", "機械夾胸", "繩索下拉", "壺鈴三頭", "機械卷腹"],
            "Back Day": ["引體向上", "機械上背", "機械下背", "機械下拉", "直臂下拉", "繩索面拉", "反式飛鳥", "二頭彎舉", "機械卷腹"],
            "Leg Day": ["深蹲", "腿推機", "保加利亞", "RDL", "北歐彎舉", "負重提踵", "機械卷腹"],
            "Power Day": ["Clean", "Snatch", "六角槓硬舉", "壺鈴swing", "藥球下砸", "機械卷腹"],
            "Cardio": ["跑步機", "飛輪", "滑步機", "登階機", "跳繩", "戶外跑"]
        }
    },
    "6日健美分化 (新計畫)": {
        "days": ["Leg Day", "Chest+Tricep", "Back+Biceps", "Shoulder+Chest", "Hamstring+Back", "Arm Day", "Cardio"],
        "exercises": {
            "Leg Day": ["深蹲", "腿推機", "保加利亞", "坐姿腿伸展", "負重提踵", "機械卷腹"],
            "Chest+Tricep": ["槓鈴臥推", "上斜臥推", "機械胸推", "雙槓撐體", "繩索下拉", "機械卷腹"],
            "Back+Biceps": ["引體向上", "機械下拉", "機械上背", "機械下背", "單臂亞鈴划船", "二頭彎舉", "機械卷腹"],
            "Shoulder+Chest": ["肩推", "側平舉&飛鳥", "反式飛鳥", "啞鈴前平舉", "機械夾胸", "機械卷腹"],
            "Hamstring+Back": ["RDL", "北歐彎舉", "六角槓硬舉", "俯臥腿彎舉", "直臂下拉", "機械卷腹"],
            "Arm Day": ["壺鈴三頭", "二頭彎舉", "繩索面拉", "牧師凳彎舉", "碎顱式", "機械卷腹"],
            "Cardio": ["跑步機", "飛輪", "滑步機", "登階機", "跳繩", "戶外跑"]
        }
    }
}