#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import pandas as pd
import sys
from datetime import datetime, timedelta
import logging

# 處理模組導入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

try:
    from app.services.analysis_service import StarlinkAnalysis
except ImportError:
    # 如果直接執行腳本，嘗試相對導入
    try:
        from analysis_service import StarlinkAnalysis
    except ImportError:
        # 最後嘗試絕對路徑導入
        analysis_service_path = os.path.join(current_dir, 'analysis_service.py')
        if os.path.exists(analysis_service_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("analysis_service", analysis_service_path)
            analysis_service = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(analysis_service)
            StarlinkAnalysis = analysis_service.StarlinkAnalysis
        else:
            raise ImportError("無法找到 analysis_service 模組")

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAnalysisIntegration:
    """
    R 分析整合服務
    
    此類別作為 Python Flask 應用程式和 R 分析腳本之間的橋梁，
    負責資料預處理、R 腳本調用和結果整合。
    """
    
    def __init__(self, output_dir="app/static", progress_output=False):
        """初始化 R 分析整合服務"""
        self.output_dir = output_dir
        self.progress_output = progress_output
        os.makedirs(output_dir, exist_ok=True)
        
        # 檢查 R 環境
        self._check_r_environment()
        
        # 創建 Python 分析實例用於衛星資料獲取
        self.python_analyzer = StarlinkAnalysis(output_dir=output_dir, progress_output=progress_output)
    
    def _check_r_environment(self):
        """檢查 R 環境和必要套件"""
        try:
            # 檢查 R 是否可用
            result = subprocess.run(['Rscript', '--version'], 
                                  capture_output=True, text=True, timeout=10, check=True)
            
            logger.info("✅ R 環境檢查通過")
            
            # 檢查必要的 R 套件
            self._check_r_packages()
            
        except subprocess.TimeoutExpired:
            logger.error("R 環境檢查超時")
            raise RuntimeError("R 環境檢查超時")
        except FileNotFoundError:
            logger.error("找不到 R 執行程式，請確認 R 已正確安裝")
            raise RuntimeError("找不到 R 執行程式，請確認 R 已正確安裝")
        except subprocess.CalledProcessError as e:
            logger.error(f"R 環境檢查失敗: {e}")
            raise RuntimeError(f"R 環境檢查失敗: {e.stderr}")
    
    def _check_r_packages(self):
        """檢查並自動安裝必要的 R 套件"""
        required_packages = [
            'tidyverse', 'lubridate', 'jsonlite', 'plotly', 
            'ggplot2', 'scales', 'DT', 'htmlwidgets', 'RColorBrewer',
            'rmarkdown'
        ]
        
        # 創建 R 腳本來檢查套件
        check_script = f"""
        required_packages <- c({', '.join([f'"{pkg}"' for pkg in required_packages])})
        missing_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]
        
        if(length(missing_packages) > 0) {{
            cat("MISSING_PACKAGES:", paste(missing_packages, collapse=","), "\\n")
            
            # 嘗試自動安裝缺失的套件
            cat("正在安裝缺失的套件...\\n")
            # 注意：在生產環境中，自動安裝套件可能不是最佳實踐
            # 最好確保環境在部署前已包含所有必要套件
            install.packages(missing_packages, repos="https://cran.r-project.org", dependencies=TRUE)
            
            # 再次檢查
            still_missing <- missing_packages[!(missing_packages %in% installed.packages()[,"Package"])]
            if(length(still_missing) > 0) {{
                cat("INSTALL_FAILED:", paste(still_missing, collapse=","), "\\n")
                quit(status=1) # 讓 Python 知道安裝失敗
            }}
        }}
        
        cat("PACKAGES_OK\\n")
        """
        
        try:
            # 增加 timeout 時間以應對可能的套件安裝過程
            result = subprocess.run(['Rscript', '-e', check_script], 
                                  capture_output=True, text=True, timeout=300, check=False)
            
            if result.returncode != 0:
                logger.error(f"R 套件檢查/安裝腳本執行失敗。\nstdout: {result.stdout}\nstderr: {result.stderr}")
                if "INSTALL_FAILED:" in result.stdout:
                    failed_packages = result.stdout.split("INSTALL_FAILED:")[1].split("\\n")[0].strip()
                    raise RuntimeError(f"無法安裝必要的 R 套件: {failed_packages}")
                raise RuntimeError("R 套件檢查或安裝過程中發生錯誤。")

            if "MISSING_PACKAGES:" in result.stdout:
                missing = result.stdout.split("MISSING_PACKAGES:")[1].split("\n")[0].strip()
                logger.warning(f"曾缺失 R 套件: {missing}，已嘗試自動安裝。請檢查 R 控制台確認安裝是否成功。")
                # 這裡不直接拋出錯誤，因為腳本會嘗試安裝
            
            if "PACKAGES_OK" in result.stdout:
                logger.info("✅ R 套件檢查通過 (或已嘗試安裝)")
            else:
                # 如果沒有 PACKAGES_OK 也沒有明確的 INSTALL_FAILED，可能還是有問題
                logger.warning("R 套件檢查腳本輸出未明確包含 PACKAGES_OK，請檢查 R 環境。")
                # 不在此處拋出錯誤，依賴後續 R 腳本執行時的錯誤捕獲
            
        except subprocess.TimeoutExpired:
            logger.error("R 套件檢查/安裝超時 (超過 5 分鐘)")
            raise RuntimeError("R 套件檢查/安裝超時")
    
    def _print_progress(self, percentage, message):
        """輸出進度資訊"""
        if self.progress_output:
            print(f"PROGRESS:{percentage}")
            print(f"MESSAGE:{message}")
            sys.stdout.flush()
    
    def _print_output_file(self, filename):
        """輸出檔案資訊"""
        if self.progress_output:
            print(f"OUTPUT_FILE:{filename}")
            sys.stdout.flush()
    
    def analyze_24h_coverage(self, interval_minutes=1, analysis_duration_minutes=60, 
                           min_elevation_threshold=25, use_r_analysis=True):
        """
        執行 24 小時覆蓋分析
        
        Args:
            interval_minutes: 分析間隔（分鐘）
            analysis_duration_minutes: 分析持續時間（分鐘）
            min_elevation_threshold: 最小仰角閾值
            use_r_analysis: 是否使用 R 進行統計分析和視覺化
        """
        try:
            self._print_progress(5, "開始衛星資料獲取...")
            
            # 使用 Python 服務獲取衛星資料
            coverage_df = self.python_analyzer.analyze_24h_coverage(
                interval_minutes=interval_minutes,
                analysis_duration_minutes=analysis_duration_minutes,
                min_elevation_threshold=min_elevation_threshold
            )
            
            if coverage_df is None or coverage_df.empty:
                raise RuntimeError("無法獲取衛星覆蓋資料")
            
            self._print_progress(30, "衛星資料獲取完成，準備 R 分析...")
            
            # 保存資料供 R 分析使用
            coverage_file = os.path.join(self.output_dir, "coverage_data.csv")
            coverage_df.to_csv(coverage_file, index=False, encoding='utf-8')
            
            if use_r_analysis:
                # 使用 R 進行統計分析和視覺化
                self._print_progress(40, "開始 R 統計分析...")
                r_result = self._run_r_analysis(coverage_file)
                
                if r_result['success']:
                    self._print_progress(80, "R 分析完成，整合結果...")
                    
                    # 整合 R 分析結果
                    stats = r_result.get('stats', {})
                    
                    # 添加觀測者位置資訊
                    stats['observer_location'] = {
                        'lat': self.python_analyzer.observer.latitude.degrees,
                        'lon': self.python_analyzer.observer.longitude.degrees
                    }
                    
                    # 保存整合後的統計結果
                    self._save_integrated_results(stats, coverage_df)
                    
                    self._print_progress(100, "分析完成")
                    return True
                else:
                    # R 分析失敗，使用 Python 備用分析
                    logger.warning("R 分析失敗，使用 Python 備用分析")
                    return self._fallback_python_analysis(coverage_df)
            else:
                # 直接使用 Python 分析
                return self._fallback_python_analysis(coverage_df)
                
        except Exception as e:
            logger.error(f"分析過程發生錯誤: {e}")
            self._print_progress(0, f"分析失敗: {str(e)}")
            return False
    
    def _run_r_analysis(self, coverage_file):
        """執行 R 分析腳本"""
        try:
            # R 分析腳本路徑
            r_script_path = os.path.join(
                os.path.dirname(__file__), 
                'analysis_service_r.R'
            )
            
            if not os.path.exists(r_script_path):
                raise RuntimeError(f"R 分析腳本不存在: {r_script_path}")
            
            # 執行 R 分析
            cmd = [
                'Rscript', 
                r_script_path, 
                coverage_file, 
                self.output_dir
            ]
            
            self._print_progress(50, "執行 R 分析腳本...")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 分鐘超時
                cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) # 設定工作目錄為專案根目錄
            )
            
            if result.returncode == 0:
                self._print_progress(70, "R 分析完成，讀取結果...")
                
                # 讀取 R 分析結果
                stats_file = os.path.join(self.output_dir, "coverage_stats.json")
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                    
                    return {
                        'success': True,
                        'stats': stats,
                        'message': 'R 分析完成'
                    }
                else:
                    logger.warning("R 分析完成但未找到統計結果檔案")
                    return {'success': False, 'message': '未找到統計結果檔案'}
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知錯誤"
                logger.error(f"R 分析失敗: {error_msg}")
                return {'success': False, 'message': f'R 分析失敗: {error_msg}'}
                
        except subprocess.TimeoutExpired:
            logger.error("R 分析超時")
            return {'success': False, 'message': 'R 分析超時'}
        except Exception as e:
            logger.error(f"執行 R 分析時發生錯誤: {e}")
            return {'success': False, 'message': f'R 分析錯誤: {str(e)}'}
    
    def _fallback_python_analysis(self, coverage_df):
        """Python 備用分析"""
        try:
            self._print_progress(60, "使用 Python 備用分析...")
            
            # 刪除可能存在的 R 報告，避免混淆
            r_report_path = os.path.join(self.output_dir, "report_r.html")
            if os.path.exists(r_report_path):
                try:
                    os.remove(r_report_path)
                    logger.info(f"已刪除舊的 R 報告: {r_report_path}")
                except OSError as e:
                    logger.warning(f"無法刪除 R 報告 {r_report_path}: {e}")
            
            # 使用原有的 Python 分析方法
            stats = self.python_analyzer._calculate_stats(coverage_df)
            
            # 添加觀測者位置資訊
            stats['observer_location'] = {
                'lat': self.python_analyzer.observer.latitude.degrees,
                'lon': self.python_analyzer.observer.longitude.degrees
            }
            
            # 保存結果
            self._save_integrated_results(stats, coverage_df)
            
            # 生成視覺化
            self._print_progress(80, "生成視覺化圖表...")
            self.python_analyzer.save_results(coverage_df, stats)
            self.python_analyzer.generate_visualizations()
            
            self._print_progress(100, "Python 分析完成")
            return True
            
        except Exception as e:
            logger.error(f"Python 備用分析失敗: {e}")
            return False
    
    def _save_integrated_results(self, stats, coverage_df):
        """保存整合後的分析結果"""
        try:
            # 刪除可能存在的 Python 舊報告，避免混淆
            python_report_path = os.path.join(self.output_dir, "report.html")
            if os.path.exists(python_report_path):
                try:
                    os.remove(python_report_path)
                    logger.info(f"已刪除舊的 Python 報告: {python_report_path}")
                except OSError as e:
                    logger.warning(f"無法刪除 Python 報告 {python_report_path}: {e}")
            
            # 保存統計結果
            stats_file = os.path.join(self.output_dir, "coverage_stats.json")
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            # 標記生成的檔案
            output_files = [
                "coverage_stats.json",
                "coverage_data.csv",
                "visible_satellites_timeline.png",
                "elevation_timeline.png", 
                "coverage_heatmap.html",
                "report_r.html"  # 新增 R Markdown 報告
            ]
            
            for filename in output_files:
                filepath = os.path.join(self.output_dir, filename)
                if os.path.exists(filepath):
                    self._print_output_file(filename)
            
            logger.info("✅ 分析結果已保存")
            
        except Exception as e:
            logger.error(f"保存結果時發生錯誤: {e}")


def main():
    """命令列介面"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Starlink Coverage Analysis with R Integration')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Analysis duration in minutes (default: 60)')
    parser.add_argument('--interval', type=int, default=1, 
                       help='Analysis interval in minutes (default: 1)')
    parser.add_argument('--elevation', type=float, default=25.0, 
                       help='Minimum elevation threshold in degrees (default: 25.0)')
    parser.add_argument('--output', type=str, default='app/static', 
                       help='Output directory (default: app/static)')
    parser.add_argument('--progress_output', action='store_true', 
                       help='Enable progress output for Flask integration')
    parser.add_argument('--use-python-only', action='store_true', 
                       help='Use Python analysis only (skip R)')
    
    args = parser.parse_args()
    
    try:
        # 創建 R 整合分析器
        analyzer = RAnalysisIntegration(
            output_dir=args.output, 
            progress_output=args.progress_output
        )
        
        # 執行分析
        success = analyzer.analyze_24h_coverage(
            interval_minutes=args.interval,
            analysis_duration_minutes=args.duration,
            min_elevation_threshold=args.elevation,
            use_r_analysis=not args.use_python_only
        )
        
        if success:
            print("🎉 分析完成！")
            sys.exit(0)
        else:
            print("❌ 分析失敗！")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 