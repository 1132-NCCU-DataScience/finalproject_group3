#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Starlink 台北衛星分析模組
提供衛星可見性和覆蓋率分析功能
"""

import os
import sys
import json
import time
import argparse
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非互動式後端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import concurrent.futures
from tqdm import tqdm
from skyfield.api import load, wgs84, EarthSatellite, Loader
from skyfield.timelib import Time
from multiprocessing import cpu_count
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from collections import deque

# 忽略一些常見的警告
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# 台北地區常數
TAIPEI_LAT = 25.0330
TAIPEI_LON = 121.5654
ELEVATION = 10.0
utc = timezone.utc

def process_time_point_worker(time_data_tuple, worker_tle_list_of_tuples, worker_observer_lat, worker_observer_lon, worker_observer_elev, worker_ts_init_args, min_elevation_threshold=25):
    """並行處理單個時間點的衛星可見性"""
    t_skyfield, time_point_datetime = time_data_tuple
    visible_satellites = []
    
    # 從傳入的經緯度和高度重新創建觀測者位置
    observer_pos = wgs84.latlon(worker_observer_lat, worker_observer_lon, elevation_m=worker_observer_elev)

    # 重新創建 timescale 物件
    ts = load.timescale(**worker_ts_init_args if worker_ts_init_args else {})

    # 重新創建 EarthSatellite 物件
    worker_sats_list = []
    if isinstance(worker_tle_list_of_tuples, list):
        for tle_tuple in worker_tle_list_of_tuples:
            try:
                name, line1, line2 = tle_tuple
                satellite = EarthSatellite(line1, line2, name, ts)
                worker_sats_list.append(satellite)
            except Exception as e:
                print(f"在 process_time_point_worker 中創建衛星 {name} 失敗: {e}")
                continue
    else:
        print(f"警告: 預期 worker_tle_list_of_tuples 為列表，但收到 {type(worker_tle_list_of_tuples)}。")

    if not isinstance(worker_sats_list, list):
        print(f"警告: 預期 worker_sats_list 為列表，但收到 {type(worker_sats_list)}。跳過此時間點的衛星處理。")
    else:
        for sat_obj in worker_sats_list:
            try:
                geocentric = sat_obj.at(t_skyfield)
                subpoint = wgs84.subpoint(geocentric)
                difference = sat_obj - observer_pos
                topocentric = difference.at(t_skyfield)
                alt, az, distance = topocentric.altaz()
                
                if alt.degrees > min_elevation_threshold:
                    sat_name = getattr(sat_obj, 'name', f"UnknownSatellite-{id(sat_obj)}")
                    visible_satellites.append({
                        'name': sat_name,
                        'distance_km': distance.km,
                        'elevation': alt.degrees,
                        'azimuth': az.degrees,
                        'timestamp': time_point_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    })
            except Exception as e:
                sat_name = getattr(sat_obj, 'name', f"UnknownSatellite-{id(sat_obj)}")
                print(f"處理衛星 {sat_name} 在時間點 {time_point_datetime} 時發生錯誤: {e}")
                continue
    
    best_satellite_info = None
    max_elevation = -90
    
    if visible_satellites:
        for sat_info in visible_satellites:
            if sat_info['elevation'] > max_elevation:
                max_elevation = sat_info['elevation']
                best_satellite_info = sat_info
    
    result = {
        'timestamp': time_point_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'visible_count': len(visible_satellites),
        'visible_satellites': visible_satellites
    }
    
    if best_satellite_info:
        result['elevation'] = best_satellite_info['elevation']
        result['best_satellite'] = best_satellite_info['name']
        result['distance_km'] = best_satellite_info['distance_km']
    else:
        result['elevation'] = 0
        result['best_satellite'] = None
        result['distance_km'] = 0
            
    return result

class StarlinkAnalysis:
    """Starlink 衛星分析類別"""
    
    def __init__(self, output_dir="output", progress_output=False):
        """初始化分析類別"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.progress_output = progress_output
        
        # 初始化 skyfield 的時間尺度
        self.ts = load.timescale()
        
        # 設置觀察者位置（預設為台北市）
        self.observer = wgs84.latlon(TAIPEI_LAT, TAIPEI_LON, elevation_m=ELEVATION)
        
        # 初始化衛星列表
        self.satellites = []
        self.raw_tle_data = []
        
        # 建立輸出目錄
        os.makedirs(output_dir, exist_ok=True)
        
        # 設定 Skyfield 數據載入器
        self.loader = Loader(output_dir, verbose=False)
        
    @staticmethod
    def analyze(lat=TAIPEI_LAT, lon=TAIPEI_LON, interval_minutes=1.0, 
                analysis_duration_minutes=60, min_elevation_threshold=25, 
                output_dir="output", num_cpus=None):
        """
        靜態方法：執行完整的衛星分析
        
        Args:
            lat: 觀察者緯度
            lon: 觀察者經度  
            interval_minutes: 時間間隔（分鐘）
            analysis_duration_minutes: 分析持續時間（分鐘）
            min_elevation_threshold: 最小仰角閾值（度）
            output_dir: 輸出目錄
            num_cpus: CPU 核心數
            
        Returns:
            dict: 包含輸出檔案路徑的字典
        """
        # 創建分析實例
        analyzer = StarlinkAnalysis(output_dir=output_dir, progress_output=True)
        
        # 設置觀察者位置
        analyzer.set_observer_location(lat, lon)
        
        # 下載 TLE 數據
        analyzer.download_tle_data()
        
        if not analyzer.satellites:
            print("錯誤: 無法獲取 TLE 數據")
            return {
                "stats_path": None,
                "report_path": None,
                "data_path": None,
                "plots_paths": []
            }
        
        # 執行分析
        coverage_df = analyzer.analyze_coverage(
            interval_minutes=interval_minutes,
            analysis_duration_minutes=analysis_duration_minutes,
            num_cpus=num_cpus,
            min_elevation_threshold=min_elevation_threshold
        )
        
        if coverage_df.empty:
            print("分析未產生結果")
            return {
                "stats_path": None,
                "report_path": None,
                "data_path": None,
                "plots_paths": []
            }
        
        # 計算統計數據
        stats = analyzer.calculate_stats(coverage_df)
        
        # 生成圖表
        plots_paths = analyzer.generate_plots(coverage_df)
        
        # 保存結果
        file_paths = analyzer.save_results(coverage_df, stats)
        
        return {
            "stats_path": file_paths.get("stats_path"),
            "report_path": file_paths.get("report_path"), 
            "data_path": file_paths.get("data_path"),
            "plots_paths": plots_paths
        }
    
    def set_observer_location(self, lat, lon, elevation_m=10.0):
        """設置觀察者位置"""
        self.observer = wgs84.latlon(lat, lon, elevation_m=elevation_m)
    
    def download_tle_data(self, force_update=False):
        """下載最新的 Starlink TLE 數據"""
        local_file = self.output_dir / 'starlink_latest.tle'
        
        # 如果有本地檔案且不強制更新，直接使用本地檔案
        if local_file.exists() and not force_update:
            print("使用現有的本地 TLE 檔案")
            with open(local_file, 'r', encoding='utf-8') as f:
                tle_data_text = f.read().strip().split('\n')
            
            # 解析衛星數據
            parse_errors = 0
            temp_satellites = []
            temp_raw_tle = []
            
            for i in range(0, len(tle_data_text) - 2, 3):
                name = tle_data_text[i].strip()
                line1 = tle_data_text[i + 1].strip()
                line2 = tle_data_text[i + 2].strip()
                
                if not name or not line1 or not line2:
                    parse_errors += 1
                    continue

                try:
                    satellite = EarthSatellite(line1, line2, name, self.ts)
                    temp_satellites.append(satellite)
                    temp_raw_tle.append((name, line1, line2))
                except Exception as e:
                    parse_errors += 1
                    continue
            
            if len(temp_satellites) >= 100:
                self.satellites = temp_satellites
                self.raw_tle_data = temp_raw_tle
                
                file_size = local_file.stat().st_size / 1024
                print(f"成功使用本地 TLE 文件，解析 {len(self.satellites)} 顆衛星 ({file_size:.1f} KB)")
                return
        
        print("正在下載 Starlink TLE 數據...")
        
        tle_sources = [
            'https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle',
            'https://celestrak.org/NORAD/elements/supplemental/starlink.txt',
            'https://celestrak.org/NORAD/elements/starlink.txt'
        ]
        
        self.raw_tle_data = []
        self.satellites = []

        # 嘗試從網路下載，只重試一次
        download_success = False
        for source_url in tle_sources:
            try:
                print(f"嘗試從 {source_url} 下載")
                
                response = requests.get(source_url, timeout=10)
                if response.status_code != 200:
                    print(f"下載失敗: HTTP {response.status_code}: {response.reason}")
                    continue
                    
                tle_data_text = response.text.strip().split('\n')
                if len(tle_data_text) < 3:
                    print("TLE 數據格式錯誤或數據不完整")
                    continue
                
                # 解析 TLE 數據
                parse_errors = 0
                temp_satellites = []
                temp_raw_tle = []
                
                for i in range(0, len(tle_data_text) - 2, 3):
                    name = tle_data_text[i].strip()
                    line1 = tle_data_text[i + 1].strip()
                    line2 = tle_data_text[i + 2].strip()
                    
                    if not name or not line1 or not line2:
                        parse_errors += 1
                        continue

                    try:
                        satellite = EarthSatellite(line1, line2, name, self.ts)
                        temp_satellites.append(satellite)
                        temp_raw_tle.append((name, line1, line2))
                    except Exception as e:
                        parse_errors += 1
                        continue
                
                if len(temp_satellites) < 100:
                    print(f"解析的衛星數量異常少: {len(temp_satellites)} 顆")
                    continue
                
                self.satellites = temp_satellites
                self.raw_tle_data = temp_raw_tle

                print(f"成功下載並解析 {len(self.satellites)} 顆 Starlink 衛星的 TLE 數據")
                
                # 保存 TLE 數據到文件
                with open(local_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                file_size = local_file.stat().st_size / 1024
                print(f"TLE 數據已保存到 {local_file} ({file_size:.1f} KB)")
                download_success = True
                return
                 
            except Exception as e:
                print(f"下載失敗: {str(e)}")
                continue
        
        # 如果網路下載失敗，嘗試使用現有的本地文件
        if not download_success and local_file.exists():
            print(f"網路下載失敗，嘗試使用現有的 TLE 文件: {local_file}")
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    tle_data_text = f.read().strip().split('\n')
                
                if len(tle_data_text) < 3:
                    raise Exception("本地 TLE 文件格式錯誤或數據不完整")
                
                parse_errors = 0
                temp_satellites = []
                temp_raw_tle = []
                
                for i in range(0, len(tle_data_text) - 2, 3):
                    name = tle_data_text[i].strip()
                    line1 = tle_data_text[i + 1].strip()
                    line2 = tle_data_text[i + 2].strip()
                     
                    if not name or not line1 or not line2:
                        parse_errors += 1
                        continue

                    try:
                        satellite = EarthSatellite(line1, line2, name, self.ts)
                        temp_satellites.append(satellite)
                        temp_raw_tle.append((name, line1, line2))
                    except Exception as e:
                        parse_errors += 1
                        continue
                
                if len(temp_satellites) < 100:
                    raise Exception(f"本地文件解析的衛星數量異常少: {len(temp_satellites)} 顆")
                
                self.satellites = temp_satellites
                self.raw_tle_data = temp_raw_tle
                
                file_size = local_file.stat().st_size / 1024
                print(f"成功使用本地 TLE 文件，解析 {len(self.satellites)} 顆衛星 ({file_size:.1f} KB)")
                print("⚠️  注意：使用的是本地緩存的 TLE 數據，可能不是最新的")
                return
                
            except Exception as e:
                print(f"讀取本地 TLE 文件失敗: {str(e)}")
        
        print("❌ 無法從任何來源獲取 TLE 數據")
        self.satellites = []
        self.raw_tle_data = []
    
    def load_satellites(self):
        """載入衛星數據"""
        if not self.raw_tle_data:
            if not self.download_tle_data():
                raise Exception("無法獲取 TLE 數據")
        
        # 解析 TLE 數據
        lines = self.raw_tle_data.strip().split('\n')
        satellites = {}
        
        # 處理 TLE 數據 (每3行一組)
        for i in range(0, len(lines) - 2, 3):
            if i + 2 < len(lines):
                name_line = lines[i].strip()
                line1 = lines[i + 1].strip()
                line2 = lines[i + 2].strip()
                
                # 確保是有效的 TLE 格式
                if line1.startswith('1 ') and line2.startswith('2 '):
                    try:
                        # 使用 Skyfield 創建衛星對象
                        satellite = self.loader.tle_file_from_text(
                            '\n'.join([name_line, line1, line2])
                        ).by_name[name_line]
                        satellites[name_line] = satellite
                    except Exception as e:
                        # 忽略有問題的 TLE 條目
                        continue
        
        self.satellites = satellites
        print(f"成功載入 {len(self.satellites)} 顆 Starlink 衛星")
        
    def analyze_coverage(self, interval_minutes=1, analysis_duration_minutes=60, num_cpus=None, min_elevation_threshold=25):
        """分析衛星覆蓋情況"""
        if not self.satellites:
            print("錯誤: 衛星列表為空。請先下載 TLE 數據。")
            return pd.DataFrame()

        print(f"開始分析 {analysis_duration_minutes} 分鐘的衛星覆蓋情況，時間間隔 {interval_minutes} 分鐘，最小仰角 {min_elevation_threshold}°...")

        start_time_dt = datetime.now(utc)
        num_time_points = int(analysis_duration_minutes // interval_minutes)
        time_points_dt = [start_time_dt + timedelta(minutes=i * interval_minutes) for i in range(num_time_points)]
        time_points_skyfield = [self.ts.utc(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time_points_dt]

        ts_init_args = {}
        results = []
        
        if num_cpus is None:
            num_cpus = cpu_count()
        
        print(f"使用 {num_cpus} 個 CPU 核心進行並行計算...")

        time_data_tuples = list(zip(time_points_skyfield, time_points_dt))

        if num_cpus > 1:
            try:
                with concurrent.futures.ProcessPoolExecutor(max_workers=num_cpus) as executor:
                    futures = [executor.submit(process_time_point_worker, 
                                              time_data, 
                                              self.raw_tle_data,
                                              self.observer.latitude.degrees, 
                                              self.observer.longitude.degrees, 
                                              self.observer.elevation.m,
                                              ts_init_args,
                                              min_elevation_threshold)
                               for time_data in time_data_tuples]
                    
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        try:
                            results.append(future.result())
                        except Exception as e:
                            print(f"處理時間點時發生錯誤: {e}")
                
                results.sort(key=lambda r: r.get('timestamp', ''))

            except Exception as e:
                print(f"並行處理過程中發生嚴重錯誤: {e}")
                print("將嘗試使用單核處理...")
                results = []
                num_cpus = 1
        
        if num_cpus == 1:
            print("使用單核處理模式...")
            
            for i, time_data in enumerate(tqdm(time_data_tuples, desc="處理時間點", unit="step")):
                try:
                    result = process_time_point_worker(time_data, 
                                                       self.raw_tle_data,
                                                       self.observer.latitude.degrees, 
                                                       self.observer.longitude.degrees, 
                                                       self.observer.elevation.m,
                                                       ts_init_args,
                                                       min_elevation_threshold)
                    results.append(result)
                except Exception as e:
                    failed_time_point_dt = time_data[1]
                    print(f"處理時間點 {failed_time_point_dt.strftime('%Y-%m-%d %H:%M:%S')} 時發生錯誤: {e}")

        if not results:
            print("警告: 分析未產生任何結果。")
            return pd.DataFrame()

        coverage_df = pd.DataFrame(results)
        if coverage_df.empty:
            print("警告: 分析結果 DataFrame 為空。")
            return coverage_df
        
        coverage_df['timestamp'] = pd.to_datetime(coverage_df['timestamp'])
        coverage_df = coverage_df.sort_values(by='timestamp').reset_index(drop=True)

        print("分析完成。")
        return coverage_df
    
    def calculate_stats(self, coverage_df):
        """從覆蓋率數據計算統計數據"""
        try:
            if 'visible_count' in coverage_df.columns:
                count_column = 'visible_count'
            else:
                raise ValueError("找不到可見衛星數量數據")
            
            stats = {
                'avg_visible_satellites': float(coverage_df[count_column].mean()),
                'max_visible_satellites': int(coverage_df[count_column].max()),
                'min_visible_satellites': int(coverage_df[count_column].min()),
                'coverage_percentage': float((coverage_df[count_column] > 0).mean() * 100),
                'analysis_duration_minutes': len(coverage_df),
                'observer_lat': self.observer.latitude.degrees,
                'observer_lon': self.observer.longitude.degrees
            }
            
            if 'elevation' in coverage_df.columns and not coverage_df['elevation'].isnull().all():
                stats['avg_elevation'] = float(coverage_df['elevation'].mean())
                stats['max_elevation'] = float(coverage_df['elevation'].max())
            else:
                stats['avg_elevation'] = 0
                stats['max_elevation'] = 0
                
            return stats
        except Exception as e:
            print(f"計算統計數據時出錯: {e}")
            return {
                'avg_visible_satellites': 0,
                'max_visible_satellites': 0,
                'min_visible_satellites': 0,
                'coverage_percentage': 0,
                'avg_elevation': 0,
                'max_elevation': 0,
                'analysis_duration_minutes': 0,
                'observer_lat': self.observer.latitude.degrees,
                'observer_lon': self.observer.longitude.degrees
            }
    
    def generate_plots(self, coverage_df):
        """生成分析圖表"""
        plots_paths = []
        
        try:
            # 設置中文字體支持
            plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'PingFang TC', 'Hiragino Sans TC', 'Noto Sans CJK TC', 'SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.family'] = 'sans-serif'
            
            # 1. 可見衛星數量時間線
            plt.figure(figsize=(12, 6))
            coverage_df['time_minutes'] = range(len(coverage_df))
            plt.plot(coverage_df['time_minutes'], coverage_df['visible_count'], 
                    color='#3498db', linewidth=2, alpha=0.8)
            plt.fill_between(coverage_df['time_minutes'], coverage_df['visible_count'], 
                           alpha=0.3, color='#3498db')
            plt.title('Starlink 可見衛星數量時間線', fontsize=16, fontweight='bold')
            plt.xlabel('時間 (分鐘)')
            plt.ylabel('可見衛星數量')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            timeline_path = self.output_dir / 'visible_satellites_timeline.png'
            plt.savefig(timeline_path, dpi=300, bbox_inches='tight')
            plt.close()
            plots_paths.append(str(timeline_path))
            print(f"時間線圖表已保存到 {timeline_path}")
            
            # 2. 仰角時間線（如果有數據）
            if 'elevation' in coverage_df.columns and not coverage_df['elevation'].isnull().all():
                plt.figure(figsize=(12, 6))
                plt.plot(coverage_df['time_minutes'], coverage_df['elevation'], 
                        color='#e74c3c', linewidth=2, alpha=0.8)
                plt.fill_between(coverage_df['time_minutes'], coverage_df['elevation'], 
                               alpha=0.3, color='#e74c3c')
                plt.title('最佳衛星仰角時間線', fontsize=16, fontweight='bold')
                plt.xlabel('時間 (分鐘)')
                plt.ylabel('仰角 (度)')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                elevation_path = self.output_dir / 'elevation_timeline.png'
                plt.savefig(elevation_path, dpi=300, bbox_inches='tight')
                plt.close()
                plots_paths.append(str(elevation_path))
                print(f"仰角圖表已保存到 {elevation_path}")
            
        except Exception as e:
            print(f"生成圖表時出錯: {e}")
        
        return plots_paths
    
    def save_results(self, coverage_df=None, stats=None):
        """保存分析結果"""
        file_paths = {}
        
        # 保存覆蓋率數據
        if coverage_df is not None:
            csv_path = self.output_dir / 'coverage_data.csv'
            coverage_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            file_paths['data_path'] = str(csv_path)
            print(f"詳細數據已保存到 {csv_path}")
        
        # 保存統計數據
        if stats is not None:
            stats_path = self.output_dir / 'coverage_stats.json'
            # 確保所有數據都可序列化
            serializable_stats = {}
            for key, value in stats.items():
                if isinstance(value, (np.integer, np.floating, np.bool_)):
                    serializable_stats[key] = value.item()
                elif isinstance(value, datetime):
                    serializable_stats[key] = value.isoformat()
                else:
                    serializable_stats[key] = value
            
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_stats, f, ensure_ascii=False, indent=4)
            file_paths['stats_path'] = str(stats_path)
            print(f"統計數據已保存到 {stats_path}")
        
        # 生成簡單的 HTML 報告
        if coverage_df is not None and stats is not None:
            report_path = self.output_dir / 'coverage_report.html'
            self._generate_html_report(report_path, coverage_df, stats)
            file_paths['report_path'] = str(report_path)
        
        return file_paths
    
    def _generate_html_report(self, report_path, coverage_df, stats):
        """生成簡單的 HTML 報告"""
        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>台北市 Starlink 衛星覆蓋分析報告</title>
    <style>
        body {{ font-family: 'Microsoft JhengHei', 'PingFang TC', 'Hiragino Sans TC', 'Noto Sans CJK TC', sans-serif; margin: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .stats-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .stat-title {{ color: #7f8c8d; margin-top: 10px; }}
        .visualization-container {{ margin: 30px 0; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>台北市 Starlink 衛星覆蓋分析報告</h1>
        <p style="text-align: center; color: #7f8c8d;">分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-value">{stats.get('avg_visible_satellites', 0):.1f}</div>
                <div class="stat-title">平均可見衛星數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('max_visible_satellites', 0)}</div>
                <div class="stat-title">最大可見衛星數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('coverage_percentage', 0):.1f}%</div>
                <div class="stat-title">衛星覆蓋率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('avg_elevation', 0):.1f}°</div>
                <div class="stat-title">平均最佳仰角</div>
            </div>
        </div>
        
        <div class="visualization-container">
            <h2>可見衛星數量時間線</h2>
            <img src="./visible_satellites_timeline.png" alt="可見衛星數量時間線">
        </div>
        
        <div class="visualization-container">
            <h2>最佳衛星仰角時間線</h2>
            <img src="./elevation_timeline.png" alt="最佳衛星仰角時間線">
        </div>
    </div>
</body>
</html>"""
        
        with open(report_path, "w", encoding='utf-8', newline='') as f:
            f.write(html_content)
        print(f"HTML 報告已生成到 {report_path}")

class SelfAttention(nn.Module):
    """自注意力機制模組"""
    def __init__(self, d_model, n_heads=8):
        super(SelfAttention, self).__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
        
    def forward(self, x):
        batch_size, seq_len, _ = x.size()
        
        Q = self.W_q(x).view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(x).view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(x).view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        
        attention_scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.d_k ** 0.5)
        attention_weights = F.softmax(attention_scores, dim=-1)
        attention_output = torch.matmul(attention_weights, V)
        
        attention_output = attention_output.transpose(1, 2).contiguous().view(
            batch_size, seq_len, self.d_model)
        
        return self.W_o(attention_output)

class SCINetBlock(nn.Module):
    """SCINet 基礎模組 - 參考論文實現"""
    def __init__(self, input_dim, hidden_dim, kernel_size=3):
        super(SCINetBlock, self).__init__()
        self.conv1 = nn.Conv1d(input_dim, hidden_dim, kernel_size, padding=kernel_size//2)
        self.conv2 = nn.Conv1d(hidden_dim, input_dim, kernel_size, padding=kernel_size//2)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(input_dim)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        x_conv = x.transpose(1, 2)  # (batch, features, seq_len)
        
        conv_out = F.relu(self.conv1(x_conv))
        conv_out = conv_out.transpose(1, 2)  # (batch, seq_len, hidden_dim)
        conv_out = self.norm1(conv_out)
        conv_out = self.dropout(conv_out)
        
        conv_out = conv_out.transpose(1, 2)  # (batch, hidden_dim, seq_len)
        conv_out = self.conv2(conv_out)
        conv_out = conv_out.transpose(1, 2)  # (batch, seq_len, features)
        
        return self.norm2(x + conv_out)

class SCINetSA(nn.Module):
    """SCINet with Self-Attention 軌道預測模型"""
    def __init__(self, input_dim=6, hidden_dim=64, num_layers=4, seq_len=168, pred_len=24):
        super(SCINetSA, self).__init__()
        self.input_dim = input_dim  # x, y, z, vx, vy, vz
        self.hidden_dim = hidden_dim
        self.seq_len = seq_len  # 歷史數據長度（小時）
        self.pred_len = pred_len  # 預測長度（小時）
        
        # 輸入嵌入
        self.input_embed = nn.Linear(input_dim, hidden_dim)
        
        # SCINet 層
        self.scinet_layers = nn.ModuleList([
            SCINetBlock(hidden_dim, hidden_dim * 2) for _ in range(num_layers)
        ])
        
        # 自注意力層
        self.self_attention = SelfAttention(hidden_dim)
        
        # 輸出層
        self.output_projection = nn.Linear(hidden_dim, input_dim)
        self.final_projection = nn.Linear(seq_len, pred_len)
        
    def forward(self, x):
        # x shape: (batch, seq_len, input_dim)
        x = self.input_embed(x)
        
        # SCINet 層
        for layer in self.scinet_layers:
            x = layer(x)
        
        # 自注意力
        x = self.self_attention(x)
        
        # 輸出投影
        x = self.output_projection(x)  # (batch, seq_len, input_dim)
        x = x.transpose(1, 2)  # (batch, input_dim, seq_len)
        x = self.final_projection(x)  # (batch, input_dim, pred_len)
        x = x.transpose(1, 2)  # (batch, pred_len, input_dim)
        
        return x

class OrbitPredictionEnhancer:
    """軌道預測增強器 - 基於深度學習"""
    
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = SCINetSA().to(self.device)
        self.scaler = StandardScaler()
        self.history_buffer = deque(maxlen=168)  # 保存7天的歷史數據（每小時一個點）
        self.is_trained = False
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def collect_orbit_data(self, satellite_states):
        """收集衛星軌道狀態數據"""
        for sat_name, state in satellite_states.items():
            if 'STARLINK' in sat_name:  # 只處理 Starlink 衛星
                # 提取位置和速度向量
                orbit_vector = [
                    state.get('x', 0), state.get('y', 0), state.get('z', 0),
                    state.get('vx', 0), state.get('vy', 0), state.get('vz', 0)
                ]
                self.history_buffer.append({
                    'timestamp': datetime.now(),
                    'satellite': sat_name,
                    'orbit_vector': orbit_vector
                })
    
    def predict_orbit_corrections(self, current_orbits, prediction_hours=24):
        """預測軌道修正量"""
        if not self.is_trained or len(self.history_buffer) < 168:
            return {}  # 需要足夠的歷史數據
        
        corrections = {}
        
        try:
            # 準備輸入數據
            X = []
            for i in range(len(self.history_buffer) - 168 + 1, len(self.history_buffer) + 1):
                if i >= 0:
                    X.append(self.history_buffer[i]['orbit_vector'])
            
            X = np.array(X).reshape(1, 168, 6)  # (1, seq_len, features)
            X_scaled = self.scaler.transform(X.reshape(-1, 6)).reshape(1, 168, 6)
            
            # 模型預測
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X_scaled).to(self.device)
                predictions = self.model(X_tensor)
                predictions = predictions.cpu().numpy()
                
                # 反標準化
                predictions = self.scaler.inverse_transform(
                    predictions.reshape(-1, 6)
                ).reshape(1, prediction_hours, 6)
            
            # 計算修正量
            for sat_name, current_state in current_orbits.items():
                if 'STARLINK' in sat_name:
                    predicted_corrections = predictions[0]  # 取第一個批次的結果
                    corrections[sat_name] = predicted_corrections
                    
        except Exception as e:
            print(f"軌道預測修正失敗: {e}")
        
        return corrections
    
    def train_model(self, orbit_history_data, epochs=100):
        """訓練模型"""
        if len(orbit_history_data) < 1000:  # 需要足夠的訓練數據
            print("警告：訓練數據不足")
            return False
        
        # 準備訓練數據
        X, y = self._prepare_training_data(orbit_history_data)
        
        # 標準化
        X_scaled = self.scaler.fit_transform(X.reshape(-1, 6)).reshape(X.shape)
        y_scaled = self.scaler.transform(y.reshape(-1, 6)).reshape(y.shape)
        
        # 轉換為 PyTorch 張量
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)
        y_tensor = torch.FloatTensor(y_scaled).to(self.device)
        
        # 訓練
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            
            if epoch % 20 == 0:
                print(f"Epoch {epoch}, Loss: {loss.item():.6f}")
        
        self.is_trained = True
        return True
    
    def _prepare_training_data(self, orbit_data):
        """準備訓練數據"""
        # 實現數據準備邏輯
        # 這裡需要根據實際的軌道數據格式來實現
        pass
    
    def save_model(self, path):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }, path)
    
    def load_model(self, path):
        """載入模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.scaler = checkpoint['scaler']
        self.is_trained = checkpoint['is_trained']

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Starlink 衛星覆蓋分析工具")
    parser.add_argument('--duration', type=int, default=60, help="分析持續時間（分鐘）")
    parser.add_argument('--interval', type=float, default=1.0, help="分析時間間隔（分鐘）")
    parser.add_argument('--lat', type=float, default=TAIPEI_LAT, help="觀察者緯度")
    parser.add_argument('--lon', type=float, default=TAIPEI_LON, help="觀察者經度")
    parser.add_argument('--min_elevation', type=float, default=25.0, help="最小衛星仰角閾值（度）")
    parser.add_argument('--output', type=str, default="output", help="輸出目錄")
    parser.add_argument('--cpu', type=int, default=None, help="用於並行處理的 CPU 核心數")

    args = parser.parse_args()
    
    # 執行分析
    result = StarlinkAnalysis.analyze(
        lat=args.lat,
        lon=args.lon,
        interval_minutes=args.interval,
        analysis_duration_minutes=args.duration,
        min_elevation_threshold=args.min_elevation,
        output_dir=args.output,
        num_cpus=args.cpu
    )
    
    if result['stats_path']:
        print(f"✅ 分析完成！結果保存在 {args.output} 目錄中")
        print(f"   統計數據: {result['stats_path']}")
        print(f"   詳細數據: {result['data_path']}")
        print(f"   HTML 報告: {result['report_path']}")
    else:
        print("❌ 分析失敗") 