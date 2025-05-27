from flask import render_template, request, jsonify, send_from_directory
import subprocess
import os
import json
import threading
from datetime import datetime
from app import app # Import the app instance
import sys

# 儲存分析狀態
analysis_status = {
    "running": False,
    "progress": 0,
    "message": "尚未開始",
    "last_run_time": None,
    "last_run_success": True,
    "error_message": "",
    "output_files": []
}

def get_latest_stats():
    # app.static_folder is an absolute path to app/static
    stats_file = os.path.join(app.static_folder, 'coverage_stats.json') 
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

@app.route('/')
def index():
    stats = get_latest_stats()
    # 確保所有預期的鍵都存在
    default_stats = {
        'avg_visible_satellites': 0,
        'coverage_percentage': 0,
        'avg_elevation': 0,
        'max_visible_satellites': 0,
        'analysis_duration_minutes': 0,
        'max_elevation': 0,
        'observer_location': {'lat': 25.03, 'lon': 121.57},
        'last_updated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 合併預設值和讀取到的值
    final_stats = {**default_stats, **stats}
    final_stats['observer_location_str'] = f"{final_stats['observer_location']['lat']:.2f}°N, {final_stats['observer_location']['lon']:.2f}°E"
    final_stats['last_updated_time'] = stats.get('last_updated_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    return render_template('index.html', stats=final_stats, analysis_status=analysis_status)

# This route might become redundant if Flask's static file handling is sufficient.
# However, if there was specific logic or if it serves a purpose for dynamically found files:
@app.route('/static_files/<path:filename>') # Renamed route for clarity, if kept
def serve_static_output_file(filename):
    # send_from_directory expects directory path relative to app.root_path or an absolute path.
    # app.static_folder is already an absolute path to the static directory.
    return send_from_directory(app.static_folder, filename)


def run_analysis_thread(duration):
    global analysis_status
    analysis_status["running"] = True
    analysis_status["progress"] = 0
    analysis_status["message"] = "分析準備中..."
    analysis_status["error_message"] = ""
    analysis_status["output_files"] = []

    try:
        # 使用新的 R 整合分析服務
        script_path = os.path.join(app.root_path, 'services', 'r_integration.py')

        # 使用當前 Python 解釋器
        executable = sys.executable 

        # 輸出目錄設定為 app.static_folder
        analysis_output_dir = app.static_folder

        process = subprocess.Popen(
            [executable, script_path, 
             '--duration', str(duration), 
             '--progress_output', 
             '--output', analysis_output_dir
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered
            universal_newlines=True,
            cwd=os.path.join(app.root_path, '..') # Run from project root
        )

        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line.startswith("PROGRESS:"):
                try:
                    progress_val = int(line.split(":")[1].strip())
                    analysis_status["progress"] = progress_val
                    analysis_status["message"] = f"分析中... {progress_val}%"
                except ValueError:
                    print(f"無法解析進度: {line}")
            elif line.startswith("MESSAGE:"):
                 analysis_status["message"] = line.split(":", 1)[1].strip()
            elif line.startswith("OUTPUT_FILE:"):
                analysis_status["output_files"].append(line.split(":", 1)[1].strip())
            else:
                print(f"分析腳本輸出: {line}") # 用於調試
        
        process.stdout.close()
        stderr_output = process.stderr.read()
        process.stderr.close()
        return_code = process.wait()

        if return_code == 0:
            analysis_status["message"] = "R 分析完成"
            analysis_status["progress"] = 100
            analysis_status["last_run_success"] = True
            if not analysis_status["output_files"]:
                 # R 分析的預設輸出檔案
                analysis_status["output_files"] = [
                    'coverage_stats.json',
                    'visible_satellites_timeline.png', 
                    'elevation_timeline.png',
                    'coverage_heatmap.html',
                    'report_r.html'  # 新增 R Markdown 報告
                ] 
        else:
            analysis_status["message"] = "R 分析失敗"
            analysis_status["last_run_success"] = False
            analysis_status["error_message"] = stderr_output or "未知錯誤"
            print(f"R 分析失敗，錯誤輸出: {stderr_output}")

    except Exception as e:
        analysis_status["message"] = "分析執行錯誤"
        analysis_status["last_run_success"] = False
        analysis_status["error_message"] = str(e)
        print(f"執行分析線程時發生錯誤: {e}")
    finally:
        analysis_status["running"] = False
        analysis_status["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    global analysis_status
    if analysis_status["running"]:
        return jsonify({"status": "error", "message": "分析已在進行中"}), 400

    duration = request.json.get('duration', 30) # 預設30分鐘
    try:
        duration = int(duration)
        if not (5 <= duration <= 240): # 限制分析時間範圍
             return jsonify({"status": "error", "message": "分析時間需介於5到240分鐘之間"}), 400
    except ValueError:
        return jsonify({"status": "error", "message": "無效的分析時間"}), 400

    thread = threading.Thread(target=run_analysis_thread, args=(duration,))
    thread.start()
    
    return jsonify({"status": "success", "message": "分析已啟動"})

@app.route('/analysis_status')
def get_analysis_status():
    global analysis_status
    if not analysis_status["running"] and analysis_status["last_run_success"] and analysis_status["progress"] == 100:
        stats = get_latest_stats()
        return jsonify({**analysis_status, "latest_stats": stats})
        
    return jsonify(analysis_status)

@app.route('/glossary')
def glossary():
    """專有名詞解釋頁面"""
    return render_template('glossary.html')

@app.route('/data-explanation')
def data_explanation():
    """數據說明頁面"""
    return render_template('data-explanation.html')

@app.route('/about')
def about():
    """關於頁面"""
    return render_template('about.html')

# The main execution block (if __name__ == '__main__':) should be in a top-level script,
# not in a blueprint/routes file. We'll create a new run.py or similar later. 