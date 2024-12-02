import os
import platform
from flask import Flask, render_template, request
import csv
import datetime
from collections import deque, defaultdict
import random
import sys

# 判別系統平台
CURRENT_PLATFORM = platform.system()

# 動態獲取基礎路徑
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 根據系統設置路徑分隔符（Windows: ;，macOS/Linux: :）
if CURRENT_PLATFORM == "Windows":
    PATH_SEPARATOR = ";"
else:  # macOS 或其他系統
    PATH_SEPARATOR = ":"

# Flask 應用初始化
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

def read_personnel(file_path):
    """從檔案讀取人員名單"""
    personnel = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            personnel.append({"name": row["name"], "is_new": row["is_new"] == "yes"})
    return personnel

def check_duplicate_members(first_queue, second_queue):
    """檢查兩個隊列是否有重複的成員"""
    first_set = set(first_queue)
    second_set = set(second_queue)
    duplicates = first_set.intersection(second_set)
    return duplicates

def get_interval_days(last_date, current_date):
    """計算間隔天數，如果沒有上次排班記錄，返回一個很大的數字"""
    if not last_date:
        return float('inf')  # 從未排班的人返回無限大
    return (current_date - last_date).days

def select_person(eligible_list, last_assigned_date, current_date):
    """選擇間隔最長的人員，如果有多個相同間隔的人則隨機選擇"""
    if not eligible_list:
        return None
    
    # 計算每個人的間隔時間
    intervals = [(person, get_interval_days(last_assigned_date[person], current_date)) 
                for person in eligible_list]
    
    # 找出最長間隔
    max_interval = max(intervals, key=lambda x: x[1])[1]
    
    # 找出所有具有最長間隔的人員
    candidates = [person for person, interval in intervals if interval == max_interval]
    
    # 從這些人中隨機選擇一個
    return random.choice(candidates)

