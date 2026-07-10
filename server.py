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
    "assignees": ["陳組長", "林幹事", "張助理"],
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
    "deliveryRoster": []
}

def load_db():
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
        return DEFAULT_DB
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_DB

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"寫入資料庫錯誤: {e}")
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
                "milestones": db.get("milestones", [])
            }
            response = json.dumps(config_data, ensure_ascii=False)
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

        else:
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()

if __name__ == '__main__':
    load_db()
    handler = GARequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"總務處系統後端伺服器已啟動： http://localhost:{PORT}")
        httpd.serve_forever()
