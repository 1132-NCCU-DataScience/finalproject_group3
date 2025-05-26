#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
開發環境啟動腳本
"""

import subprocess
import sys
import os
import time
import signal

def check_port(port):
    """檢查端口是否被佔用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def kill_existing_processes():
    """殺掉現有的 Flask 程序"""
    try:
        subprocess.run(['pkill', '-f', 'python.*run.py'], check=False)
        time.sleep(1)
    except:
        pass

def start_scss_watcher():
    """啟動 SCSS 監聽器（如果 sass 可用）"""
    try:
        # 檢查 sass 是否可用
        subprocess.run(['sass', '--version'], capture_output=True, check=True)
        
        # 啟動 SCSS 監聽器
        scss_cmd = [
            'sass', '--watch',
            'app/static/css/about-project.scss:app/static/css/about-project.css'
        ]
        
        print("🎨 啟動 SCSS 監聽器...")
        process = subprocess.Popen(scss_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  sass 未安裝，跳過 SCSS 監聽")
        return None

def main():
    print("🚀 Starlink 台北 - 開發環境啟動器")
    print("=" * 50)
    
    # 檢查並清理現有程序
    port = 8081
    if check_port(port):
        print(f"⚠️  端口 {port} 被佔用，正在清理...")
        kill_existing_processes()
        time.sleep(2)
    
    # 啟動 SCSS 監聽器
    scss_process = start_scss_watcher()
    
    # 啟動 Flask 應用
    print("🌐 啟動 Flask 應用...")
    flask_cmd = [sys.executable, 'run.py', '--port', str(port), '--debug']
    
    try:
        # 設定信號處理器
        def signal_handler(sig, frame):
            print("\n🛑 正在關閉服務...")
            if scss_process:
                scss_process.terminate()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # 啟動 Flask
        print(f"✅ 服務器啟動中... 請稍候")
        print(f"🌐 應用將在 http://localhost:{port} 運行")
        print("📝 按 Ctrl+C 停止服務")
        print("-" * 50)
        
        subprocess.run(flask_cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 服務已停止")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
    finally:
        if scss_process:
            scss_process.terminate()

if __name__ == "__main__":
    main() 