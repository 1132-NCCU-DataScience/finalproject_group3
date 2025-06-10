#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
R 整合服務模組
提供 Python 和 R 之間的橋接功能
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RIntegrationService:
    """R 整合服務類別"""
    
    def __init__(self, r_script_dir: str = "R"):
        """
        初始化 R 整合服務
        
        Args:
            r_script_dir: R 腳本目錄路徑
        """
        self.r_script_dir = Path(r_script_dir)
        self.base_dir = Path(__file__).parent.parent.parent
        self.r_executable = self._find_r_executable()
        
    def _find_r_executable(self) -> Optional[str]:
        """找到 R 可執行檔案路徑"""
        possible_paths = [
            "/home/lean/miniconda3/bin/R",
            "/usr/bin/R",
            "/usr/local/bin/R"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # 使用 which 命令
        try:
            result = subprocess.run(['which', 'R'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
            
        return None
    
    def check_r_environment(self) -> Dict[str, Any]:
        """檢查 R 環境狀態"""
        status = {
            "r_available": False,
            "r_path": None,
            "required_packages": [],
            "missing_packages": [],
            "status": "unknown"
        }
        
        if not self.r_executable:
            status["status"] = "R executable not found"
            return status
            
        status["r_available"] = True
        status["r_path"] = self.r_executable
        
        # 檢查必要套件
        required_packages = [
            "shiny", "shinydashboard", "plotly", "DT", 
            "ggplot2", "dplyr", "jsonlite", "reticulate"
        ]
        
        try:
            r_command = f"""
            required_packages <- c({', '.join([f'"{pkg}"' for pkg in required_packages])})
            installed_packages <- installed.packages()[,"Package"]
            missing <- required_packages[!required_packages %in% installed_packages]
            cat(paste(missing, collapse=","))
            """
            
            result = subprocess.run(
                [self.r_executable, '--slave', '-e', r_command],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                missing = result.stdout.strip()
                if missing:
                    status["missing_packages"] = missing.split(",")
                    status["status"] = f"Missing packages: {missing}"
                else:
                    status["status"] = "All packages available"
                status["required_packages"] = required_packages
            else:
                status["status"] = f"Error checking packages: {result.stderr}"
                
        except Exception as e:
            status["status"] = f"Error: {str(e)}"
            
        return status
    
    def run_analysis(self, 
                    lat: float = 25.0330, 
                    lon: float = 121.5654,
                    duration: int = 60,
                    interval: float = 1.0,
                    min_elevation: float = 25.0) -> Dict[str, Any]:
        """
        運行 R 分析
        
        Args:
            lat: 緯度
            lon: 經度
            duration: 分析持續時間（分鐘）
            interval: 時間間隔（分鐘）
            min_elevation: 最小仰角閾值
            
        Returns:
            分析結果字典
        """
        if not self.r_executable:
            return {
                "success": False,
                "error": "R executable not found",
                "data": None
            }
        
        try:
            # 準備 R 命令
            r_command = f"""
            source("{self.base_dir}/R/analysis.R")
            result <- run_analysis(
                lat = {lat},
                lon = {lon},
                interval_minutes = {interval},
                analysis_duration_minutes = {duration},
                min_elevation_threshold = {min_elevation}
            )
            cat(jsonlite::toJSON(result, auto_unbox = TRUE))
            """
            
            # 運行 R 命令
            process = subprocess.run(
                [self.r_executable, '--slave', '-e', r_command],
                capture_output=True, text=True, timeout=300,  # 5 分鐘超時
                cwd=str(self.base_dir)
            )
            
            if process.returncode == 0:
                try:
                    result_data = json.loads(process.stdout)
                    return {
                        "success": True,
                        "error": None,
                        "data": result_data
                    }
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"JSON decode error: {str(e)}",
                        "raw_output": process.stdout,
                        "data": None
                    }
            else:
                return {
                    "success": False,
                    "error": f"R execution failed: {process.stderr}",
                    "returncode": process.returncode,
                    "data": None
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "R analysis timed out (>5 minutes)",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "data": None
            }
    
    def run_shiny_app(self, port: int = 3838, host: str = "0.0.0.0") -> subprocess.Popen:
        """
        啟動 Shiny 應用
        
        Args:
            port: 端口號
            host: 主機地址
            
        Returns:
            Popen 程序對象
        """
        if not self.r_executable:
            raise RuntimeError("R executable not found")
        
        # 設置環境變數
        env = os.environ.copy()
        env["R_SHINY_PORT"] = str(port)
        env["R_SHINY_HOST"] = host
        
        # R 命令
        r_command = f"""
        library(shiny)
        runApp(appDir=".", port={port}, host="{host}", launch.browser=FALSE)
        """
        
        # 啟動 Shiny 應用
        process = subprocess.Popen(
            [self.r_executable, '--slave', '-e', r_command],
            env=env,
            cwd=str(self.base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        return process
    
    def load_analysis_results(self, output_dir: str = "output") -> Dict[str, Any]:
        """
        載入分析結果
        
        Args:
            output_dir: 輸出目錄
            
        Returns:
            分析結果字典
        """
        output_path = self.base_dir / output_dir
        
        results = {
            "stats": None,
            "data": None,
            "files": {
                "stats_file": None,
                "data_file": None,
                "report_file": None
            }
        }
        
        # 載入統計數據
        stats_file = output_path / "coverage_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    results["stats"] = json.load(f)
                results["files"]["stats_file"] = str(stats_file)
            except Exception as e:
                logger.error(f"Error loading stats: {e}")
        
        # 檢查其他檔案
        data_file = output_path / "coverage_data.csv"
        if data_file.exists():
            results["files"]["data_file"] = str(data_file)
            
        report_file = output_path / "coverage_report.html"
        if report_file.exists():
            results["files"]["report_file"] = str(report_file)
            
        return results

# 全域實例
r_service = RIntegrationService()

def get_r_service() -> RIntegrationService:
    """獲取 R 整合服務實例"""
    return r_service

if __name__ == "__main__":
    # 測試
    service = RIntegrationService()
    
    print("=== R 環境檢查 ===")
    status = service.check_r_environment()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    if status["r_available"]:
        print("\n=== 載入現有結果 ===")
        results = service.load_analysis_results()
        print(json.dumps(results, indent=2, ensure_ascii=False)) 