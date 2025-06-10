#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自動化數據收集腳本
用於收集 Starlink 衛星歷史軌道數據以訓練深度學習模型
"""

import os
import sys
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import logging

# 添加專案根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

from satellite_analysis import StarlinkAnalyzer

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """歷史數據收集器"""
    
    def __init__(self, output_dir: str = "data/training"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analyzer = None
        
    def collect_daily_data(self, date: datetime, observer_lat: float = 25.0330, observer_lon: float = 121.5654):
        """收集指定日期的衛星數據"""
        try:
            if self.analyzer is None:
                self.analyzer = StarlinkAnalyzer(observer_lat, observer_lon)
                self.analyzer.load_tle_data()
            
            # 生成該日期的分析數據
            results = []
            
            # 每小時採樣一次
            for hour in range(24):
                analysis_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                try:
                    # 分析該時間點的衛星狀態
                    visible_sats = self.analyzer.get_visible_satellites_at_time(analysis_time)
                    
                    # 提取軌道參數
                    orbit_data = {
                        'timestamp': analysis_time.isoformat(),
                        'hour': hour,
                        'day_of_year': analysis_time.timetuple().tm_yday,
                        'visible_count': len(visible_sats),
                        'satellites': []
                    }
                    
                    for sat_name, sat_info in visible_sats.items():
                        if 'position' in sat_info and 'velocity' in sat_info:
                            sat_data = {
                                'name': sat_name,
                                'elevation': sat_info.get('elevation', 0),
                                'azimuth': sat_info.get('azimuth', 0),
                                'distance': sat_info.get('distance_km', 0),
                                'position': sat_info['position'],  # [x, y, z]
                                'velocity': sat_info['velocity']   # [vx, vy, vz]
                            }
                            orbit_data['satellites'].append(sat_data)
                    
                    results.append(orbit_data)
                    
                except Exception as e:
                    logger.warning(f"分析時間 {analysis_time} 失敗: {e}")
                    continue
            
            # 保存日期數據
            date_str = date.strftime("%Y%m%d")
            output_file = self.output_dir / f"starlink_data_{date_str}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"已保存 {date_str} 的數據到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"收集 {date.strftime('%Y-%m-%d')} 數據失敗: {e}")
            return None
    
    def collect_historical_range(self, 
                               start_date: datetime, 
                               end_date: datetime,
                               observer_lat: float = 25.0330, 
                               observer_lon: float = 121.5654):
        """收集指定時間範圍的歷史數據"""
        logger.info(f"開始收集 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 的數據")
        
        current_date = start_date
        collected_files = []
        
        while current_date <= end_date:
            logger.info(f"正在收集 {current_date.strftime('%Y-%m-%d')} 的數據...")
            
            output_file = self.collect_daily_data(current_date, observer_lat, observer_lon)
            if output_file:
                collected_files.append(output_file)
            
            current_date += timedelta(days=1)
            
            # 避免過度負載，每次收集後休息
            time.sleep(1)
        
        logger.info(f"收集完成，共收集了 {len(collected_files)} 個文件")
        
        # 生成數據集摘要
        self.generate_dataset_summary(collected_files)
        
        return collected_files
    
    def generate_dataset_summary(self, data_files: list):
        """生成數據集摘要"""
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_files': len(data_files),
            'files': [],
            'statistics': {
                'total_observations': 0,
                'total_satellites_observed': 0,
                'date_range': {'start': None, 'end': None}
            }
        }
        
        all_dates = []
        total_obs = 0
        total_sats = 0
        
        for file_path in data_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                file_info = {
                    'filename': file_path.name,
                    'observations': len(data),
                    'satellites_count': sum(len(obs.get('satellites', [])) for obs in data)
                }
                
                summary['files'].append(file_info)
                total_obs += file_info['observations']
                total_sats += file_info['satellites_count']
                
                # 提取日期信息
                if data:
                    date_str = data[0]['timestamp'][:10]  # YYYY-MM-DD
                    all_dates.append(date_str)
                
            except Exception as e:
                logger.warning(f"處理文件 {file_path} 時出錯: {e}")
        
        summary['statistics']['total_observations'] = total_obs
        summary['statistics']['total_satellites_observed'] = total_sats
        
        if all_dates:
            all_dates.sort()
            summary['statistics']['date_range']['start'] = all_dates[0]
            summary['statistics']['date_range']['end'] = all_dates[-1]
        
        # 保存摘要
        summary_file = self.output_dir / "dataset_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"數據集摘要已保存到 {summary_file}")
        
        print(f"\n=== 數據收集摘要 ===")
        print(f"總文件數: {summary['total_files']}")
        print(f"總觀測次數: {summary['statistics']['total_observations']}")
        print(f"總衛星觀測: {summary['statistics']['total_satellites_observed']}")
        print(f"日期範圍: {summary['statistics']['date_range']['start']} 到 {summary['statistics']['date_range']['end']}")

def main():
    """主要執行功能"""
    collector = HistoricalDataCollector()
    
    # 收集過去30天的數據（模擬）
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=30)
    
    print(f"=== Starlink 歷史數據收集 ===")
    print(f"收集時間範圍: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print(f"觀測位置: 台北 (25.0330°N, 121.5654°E)")
    
    # 開始收集
    collected_files = collector.collect_historical_range(start_date, end_date)
    
    print(f"\n收集完成！共收集了 {len(collected_files)} 個數據文件")
    print(f"數據保存在: {collector.output_dir}")

if __name__ == "__main__":
    main() 