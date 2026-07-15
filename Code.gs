// ==========================================
// 樹義總務處全能管理系統 - Google Apps Script 後台
// 版本：2.0
// 說明：透過 Google Sheets 作為雲端資料庫，
//       提供前端 HTML 系統的資料讀寫 API。
//
// 部署方式：
//   1. 開啟 Google Apps Script (script.google.com)
//   2. 建立新專案，貼上此程式碼
//   3. 點選「部署」→「新增部署」→「網頁應用程式」
//   4. 執行身分：「我」；存取權：「所有人」
//   5. 複製部署 URL，貼入前端設定頁面的「雲端試算表 API URL」
//
// 支援的工作表名稱（type 參數）：
//   tasks, keyInventory, keyLogs, venueReservations,
//   venueInventory, dutyRoster, deliveryRoster,
//   acTopups, acCards, meetings, etags,
//   assignees, labels, milestones, staffRoles,
//   halls, subjectClassrooms, auditLogs,
//   classes, offices, periods
// ==========================================


// ==========================================
// 常數設定
// ==========================================

// 允許的 type 白名單（防止操作到無關工作表）
var ALLOWED_TYPES = [
  'tasks',
  'keyInventory',
  'keyLogs',
  'venueReservations',
  'venueInventory',
  'dutyRoster',
  'deliveryRoster',
  'acTopups',
  'acCards',
  'meetings',
  'etags',
  'assignees',
  'labels',
  'milestones',
  'staffRoles',
  'halls',
  'subjectClassrooms',
  'auditLogs',
  'classes',
  'offices',
  'periods'
];


// ==========================================
// doGet：讀取指定工作表資料，回傳 JSON 陣列
// ==========================================
// 呼叫範例：
//   GET https://script.google.com/.../exec?type=tasks
//   GET https://script.google.com/.../exec?type=keyInventory
// ==========================================
function doGet(e) {
  var type = (e && e.parameter && e.parameter.type) ? e.parameter.type.trim() : '';

  if (!type) {
    return makeJsonResponse({ error: 'Missing type parameter', status: 400 });
  }

  if (ALLOWED_TYPES.indexOf(type) === -1) {
    return makeJsonResponse({ error: 'Invalid type: ' + type, status: 403 });
  }

  try {
    var ss    = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(type);

    // 工作表不存在，傳回空陣列（讓前端自行處理初始化）
    if (!sheet) {
      return makeJsonResponse([]);
    }

    var lastRow    = sheet.getLastRow();
    var lastColumn = sheet.getLastColumn();

    if (lastRow < 2 || lastColumn < 1) {
      return makeJsonResponse([]);
    }

    var headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];
    var data    = sheet.getRange(2, 1, lastRow - 1, lastColumn).getValues();

    var result = [];
    for (var i = 0; i < data.length; i++) {
      var obj      = {};
      var hasValue = false;

      for (var j = 0; j < headers.length; j++) {
        var key = headers[j];
        if (!key) continue;

        var val = data[i][j];

        if (val instanceof Date) {
          obj[key] = formatDate(val);
        } else if (typeof val === 'string' && isJsonString(val)) {
          // 還原存入時被 JSON.stringify 的物件/陣列欄位
          try {
            obj[key] = JSON.parse(val);
          } catch (_) {
            obj[key] = val;
          }
        } else {
          obj[key] = val;
        }

        if (val !== '' && val !== null && val !== undefined) {
          hasValue = true;
        }
      }

      // 忽略完全空白的列
      if (hasValue) {
        result.push(obj);
      }
    }

    return makeJsonResponse(result);

  } catch (err) {
    return makeJsonResponse({ error: err.toString(), status: 500 });
  }
}


