import http.server
import socketserver
import json
import os
import urllib.parse
import datetime
import time
import random

PORT = int(os.environ.get('PORT', 8000))
DB_FILE = 'db.json'

# 預設資料庫範本
DEFAULT_DB = {
    "assignees": ["陳組長", "林幹事", "張助理", "黃主任", "李志工"],
    "labels": [
        { "name": "修繕", "weight": 5 },
        { "name": "採購", "weight": 3 },
        { "name": "行政", "weight": 1 },
        { "name": "安全", "weight": 3 }
    ],
    "milestones": [
        "115學年度暑期校園修繕",
        "辦公設備汰舊換新",
        "退休同仁感恩餐會",
        "例行行政庶務"
    ],
    "tasks": [
        {
            "id": "task-1",
            "title": "活動中心舞台燈光電路修繕",
            "status": "In Progress",
            "assignee": "陳組長",
            "startDate": "2026-07-05",
            "dueDate": "2026-07-15",
            "label": "修繕",
            "weight": 5,
            "milestone": "115學年度暑期校園修繕"
        }
    ],
    "keyInventory": [
        { "id": "kf-1", "name": "五年十班教室鑰匙", "type": "鑰匙", "status": "Available" },
        { "id": "kf-2", "name": "行政大樓磁扣 #12", "type": "磁扣", "status": "Available" },
        { "id": "kf-3", "name": "體育器材室鑰匙", "type": "鑰匙", "status": "Available" }
    ],
    "keyLogs": [],
    "venueInventory": ["雅舍", "活動中心", "4樓會議室"],
    "venueReservations": [],
    "dutyRoster": [],
    "deliveryRoster": [],
    "classes": [f"{g}{r:02d}" for g in range(1, 7) for r in range(1, 11)],
    "offices": ["教務處", "學務處", "總務處", "輔導室", "人事室", "會計室", "校長室"],
    "periods": ["早修", "第一節", "第二節", "第三節", "第四節", "午休", "第五節", "第六節", "第七節"],
    "acTopups": [],
    "acCards": [{"classCode": f"{g}{r:02d}", "returned": False, "signature": "", "date": ""} for g in range(1, 7) for r in range(1, 11)],
    "meetings": [],
    "staffRoles": [
        { "name": "陳組長", "role": "組長", "password": "1234" },
        { "name": "林幹事", "role": "職工", "password": "1234" },
        { "name": "張助理", "role": "職工", "password": "1234" },
        { "name": "黃主任", "role": "主任", "password": "1234" },
        { "name": "李志工", "role": "志工", "password": "1234" }
    ],
    "halls": [
        "齊陽堂", "臨淮堂", "鍾陵堂", "蘭陵堂", "隴西堂", "譙國堂", "濟陽堂", "彭城堂",
        "陳留堂", "清河堂", "高陽堂", "高平堂", "苑陽堂", "范陽堂", "延陵堂", "始平堂",
        "京兆堂", "沛國堂", "宏農堂", "下邳堂", "上谷堂", "天水堂", "太原堂", "平原堂",
        "中山堂", "平陽堂", "安定堂", "汝南堂", "南陽堂", "江夏堂", "魯國堂", "樂安堂",
        "廣陵堂", "榮陽堂", "百濟堂", "西平堂", "西河堂", "吳興堂", "東海堂", "河東堂",
        "南昌堂", "上黨堂", "武功堂", "解梁堂", "廣平堂", "東魯堂", "河南堂", "河間堂",
        "敦煌堂", "渤海堂", "新鄭堂", "鉅鹿堂", "盧江堂", "穎川堂", "豫章堂", "齊郡堂",
        "榮安堂", "會稽堂", "馮翊堂", "雁門堂", "博陵堂", "晉陽堂"
    ],
    "subjectClassrooms": [
        { "name": "語言教室一", "hall": "齊陽堂" },
        { "name": "語言教室二", "hall": "臨淮堂" },
        { "name": "語言教室三", "hall": "鍾陵堂" },
        { "name": "視聽教室", "hall": "蘭陵堂" },
        { "name": "自然教室", "hall": "隴西堂" },
        { "name": "多元社團教室", "hall": "譙國堂" },
        { "name": "教具室", "hall": "濟陽堂" },
        { "name": "教師研習室", "hall": "彭城堂" },
        { "name": "圖書室", "hall": "陳留堂" },
        { "name": "平陵堂藝廊", "hall": "清河堂" },
        { "name": "武功堂科任辦公室", "hall": "高陽堂" },
        { "name": "解梁堂輔導諮商室", "hall": "高平堂" },
        { "name": "廣平堂輔導處", "hall": "苑陽堂" },
        { "name": "自然教室一", "hall": "范陽堂" },
        { "name": "音樂教室一", "hall": "延陵堂" },
        { "name": "音樂教室二", "hall": "始平堂" },
        { "name": "音樂教室三", "hall": "京兆堂" },
        { "name": "資訊教室一", "hall": "沛國堂" },
        { "name": "資訊教室二", "hall": "宏農堂" },
        { "name": "自然科教具室", "hall": "下邳堂" }
    ],
    "auditLogs": []
}

