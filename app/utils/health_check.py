#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Starlink 台北衛星分析系統健康檢查工具
監控系統狀態、資源使用和數據完整性
"""

import os
import sys
import json
import psutil
import requests
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

class SystemHealthChecker:
    def __init__(self):
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'overall_status': 'UNKNOWN',
            'recommendations': []
        }
    
    def check_system_resources(self):
        """檢查系統資源使用情況"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體使用
            memory = psutil.virtual_memory()
            
            # 磁碟使用
            disk = psutil.disk_usage('.')
            
            self.report['checks']['system_resources'] = {
                'status': 'PASS',
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2)
            }
            
            # 警告條件
            warnings = []
            if cpu_percent > 80:
                warnings.append("CPU 使用率過高")
            if memory.percent > 85:
                warnings.append("記憶體使用率過高")
            if disk.percent > 90:
                warnings.append("磁碟空間不足")
            
            if warnings:
                self.report['checks']['system_resources']['warnings'] = warnings
                self.report['recommendations'].extend([
                    "建議關閉不必要的程式以釋放資源",
                    "考慮增加系統記憶體或清理磁碟空間"
                ])
                
        except Exception as e:
            self.report['checks']['system_resources'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def check_python_environment(self):
        """檢查 Python 環境和套件"""
        try:
            import numpy
            import pandas
            import matplotlib
            import skyfield
            import plotly
            
            packages = {
                'numpy': numpy.__version__,
                'pandas': pandas.__version__,
                'matplotlib': matplotlib.__version__,
                'skyfield': skyfield.__version__,
                'plotly': plotly.__version__
            }
            
            self.report['checks']['python_environment'] = {
                'status': 'PASS',
                'python_version': sys.version,
                'packages': packages
            }
            
        except ImportError as e:
            self.report['checks']['python_environment'] = {
                'status': 'FAIL',
                'error': f"缺少套件: {str(e)}"
            }
            self.report['recommendations'].append("執行 'conda env update -f environment.yml' 更新環境")
    
    def check_data_integrity(self):
        """檢查數據完整性"""
        try:
            output_dir = Path('output')
            checks = {}
            
            # 檢查 TLE 數據
            tle_files = list(output_dir.glob('*.tle'))
            if tle_files:
                latest_tle = max(tle_files, key=os.path.getmtime)
                tle_age = datetime.now() - datetime.fromtimestamp(latest_tle.stat().st_mtime)
                tle_size = latest_tle.stat().st_size / 1024  # KB
                
                checks['tle_data'] = {
                    'file': str(latest_tle),
                    'age_hours': round(tle_age.total_seconds() / 3600, 1),
                    'size_kb': round(tle_size, 1),
                    'status': 'FRESH' if tle_age.days < 1 else 'STALE'
                }
                
                if tle_age.days > 3:
                    self.report['recommendations'].append("TLE 數據已過期，建議更新")
            else:
                checks['tle_data'] = {'status': 'MISSING'}
                self.report['recommendations'].append("缺少 TLE 數據文件")
            
            # 檢查分析結果
            csv_files = list(output_dir.glob('coverage_data.csv'))
            if csv_files:
                latest_csv = max(csv_files, key=os.path.getmtime)
                try:
                    df = pd.read_csv(latest_csv)
                    checks['analysis_data'] = {
                        'file': str(latest_csv),
                        'rows': len(df),
                        'columns': list(df.columns),
                        'status': 'VALID' if len(df) > 0 else 'EMPTY'
                    }
                except Exception as e:
                    checks['analysis_data'] = {
                        'file': str(latest_csv),
                        'status': 'CORRUPTED',
                        'error': str(e)
                    }
            else:
                checks['analysis_data'] = {'status': 'MISSING'}
                self.report['recommendations'].append("缺少分析結果數據")
            
            # 檢查統計數據
            stats_file = output_dir / 'coverage_stats.json'
            if stats_file.exists():
                try:
                    with open(stats_file) as f:
                        stats = json.load(f)
                    checks['statistics'] = {
                        'status': 'VALID',
                        'data': stats
                    }
                except Exception as e:
                    checks['statistics'] = {
                        'status': 'CORRUPTED',
                        'error': str(e)
                    }
            else:
                checks['statistics'] = {'status': 'MISSING'}
            
            self.report['checks']['data_integrity'] = checks
            
        except Exception as e:
            self.report['checks']['data_integrity'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def check_network_connectivity(self):
        """檢查網路連接性"""
        try:
            test_urls = [
                'https://celestrak.org',
                'https://www.google.com'
            ]
            
            results = {}
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=10)
                    results[url] = {
                        'status': 'REACHABLE',
                        'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2),
                        'status_code': response.status_code
                    }
                except Exception as e:
                    results[url] = {
                        'status': 'UNREACHABLE',
                        'error': str(e)
                    }
            
            self.report['checks']['network_connectivity'] = results
            
            # 檢查是否有網路問題
            unreachable_count = sum(1 for r in results.values() if r['status'] == 'UNREACHABLE')
            if unreachable_count == len(test_urls):
                self.report['recommendations'].append("網路連接有問題，可能影響 TLE 數據更新")
                
        except Exception as e:
            self.report['checks']['network_connectivity'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def check_file_permissions(self):
        """檢查文件權限"""
        try:
            important_files = [
                'satellite_analysis.py',
                'app.R',
                'environment.yml',
                'start.sh'
            ]
            
            permission_issues = []
            for file_path in important_files:
                if os.path.exists(file_path):
                    if not os.access(file_path, os.R_OK):
                        permission_issues.append(f"{file_path}: 無讀取權限")
                    if file_path.endswith('.sh') and not os.access(file_path, os.X_OK):
                        permission_issues.append(f"{file_path}: 無執行權限")
                else:
                    permission_issues.append(f"{file_path}: 文件不存在")
            
            # 檢查輸出目錄權限
            if not os.access('output', os.W_OK):
                permission_issues.append("output 目錄: 無寫入權限")
            
            self.report['checks']['file_permissions'] = {
                'status': 'PASS' if not permission_issues else 'FAIL',
                'issues': permission_issues
            }
            
            if permission_issues:
                self.report['recommendations'].append("修正文件權限問題")
                
        except Exception as e:
            self.report['checks']['file_permissions'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def determine_overall_status(self):
        """判斷整體系統狀態"""
        fail_count = sum(1 for check in self.report['checks'].values() 
                        if isinstance(check, dict) and check.get('status') == 'FAIL')
        
        warning_count = sum(1 for check in self.report['checks'].values() 
                           if isinstance(check, dict) and 'warnings' in check)
        
        if fail_count == 0 and warning_count == 0:
            self.report['overall_status'] = 'HEALTHY'
        elif fail_count == 0:
            self.report['overall_status'] = 'WARNING'
        else:
            self.report['overall_status'] = 'CRITICAL'
    
    def run_all_checks(self):
        """執行所有健康檢查"""
        print("🔍 執行系統健康檢查...")
        
        self.check_system_resources()
        self.check_python_environment()
        self.check_data_integrity()
        self.check_network_connectivity()
        self.check_file_permissions()
        
        self.determine_overall_status()
        
        return self.report
    
    def print_report(self):
        """輸出檢查報告"""
        status_icons = {
            'HEALTHY': '✅',
            'WARNING': '⚠️',
            'CRITICAL': '❌',
            'PASS': '✅',
            'FAIL': '❌'
        }
        
        print(f"\n{'='*60}")
        print(f"🏥 系統健康檢查報告")
        print(f"📅 時間: {self.report['timestamp']}")
        print(f"📊 整體狀態: {status_icons.get(self.report['overall_status'], '❓')} {self.report['overall_status']}")
        print(f"{'='*60}")
        
        for check_name, check_data in self.report['checks'].items():
            if isinstance(check_data, dict):
                status = check_data.get('status', 'UNKNOWN')
                icon = status_icons.get(status, '❓')
                print(f"\n{icon} {check_name.replace('_', ' ').title()}: {status}")
                
                if 'error' in check_data:
                    print(f"   ❌ 錯誤: {check_data['error']}")
                
                if 'warnings' in check_data:
                    for warning in check_data['warnings']:
                        print(f"   ⚠️ {warning}")
        
        if self.report['recommendations']:
            print(f"\n💡 建議:")
            for i, rec in enumerate(self.report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        print(f"\n{'='*60}")
    
    def save_report(self, filename=None):
        """保存檢查報告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_check_{timestamp}.json"
        
        os.makedirs('logs', exist_ok=True)
        filepath = os.path.join('logs', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 檢查報告已保存: {filepath}")

def main():
    """主函數"""
    checker = SystemHealthChecker()
    report = checker.run_all_checks()
    checker.print_report()
    checker.save_report()
    
    # 根據狀態設定退出代碼
    exit_codes = {
        'HEALTHY': 0,
        'WARNING': 1,
        'CRITICAL': 2
    }
    
    sys.exit(exit_codes.get(report['overall_status'], 3))

if __name__ == "__main__":
    main() 