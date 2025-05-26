#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🛰️ Starlink 台北衛星分析系統 - 主命令行工具
"""

import argparse
import sys
import os
import subprocess # Added for running Flask app
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='🛰️ Starlink 台北衛星分析系統',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  %(prog)s analyze --duration 30     # 執行30分鐘分析
  %(prog)s analyze --quick           # 快速10分鐘分析
  %(prog)s view                      # 查看結果 (現在由 web 指令處理)
  %(prog)s health                    # 健康檢查
  %(prog)s web                       # 啟動互動式網頁服務器
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用指令', required=True)
    
    # 分析指令
    analyze_parser = subparsers.add_parser('analyze', help='執行衛星覆蓋分析 (結果會自動更新到網頁)')
    analyze_parser.add_argument('--duration', type=int, default=30, 
                               help='分析時間長度（分鐘），預設30分鐘')
    analyze_parser.add_argument('--quick', action='store_true',
                               help='快速分析（10分鐘）')
    analyze_parser.add_argument('--interval', type=float, default=1.0,
                               help='時間間隔（分鐘），預設1.0分鐘')
    analyze_parser.add_argument('--min_elevation', type=float, default=25.0, 
                                help='最小衛星仰角閾值（度），預設25.0度')
    analyze_parser.add_argument('--cpu', type=int, default=None, help='用於並行處理的 CPU 核心數 (預設使用所有可用核心)')
    
    # 查看結果指令 (保留但提示使用 web)
    subparsers.add_parser('view', help='提示: 請使用 "web" 指令啟動網頁查看結果')
    
    # 健康檢查指令
    subparsers.add_parser('health', help='系統健康檢查')
    
    # 網頁服務器指令
    web_parser = subparsers.add_parser('web', help='啟動互動式網頁服務器')
    web_parser.add_argument('--port', type=int, default=8080,
                           help='網頁服務器端口，預設8080')
    web_parser.add_argument('--host', type=str, default='0.0.0.0',
                           help='網頁服務器監聽地址，預設0.0.0.0')
    
    # 更新指令 (現已整合到網頁後端)
    # subparsers.add_parser('update', help='更新主頁面數據 (現已自動化)')
    
    args = parser.parse_args()
        
    try:
        if args.command == 'analyze':
            duration = 10 if args.quick else args.duration
            print(f"🛰️  從命令行啟動 {duration} 分鐘分析...")
            print("   分析完成後，結果將自動顯示於網頁界面 (如果正在運行)。")
            cmd_parts = [
                sys.executable, os.path.join("app", "services", "analysis_service.py"), 
                "--duration", str(duration), 
                "--interval", str(args.interval),
                "--min_elevation", str(args.min_elevation)
            ]
            if args.cpu is not None:
                cmd_parts.extend(["--cpu", str(args.cpu)])
            
            process = subprocess.run(cmd_parts, capture_output=True, text=True, check=False)
            if process.returncode == 0:
                print("✅ 分析腳本執行完成。")
                print("標準輸出:")
                print(process.stdout)
            else:
                print("❌ 分析腳本執行失敗。")
                print("錯誤輸出:")
                print(process.stderr)
            
        elif args.command == 'view':
            print("ℹ️  提示: 若要查看結果，請使用 `python starlink.py web` 啟動網頁服務器並在瀏覽器中訪問。")
            
        elif args.command == 'health':
            print("🏥 執行系統健康檢查...")
            # Define potential paths for health_check.py
            script_dir = os.path.dirname(__file__) # Directory of starlink.py
            paths_to_check = [
                os.path.join(script_dir, "utils", "health_check.py"),
                os.path.join(script_dir, "app", "utils", "health_check.py"),
                os.path.join(script_dir, "scripts", "health_check.py"), # If you create a scripts/ dir for such utilities
                os.path.join(script_dir, "health_check.py") # If it's moved to the root alongside starlink.py
            ]
            
            health_check_script = None
            for path in paths_to_check:
                if os.path.exists(path):
                    health_check_script = path
                    break
            
            if health_check_script:
                subprocess.run([sys.executable, health_check_script], check=False)
            else:
                print(f"❌ 錯誤: 找不到健康檢查腳本。已嘗試的路徑: {paths_to_check}")
            
        elif args.command == 'web':
            print(f"🌐 啟動 Flask 網頁服務器於 http://{args.host}:{args.port}")
            print("   請在瀏覽器中打開上述網址。按 Ctrl+C 停止服務器。")
            try:
                run_script_path = os.path.join(os.path.dirname(__file__), "run.py")
                run_script_path = os.path.abspath(run_script_path)

                if not os.path.exists(run_script_path):
                    print(f"❌ 錯誤: 找不到 Flask 啟動腳本 run.py。預期路徑: {run_script_path}")
                    sys.exit(1)

                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                
                process = subprocess.Popen([sys.executable, run_script_path, "--host", args.host, "--port", str(args.port)], env=env)
                process.wait()
            except KeyboardInterrupt:
                print("\n⏹️  Flask 服務器已由用戶停止。")
            finally:
                if 'process' in locals() and process.poll() is None:
                    process.terminate()
                    process.wait()
            
        # elif args.command == 'update': # Update command is removed
        #     print("📊 更新主頁面數據... (此功能現由網頁後端自動處理)")
        #     # subprocess.run(["python", "utils/update_index.py"])
            
    except KeyboardInterrupt:
        print("\n\n⏹️  用戶中斷操作")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 