LAST_GOOD_DB = None

def load_db():
    global LAST_GOOD_DB
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
        LAST_GOOD_DB = DEFAULT_DB
        return DEFAULT_DB
        
    # 重試機制：針對併發讀寫鎖定進行最多 5 次讀取重試
    for i in range(5):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    LAST_GOOD_DB = data
                    return data
        except (json.JSONDecodeError, IOError, PermissionError):
            time.sleep(0.05)
            
    # 如果重試均失敗，且已有快取，傳回快取避免回退預設值
    if LAST_GOOD_DB is not None:
        print("警告：讀取資料庫失敗，傳回記憶體備份快取。")
        return LAST_GOOD_DB
        
    # 最壞情況下且無快取，嘗試直接讀取或回退到預設
    try:
        if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                LAST_GOOD_DB = data
                return data
    except Exception as e:
        print(f"讀取資料庫失敗且無記憶體快取: {e}")
    
    LAST_GOOD_DB = DEFAULT_DB
    return DEFAULT_DB

def save_db(data):
    global LAST_GOOD_DB
    tmp_file = DB_FILE + '.tmp'
    try:
        # 原子化寫入：先寫入臨時文件，再替換原始文件
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, DB_FILE)
        LAST_GOOD_DB = data
        return True
    except Exception as e:
        print(f"寫入資料庫錯誤: {e}")
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        return False