def generate_schedule(personnel, start_date, weeks=26):
    """排班程式"""
    schedule = []
    first_priority_queue = deque()
    second_priority_queue = deque()
    new_comers = set()
    last_assigned_date = defaultdict(lambda: None)
    has_served_second = set()  # 追蹤已在 second priority 排班過的人
    intervals = defaultdict(list)
    MIN_INTERVAL = 30
    NEWCOMER_WAIT_WEEKS = 26

    # 初始化日期和週數
    current_date = start_date
    current_week = 0

    # 將所有人員放入臨��列表並記錄新人
    all_staff = []
    for person in personnel:
        all_staff.append(person["name"])
        if person["is_new"]:
            new_comers.add(person["name"])
    
    # 隨機打亂人員列表
    random.shuffle(all_staff)
    
    # 將打亂後的列表平均分配到兩個隊列
    mid_point = len(all_staff) // 2
    first_priority_queue.extend([p for p in all_staff[:mid_point] if p not in new_comers])
    second_priority_queue.extend(all_staff[mid_point:])
    
    # 印出初始隊列內容
    print("\n初始隊列分配:")
    print("First Priority Queue:", list(first_priority_queue))
    print("Second Priority Queue:", list(second_priority_queue))
    print("新進人員:", list(new_comers))
    print("\n")
    
    while len(schedule) < weeks:
        print(f"\n第 {current_week + 1} 週排班檢查:")
        
        # 檢查隊列是否有重複成員
        duplicates = check_duplicate_members(first_priority_queue, second_priority_queue)
        if duplicates:
            print("\n警告：發現重複成員！")
            print("重複出現的成員:", duplicates)
            raise ValueError("隊列中存在重複成員")
        
        print("\nFirst Priority Queue:", list(first_priority_queue))
        print("Second Priority Queue:", list(second_priority_queue))
        
        # 檢查 first_priority_queue 的每個人
        print("\nFirst Priority Queue 檢查:")
        eligible_first = []
        for p in first_priority_queue:
            interval = get_interval_days(last_assigned_date[p], current_date)
            if p in new_comers and p not in has_served_second:
                print(f"- {p}: 不符合資格 (尚未在 second priority 排班)")
            elif p in new_comers and current_week < NEWCOMER_WAIT_WEEKS:
                print(f"- {p}: 不符合資格 (新人尚未滿半年)")
            elif interval < MIN_INTERVAL:
                print(f"- {p}: 不符合資格 (間隔僅 {interval} 天)")
            else:
                print(f"- {p}: 符合資格 (間隔 {interval} 天)")
                eligible_first.append(p)
        
        # 檢查 second_priority_queue 的每個人
        print("\nSecond Priority Queue 檢查:")
        eligible_second = []
        for p in second_priority_queue:
            interval = get_interval_days(last_assigned_date[p], current_date)
            if p in new_comers and current_week < NEWCOMER_WAIT_WEEKS:
                print(f"- {p}: 不符合資格 (新人尚未滿半年)")
            elif interval < MIN_INTERVAL:
                print(f"- {p}: 不符合資格 (間隔僅 {interval} 天)")
            else:
                print(f"- {p}: 符合資格 (間隔 {interval} 天)")
                eligible_second.append(p)
        
        if not eligible_first or not eligible_second:
            print("\n合格人數統計:")
            print(f"First Priority Queue 合格人數: {len(eligible_first)}")
            print(f"Second Priority Queue 合格人數: {len(eligible_second)}")
            raise ValueError(f"沒有足夠的合格人員可以排班！需要至少 {MIN_INTERVAL} 天的間隔。")
        
        # 選擇間隔最長的人員
        first_priority = select_person(eligible_first, last_assigned_date, current_date)
        second_priority = select_person(eligible_second, last_assigned_date, current_date)
        
        # 記錄新人在 second priority 的排班經驗
        if second_priority in new_comers:
            has_served_second.add(second_priority)
        
        print(f"\n本週排班結果:")
        print(f"First Priority: {first_priority} (間隔: {get_interval_days(last_assigned_date[first_priority], current_date)} 天)")
        print(f"Second Priority: {second_priority} (間隔: {get_interval_days(last_assigned_date[second_priority], current_date)} 天)")

        schedule.append({
            "week": current_date.strftime("%Y-%m-%d"),
            "first_priority": first_priority,
            "second_priority": second_priority
        })

        # 計算並記錄間隔時間
        for person in [first_priority, second_priority]:
            if last_assigned_date[person]:
                interval = (current_date - last_assigned_date[person]).days
                intervals[person].append(interval)
            last_assigned_date[person] = current_date
        
        # 將選中的人員從原隊列中移除，然後加入另一個隊列
        first_priority_queue.remove(first_priority)
        second_priority_queue.remove(second_priority)
        
        # 新人只有在 second priority 排班後才能進入 first priority queue
        second_priority_queue.append(first_priority)
        if second_priority in new_comers and second_priority not in has_served_second:
            second_priority_queue.append(second_priority)
        else:
            first_priority_queue.append(second_priority)
        
        # 更新週數和日期
        current_week += 1
        current_date += datetime.timedelta(weeks=1)
        
        print("\n隊列更新後狀態:")
        print("First Priority Queue:", list(first_priority_queue))
        print("Second Priority Queue:", list(second_priority_queue))
        print("已在 Second Priority 服務過的新人:", list(has_served_second))
    
    return schedule, intervals

def get_resource_path(relative_path):
    """獲取資源文件的絕對路徑"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 創建臨時文件夾，將路徑存儲在 _MEIPASS 中
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 取得用戶輸入的資料
        weeks = int(request.form["weeks"])
        start_date = datetime.datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        
        # 使用 get_resource_path 獲取 personnel.csv 的正確路徑
        personnel_path = get_resource_path('personnel.csv')
        personnel = read_personnel(personnel_path)
        
        # 生成排班表
        schedule, intervals = generate_schedule(personnel, start_date, weeks)

        # 統計最長與最短間隔
        longest_interval = {"name": None, "interval": 0}
        shortest_interval = {"name": None, "interval": float("inf")}
        for person, person_intervals in intervals.items():
            if person_intervals:
                max_interval = max(person_intervals)
                min_interval = min(person_intervals)
                if max_interval > longest_interval["interval"]:
                    longest_interval = {"name": person, "interval": max_interval}
                if min_interval < shortest_interval["interval"]:
                    shortest_interval = {"name": person, "interval": min_interval}

        # 將排班結果與統計資料傳遞給結果頁面
        return render_template("result.html", schedule=schedule, longest=longest_interval, shortest=shortest_interval)
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