// ==========================================
// doPost：寫入指定工作表資料
// ==========================================
// action 欄位控制操作模式：
//
//   "replace"（預設）── 整表覆蓋
//   Body：{ "type": "tasks", "list": [ {...}, {...} ] }
//
//   "append" ── 新增單筆
//   Body：{ "type": "tasks", "action": "append", "item": {...} }
//
//   "delete" ── 依 id 刪除
//   Body：{ "type": "tasks", "action": "delete", "id": "task-1" }
//
//   "update" ── 依 id 更新整列
//   Body：{ "type": "tasks", "action": "update", "id": "task-1", "item": {...} }
// ==========================================
function doPost(e) {
  var responseData = { success: false };

  try {
    if (!e || !e.postData || !e.postData.contents) {
      responseData.error = 'Empty request body';
      return makeJsonResponse(responseData);
    }

    var postData = JSON.parse(e.postData.contents);
    var type     = postData.type;
    var action   = postData.action || 'replace';

    if (!type) {
      responseData.error = 'Missing type';
      return makeJsonResponse(responseData);
    }

    if (ALLOWED_TYPES.indexOf(type) === -1) {
      responseData.error = 'Invalid type: ' + type;
      return makeJsonResponse(responseData);
    }

    var ss    = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(type);

    // ── 整表覆蓋（replace）─────────────────────────────────────
    if (action === 'replace') {
      var list = postData.list;
      if (!Array.isArray(list)) {
        responseData.error = 'list must be an array';
        return makeJsonResponse(responseData);
      }

      if (!sheet) {
        sheet = ss.insertSheet(type);
      } else {
        sheet.clear();
      }

      if (list.length === 0) {
        sheet.appendRow(['id']);
        responseData.success = true;
        responseData.written = 0;
        return makeJsonResponse(responseData);
      }

      // 收集所有 key，id 優先排首
      var headerSet = {};
      list.forEach(function(item) {
        if (item && typeof item === 'object' && !Array.isArray(item)) {
          Object.keys(item).forEach(function(k) { headerSet[k] = true; });
        }
      });

      var headers  = Object.keys(headerSet);
      var idIndex  = headers.indexOf('id');
      if (idIndex > 0) { headers.splice(idIndex, 1); headers.unshift('id'); }

      sheet.appendRow(headers);

      var rows = list.map(function(item) {
        return headers.map(function(key) {
          var val = item[key];
          if (val === undefined || val === null) return '';
          if (typeof val === 'object') return JSON.stringify(val);
          return val;
        });
      });

      if (rows.length > 0) {
        sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      }

      responseData.success = true;
      responseData.written  = rows.length;
      return makeJsonResponse(responseData);
    }

    // ── 新增單列（append）─────────────────────────────────────
    if (action === 'append') {
      var item = postData.item;
      if (!item || typeof item !== 'object') {
        responseData.error = 'item is required for append action';
        return makeJsonResponse(responseData);
      }

      if (!sheet) {
        sheet = ss.insertSheet(type);
        var newHeaders = Object.keys(item);
        var idIdx = newHeaders.indexOf('id');
        if (idIdx > 0) { newHeaders.splice(idIdx, 1); newHeaders.unshift('id'); }
        sheet.appendRow(newHeaders);
      }

      var existHeaders = getSheetHeaders(sheet);

      // 補充工作表中不存在的新欄位
      Object.keys(item).forEach(function(k) {
        if (existHeaders.indexOf(k) === -1) {
          existHeaders.push(k);
          sheet.getRange(1, existHeaders.length).setValue(k);
        }
      });

      var row = existHeaders.map(function(key) {
        var val = item[key];
        if (val === undefined || val === null) return '';
        if (typeof val === 'object') return JSON.stringify(val);
        return val;
      });

      sheet.appendRow(row);
      responseData.success = true;
      return makeJsonResponse(responseData);
    }

    // ── 依 id 刪除（delete）───────────────────────────────────
    if (action === 'delete') {
      var targetId = postData.id;
      if (!targetId) {
        responseData.error = 'id is required for delete action';
        return makeJsonResponse(responseData);
      }
      if (!sheet) {
        responseData.error = 'Sheet not found: ' + type;
        return makeJsonResponse(responseData);
      }

      var rowIndex = findRowIndexById(sheet, targetId);
      if (rowIndex === -1) {
        responseData.error = 'Row not found for id: ' + targetId;
        return makeJsonResponse(responseData);
      }

      sheet.deleteRow(rowIndex);
      responseData.success = true;
      return makeJsonResponse(responseData);
    }

    // ── 依 id 更新（update）───────────────────────────────────
    if (action === 'update') {
      var updateId   = postData.id;
      var updateItem = postData.item;
      if (!updateId || !updateItem) {
        responseData.error = 'id and item are required for update action';
        return makeJsonResponse(responseData);
      }
      if (!sheet) {
        responseData.error = 'Sheet not found: ' + type;
        return makeJsonResponse(responseData);
      }

      var headers = getSheetHeaders(sheet);
      var rowIdx  = findRowIndexById(sheet, updateId);
      if (rowIdx === -1) {
        responseData.error = 'Row not found for id: ' + updateId;
        return makeJsonResponse(responseData);
      }

      var updatedRow = headers.map(function(key) {
        var val = updateItem[key];
        if (val === undefined || val === null) return '';
        if (typeof val === 'object') return JSON.stringify(val);
        return val;
      });

      sheet.getRange(rowIdx, 1, 1, headers.length).setValues([updatedRow]);
      responseData.success = true;
      return makeJsonResponse(responseData);
    }

    responseData.error = 'Unknown action: ' + action;
    return makeJsonResponse(responseData);

  } catch (err) {
    responseData.error = err.toString();
    return makeJsonResponse(responseData);
  }
}