class GARequestHandler(http.server.BaseHTTPRequestHandler):

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # API 路由
        if path == '/api/tasks':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps(db.get("tasks", []), ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/config':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            config_data = {
                "assignees": db.get("assignees", []),
                "labels": db.get("labels", []),
                "milestones": db.get("milestones", []),
                "classes": db.get("classes", []),
                "offices": db.get("offices", []),
                "periods": db.get("periods", []),
                "staffRoles": db.get("staffRoles", []),
                "halls": db.get("halls", []),
                "subjectClassrooms": db.get("subjectClassrooms", [])
            }
            response = json.dumps(config_data, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/ac/topups':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps(db.get("acTopups", []), ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/ac/cards':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps(db.get("acCards", []), ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/meetings':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps(db.get("meetings", []), ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/audit-logs':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps(db.get("auditLogs", []), ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/etags':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps(db.get("etags", []), ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/keys':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            data = {
                "inventory": db.get("keyInventory", []),
                "logs": db.get("keyLogs", [])
            }
            response = json.dumps(data, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/venues':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            data = {
                "inventory": db.get("venueInventory", ["雅舍", "活動中心", "4樓會議室"]),
                "reservations": db.get("venueReservations", [])
            }
            response = json.dumps(data, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        elif path == '/api/roster':
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            data = {
                "duty": db.get("dutyRoster", []),
                "delivery": db.get("deliveryRoster", [])
            }
            response = json.dumps(data, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            return

        # 靜態網頁檔案路由
        else:
            file_path = 'index.html'
            if path != '/' and path != '/index.html':
                file_path = path.lstrip('/')
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                if file_path.endswith('.html'):
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                elif file_path.endswith('.css'):
                    self.send_header('Content-Type', 'text/css; charset=utf-8')
                elif file_path.endswith('.js'):
                    self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                elif file_path.endswith('.ico'):
                    self.send_header('Content-Type', 'image/x-icon')
                else:
                    self.send_header('Content-Type', 'application/octet-stream')
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write("找不到檔案。".encode('utf-8'))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            req_data = json.loads(body) if body else {}
        except Exception:
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write("JSON 格式錯誤".encode('utf-8'))
            return

        db = load_db()

        if path == '/api/tasks':
            if "title" not in req_data:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write("缺少任務名稱".encode('utf-8'))
                return
            
            req_data["id"] = f"task-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
            
            db.setdefault("tasks", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/etags':
            req_data["id"] = f"etag-{int(time.time()*1000)}-{random.randint(100, 999)}"
            db.setdefault("etags", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/tasks/bulk':
            if not isinstance(req_data, list):
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write("批次資料必須為陣列".encode('utf-8'))
                return

            db.setdefault("tasks", []).extend(req_data)
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "count": len(req_data)}, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/config':
            db["assignees"] = req_data.get("assignees", db.get("assignees", []))
            db["labels"] = req_data.get("labels", db.get("labels", []))
            db["milestones"] = req_data.get("milestones", db.get("milestones", []))
            db["classes"] = req_data.get("classes", db.get("classes", []))
            db["offices"] = req_data.get("offices", db.get("offices", []))
            db["periods"] = req_data.get("periods", db.get("periods", []))
            db["staffRoles"] = req_data.get("staffRoles", db.get("staffRoles", []))
            db["halls"] = req_data.get("halls", db.get("halls", []))
            db["subjectClassrooms"] = req_data.get("subjectClassrooms", db.get("subjectClassrooms", []))
            
            # 確保冷氣卡狀態與班級列表一致
            ac_cards = db.setdefault("acCards", [])
            existing_codes = {item["classCode"] for item in ac_cards}
            classes_set = set(db["classes"])
            ac_cards = [item for item in ac_cards if item["classCode"] in classes_set]
            for c in db["classes"]:
                if c not in existing_codes:
                    ac_cards.append({
                        "classCode": c,
                        "returned": False,
                        "signature": "",
                        "date": ""
                    })
            db["acCards"] = ac_cards
            
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/ac/topups':
            topup_id = f"act-{int(time.time()*1000)}-{random.randint(100, 999)}"
            req_data["id"] = topup_id
            if "date" not in req_data or not req_data["date"]:
                req_data["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
            
            db.setdefault("acTopups", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/ac/cards/sign':
            class_code = req_data.get("classCode")
            signature = req_data.get("signature", "")
            if not class_code:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                return
            
            ac_cards = db.setdefault("acCards", [])
            found = False
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            for item in ac_cards:
                if item.get("classCode") == class_code:
                    item["returned"] = True
                    item["signature"] = signature
                    item["date"] = now_str
                    found = True
                    req_data = item
                    break
            
            if not found:
                new_item = {
                    "classCode": class_code,
                    "returned": True,
                    "signature": signature,
                    "date": now_str
                }
                ac_cards.append(new_item)
                req_data = new_item
                
            db["acCards"] = ac_cards
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/ac/cards/reset':
            class_code = req_data.get("classCode")
            if not class_code:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                return
            
            ac_cards = db.setdefault("acCards", [])
            found = False
            for item in ac_cards:
                if item.get("classCode") == class_code:
                    item["returned"] = False
                    item["signature"] = ""
                    item["date"] = ""
                    found = True
                    req_data = item
                    break
            
            db["acCards"] = ac_cards
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/meetings':
            meet_id = f"meet-{int(time.time()*1000)}-{random.randint(100, 999)}"
            req_data["id"] = meet_id
            
            db.setdefault("meetings", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/audit-logs':
            log_id = f"alog-{int(time.time()*1000)}-{random.randint(100, 999)}"
            req_data["id"] = log_id
            if "timestamp" not in req_data or not req_data["timestamp"]:
                req_data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.setdefault("auditLogs", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/keys/inventory':
            inventory = db.setdefault("keyInventory", [])
            item_id = req_data.get("id")
            
            if item_id:
                for idx, item in enumerate(inventory):
                    if item.get("id") == item_id:
                        req_data["status"] = item.get("status", "Available")
                        inventory[idx] = req_data
                        break
            else:
                req_data["id"] = f"kf-{int(time.time()*1000)}-{random.randint(100, 999)}"
                req_data["status"] = "Available"
                inventory.append(req_data)
                
            db["keyInventory"] = inventory
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/keys/borrow':
            borrower = req_data.get("borrower")
            item_id = req_data.get("itemId")
            staff = req_data.get("staff")
            signature = req_data.get("signature", "")
            
            if not borrower or not item_id:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write("缺少必要欄位".encode('utf-8'))
                return
                
            inventory = db.setdefault("keyInventory", [])
            item_name = "未知鑰匙/磁扣"
            for item in inventory:
                if item.get("id") == item_id:
                    item["status"] = "Lent"
                    item_name = item.get("name")
                    break
                    
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            log_id = f"klog-{int(time.time()*1000)}-{random.randint(100, 999)}"
            
            new_log = {
                "id": log_id,
                "borrowDate": now_str,
                "returnDate": "",
                "borrower": borrower,
                "itemId": item_id,
                "itemName": item_name,
                "staff": staff,
                "signature": signature,
                "status": "Borrowed"
            }
            
            db.setdefault("keyLogs", []).append(new_log)
            db["keyInventory"] = inventory
            
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(new_log, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/keys/return':
            log_id = req_data.get("id")
            if not log_id:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                return
                
            logs = db.setdefault("keyLogs", [])
            inventory = db.setdefault("keyInventory", [])
            
            target_item_id = None
            found_log = None
            
            for log in logs:
                if log.get("id") == log_id and log.get("status") == "Borrowed":
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    log["returnDate"] = now_str
                    log["status"] = "Returned"
                    target_item_id = log.get("itemId")
                    found_log = log
                    break
                    
            if not found_log:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write("找不到該筆借出中紀錄".encode('utf-8'))
                return
                
            if target_item_id:
                for item in inventory:
                    if item.get("id") == target_item_id:
                        item["status"] = "Available"
                        break
                        
            db["keyLogs"] = logs
            db["keyInventory"] = inventory
            
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(found_log, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()

        elif path == '/api/venues/inventory':
            inventory = db.setdefault("venueInventory", ["雅舍", "活動中心", "4樓會議室"])
            name = req_data.get("name")
            if name and name not in inventory:
                inventory.append(name)
                db["venueInventory"] = inventory
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "name": name}, ensure_ascii=False).encode('utf-8'))
                    return
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/venues/reserve':
            res_id = f"vres-{int(time.time()*1000)}-{random.randint(100, 999)}"
            req_data["id"] = res_id
            
            db.setdefault("venueReservations", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/roster/duty':
            dr_id = f"dr-{int(time.time()*1000)}-{random.randint(100, 999)}"
            req_data["id"] = dr_id
            db.setdefault("dutyRoster", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/roster/delivery':
            del_id = f"del-{int(time.time()*1000)}-{random.randint(100, 999)}"
            req_data["id"] = del_id
            db.setdefault("deliveryRoster", []).append(req_data)
            if save_db(db):
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            req_data = json.loads(body) if body else {}
        except Exception:
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()
            return

        db = load_db()

        if path == '/api/tasks':
            task_id = req_data.get("id")
            if not task_id:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write("缺少任務 ID".encode('utf-8'))
                return

            tasks_list = db.get("tasks", [])
            for idx, task in enumerate(tasks_list):
                if task.get("id") == task_id:
                    tasks_list[idx] = req_data
                    db["tasks"] = tasks_list
                    if save_db(db):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                        return
                    else:
                        self.send_response(500)
                        self.send_cors_headers()
                        self.end_headers()
                        return
            
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write("找不到指定的任務 ID".encode('utf-8'))

        elif path == '/api/etags':
            etag_id = req_data.get("id")
            if not etag_id:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write("缺少 eTag ID".encode('utf-8'))
                return

            etags_list = db.get("etags", [])
            for idx, item in enumerate(etags_list):
                if item.get("id") == etag_id:
                    etags_list[idx] = req_data
                    db["etags"] = etags_list
                    if save_db(db):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(req_data, ensure_ascii=False).encode('utf-8'))
                        return
                    else:
                        self.send_response(500)
                        self.send_cors_headers()
                        self.end_headers()
                        return
            
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write("找不到指定的 eTag ID".encode('utf-8'))

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        task_id = query_params.get('id', [None])[0]

        db = load_db()

        if path == '/api/tasks' and task_id:
            tasks_list = db.get("tasks", [])
            new_tasks = [t for t in tasks_list if t.get("id") != task_id]
            if len(new_tasks) < len(tasks_list):
                db["tasks"] = new_tasks
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "deleted": task_id}, ensure_ascii=False).encode('utf-8'))
                    return
                else:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.end_headers()
                    return
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write("找不到指定的任務".encode('utf-8'))
            return

        elif path == '/api/etags' and task_id:
            etags_list = db.get("etags", [])
            new_etags = [e for e in etags_list if e.get("id") != task_id]
            if len(new_etags) < len(etags_list):
                db["etags"] = new_etags
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "deleted": task_id}, ensure_ascii=False).encode('utf-8'))
                    return
                else:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.end_headers()
                    return
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write("找不到指定的 eTag 登記資料".encode('utf-8'))
            return

        elif path == '/api/ac/topups' and task_id:
            topups = db.get("acTopups", [])
            new_topups = [t for t in topups if t.get("id") != task_id]
            if len(new_topups) < len(topups):
                db["acTopups"] = new_topups
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "deleted": task_id}, ensure_ascii=False).encode('utf-8'))
                    return
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/meetings' and task_id:
            meetings = db.get("meetings", [])
            new_meetings = [m for m in meetings if m.get("id") != task_id]
            if len(new_meetings) < len(meetings):
                db["meetings"] = new_meetings
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "deleted": task_id}, ensure_ascii=False).encode('utf-8'))
                    return
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/keys/logs' and task_id:
            logs = db.get("keyLogs", [])
            inventory = db.get("keyInventory", [])
            
            found_log = None
            for log in logs:
                if log.get("id") == task_id:
                    found_log = log
                    break
                    
            if found_log:
                if found_log.get("status") == "Borrowed":
                    target_item_id = found_log.get("itemId")
                    if target_item_id:
                        for item in inventory:
                            if item.get("id") == target_item_id:
                                item["status"] = "Available"
                                break
                                
                new_logs = [log for log in logs if log.get("id") != task_id]
                db["keyLogs"] = new_logs
                db["keyInventory"] = inventory
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "deleted": task_id}, ensure_ascii=False).encode('utf-8'))
                    return
                else:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.end_headers()
                    return
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/keys/inventory' and task_id:
            inventory = db.get("keyInventory", [])
            new_inventory = [item for item in inventory if item.get("id") != task_id]
            
            if len(new_inventory) < len(inventory):
                db["keyInventory"] = new_inventory
                if save_db(db):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "deleted": task_id}, ensure_ascii=False).encode('utf-8'))
                    return
                else:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.end_headers()
                    return
            
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/venues/inventory':
            name_param = query_params.get('name', [None])[0]
            if name_param:
                inventory = db.setdefault("venueInventory", ["雅舍", "活動中心", "4樓會議室"])
                if name_param in inventory:
                    inventory.remove(name_param)
                    db["venueInventory"] = inventory
                    if save_db(db):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "deleted": name_param}, ensure_ascii=False).encode('utf-8'))
                        return
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/venues/reserve':
            id_param = query_params.get('id', [None])[0]
            if id_param:
                reservations = db.setdefault("venueReservations", [])
                new_res = [r for r in reservations if r.get("id") != id_param]
                if len(new_res) < len(reservations):
                    db["venueReservations"] = new_res
                    if save_db(db):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "deleted": id_param}, ensure_ascii=False).encode('utf-8'))
                        return
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/roster/duty':
            id_param = query_params.get('id', [None])[0]
            if id_param:
                roster = db.setdefault("dutyRoster", [])
                new_roster = [r for r in roster if r.get("id") != id_param]
                if len(new_roster) < len(roster):
                    db["dutyRoster"] = new_roster
                    if save_db(db):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "deleted": id_param}, ensure_ascii=False).encode('utf-8'))
                        return
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/roster/delivery':
            id_param = query_params.get('id', [None])[0]
            if id_param:
                roster = db.setdefault("deliveryRoster", [])
                new_roster = [r for r in roster if r.get("id") != id_param]
                if len(new_roster) < len(roster):
                    db["deliveryRoster"] = new_roster
                    if save_db(db):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "deleted": id_param}, ensure_ascii=False).encode('utf-8'))
                        return
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

        elif path == '/api/audit-logs':
            db["auditLogs"] = []
            if save_db(db):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "已清空所有日誌"}, ensure_ascii=False).encode('utf-8'))
                return
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()

        else:
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

if __name__ == '__main__':
    load_db()
    handler = GARequestHandler
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    with socketserver.TCPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"總務處系統後端伺服器已啟動")
        print(f"  本機存取：http://localhost:{PORT}")
        print(f"  區域網路（手機/平板用）：http://{local_ip}:{PORT}")
        print(f"  請確認 Windows 防火牆已開放 {PORT} 埠")
        httpd.serve_forever()