// ==========================================
// 輔助函式
// ==========================================

/**
 * 統一產生 JSON 回應
 */
function makeJsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 格式化日期
 * 時分秒全為 0 → YYYY-MM-DD
 * 否則 → YYYY-MM-DD HH:mm
 */
function formatDate(date) {
  var y   = date.getFullYear();
  var m   = pad(date.getMonth() + 1);
  var d   = pad(date.getDate());
  var h   = pad(date.getHours());
  var min = pad(date.getMinutes());
  var s   = pad(date.getSeconds());

  if (h === '00' && min === '00' && s === '00') {
    return y + '-' + m + '-' + d;
  }
  return y + '-' + m + '-' + d + ' ' + h + ':' + min;
}

/** 數字補零 */
function pad(n) {
  return ('0' + n).slice(-2);
}

/**
 * 判斷字串是否為 JSON 物件或陣列（用於讀取時自動反序列化）
 */
function isJsonString(str) {
  if (typeof str !== 'string') return false;
  var s = str.trim();
  return (s.charAt(0) === '{' && s.charAt(s.length - 1) === '}') ||
         (s.charAt(0) === '[' && s.charAt(s.length - 1) === ']');
}

/**
 * 取得工作表標題列（過濾空欄位）
 */
function getSheetHeaders(sheet) {
  var lastCol = sheet.getLastColumn();
  if (lastCol < 1) return [];
  return sheet.getRange(1, 1, 1, lastCol).getValues()[0].filter(function(h) {
    return h !== '' && h !== null && h !== undefined;
  });
}

/**
 * 在工作表中依 id 欄位找到該列的列號（1-indexed）
 * 找不到回傳 -1
 */
function findRowIndexById(sheet, targetId) {
  var headers = getSheetHeaders(sheet);
  var idCol   = headers.indexOf('id') + 1; // 轉換為 1-indexed
  if (idCol === 0) return -1;

  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return -1;

  var idValues = sheet.getRange(2, idCol, lastRow - 1, 1).getValues();
  for (var i = 0; i < idValues.length; i++) {
    if (String(idValues[i][0]) === String(targetId)) {
      return i + 2; // +2：跳過標題列（列號從 1 開始，資料從第 2 列開始）
    }
  }
  return -1;
}


// ==========================================
// 初始化工具（在 Apps Script 編輯器中手動執行一次）
// ==========================================
/**
 * 自動建立所有需要的工作表，並設定標題列格式。
 * 已存在的工作表不會被清除或覆蓋。
 */
function initializeAllSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var sheetConfigs = {
    'tasks'             : ['id', 'title', 'status', 'assignee', 'startDate', 'dueDate', 'label', 'weight', 'milestone'],
    'keyInventory'      : ['id', 'name', 'type', 'status'],
    'keyLogs'           : ['id', 'keyId', 'keyName', 'type', 'borrower', 'borrowerRole', 'contact', 'borrowDate', 'expectedReturn', 'returnDate', 'purpose', 'status'],
    'venueReservations' : ['id', 'venue', 'date', 'startTime', 'endTime', 'organizer', 'purpose', 'attendees', 'status', 'approver', 'note'],
    'venueInventory'    : ['name'],
    'dutyRoster'        : ['id', 'date', 'period', 'assignee', 'type', 'note'],
    'deliveryRoster'    : ['id', 'date', 'assignee', 'from', 'to', 'purpose', 'note'],
    'acTopups'          : ['id', 'date', 'amount', 'operator', 'note'],
    'acCards'           : ['classCode', 'returned', 'signature', 'date'],
    'meetings'          : ['id', 'title', 'date', 'startTime', 'endTime', 'location', 'organizer', 'attendees', 'agenda', 'minutes', 'status'],
    'etags'             : ['id', 'name', 'classCode', 'hall', 'type', 'date', 'note'],
    'assignees'         : ['name'],
    'labels'            : ['name', 'weight'],
    'milestones'        : ['name'],
    'staffRoles'        : ['name', 'role', 'password'],
    'halls'             : ['name'],
    'subjectClassrooms' : ['name', 'hall'],
    'auditLogs'         : ['id', 'timestamp', 'operator', 'action', 'target', 'detail'],
    'classes'           : ['classCode'],
    'offices'           : ['name'],
    'periods'           : ['name']
  };

  var created = [];
  var existed = [];

  Object.keys(sheetConfigs).forEach(function(name) {
    var sheet = ss.getSheetByName(name);
    if (!sheet) {
      sheet = ss.insertSheet(name);
      sheet.appendRow(sheetConfigs[name]);
      // 凍結標題列
      sheet.setFrozenRows(1);
      // 格式化標題列（粉紅色主題）
      var headerRange = sheet.getRange(1, 1, 1, sheetConfigs[name].length);
      headerRange.setBackground('#d84f8b');
      headerRange.setFontColor('#ffffff');
      headerRange.setFontWeight('bold');
      created.push(name);
    } else {
      existed.push(name);
    }
  });

  var msg = '✅ 初始化完成！\n\n';
  if (created.length > 0) msg += '📋 新建工作表（' + created.length + ' 個）：\n' + created.join(', ') + '\n\n';
  if (existed.length > 0) msg += '⚠️ 已存在略過（' + existed.length + ' 個）：\n' + existed.join(', ');

  SpreadsheetApp.getUi().alert(msg);
}


// ==========================================
// 測試函式（在 Apps Script 編輯器中執行）
// ==========================================

/** 測試 GET：讀取 tasks */
function testDoGet() {
  var result = doGet({ parameter: { type: 'tasks' } });
  Logger.log('=== doGet tasks ===');
  Logger.log(result.getContent());
}

/** 測試 POST replace：整表覆蓋寫入 tasks */
function testDoPost_Replace() {
  var result = doPost({
    postData: {
      contents: JSON.stringify({
        type: 'tasks',
        action: 'replace',
        list: [
          {
            id: 'task-test-1',
            title: '測試任務（覆蓋）',
            status: 'To Do',
            assignee: '陳組長',
            startDate: '2026-07-15',
            dueDate: '2026-07-31',
            label: '行政',
            weight: 1,
            milestone: '例行行政庶務'
          }
        ]
      })
    }
  });
  Logger.log('=== doPost replace ===');
  Logger.log(result.getContent());
}

/** 測試 POST append：新增單筆任務 */
function testDoPost_Append() {
  var result = doPost({
    postData: {
      contents: JSON.stringify({
        type: 'tasks',
        action: 'append',
        item: {
          id: 'task-append-' + new Date().getTime(),
          title: '新增測試任務（append）',
          status: 'In Progress',
          assignee: '林幹事',
          startDate: '2026-07-16',
          dueDate: '2026-08-01',
          label: '修繕',
          weight: 3,
          milestone: '115學年度暑期校園修繕'
        }
      })
    }
  });
  Logger.log('=== doPost append ===');
  Logger.log(result.getContent());
}

/** 測試 POST delete：依 id 刪除 */
function testDoPost_Delete() {
  var result = doPost({
    postData: {
      contents: JSON.stringify({
        type: 'tasks',
        action: 'delete',
        id: 'task-test-1'
      })
    }
  });
  Logger.log('=== doPost delete ===');
  Logger.log(result.getContent());
}

/** 測試 POST update：依 id 更新 */
function testDoPost_Update() {
  var result = doPost({
    postData: {
      contents: JSON.stringify({
        type: 'tasks',
        action: 'update',
        id: 'task-test-1',
        item: {
          id: 'task-test-1',
          title: '已更新的測試任務',
          status: 'Done',
          assignee: '陳組長',
          startDate: '2026-07-15',
          dueDate: '2026-07-31',
          label: '行政',
          weight: 1,
          milestone: '例行行政庶務'
        }
      })
    }
  });
  Logger.log('=== doPost update ===');
  Logger.log(result.getContent());
}
