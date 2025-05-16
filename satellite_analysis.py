#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from skyfield.api import load, wgs84, EarthSatellite, utc
from tqdm import tqdm
import plotly.express as px
import plotly.graph_objects as go
import concurrent.futures
import argparse

# 台北市經緯度座標
TAIPEI_LAT = 25.0330
TAIPEI_LON = 121.5654
ELEVATION = 10.0  # 假設高度(公尺)

# 設定中文字體，嘗試使用文泉驛微米黑，如果沒有，matplotlib會回退到預設字體
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei'] 
# 解決負號顯示問題
plt.rcParams['axes.unicode_minus'] = False 

class StarlinkAnalysis:
    def __init__(self, tle_file=None, output_dir="output"):
        """初始化分析類別"""
        self.output_dir = output_dir
        
        # 創建輸出目錄
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 加載天體資料
        self.ts = load.timescale()
        
        # 設定觀測位置 (台北)
        self.observer = wgs84.latlon(TAIPEI_LAT, TAIPEI_LON, ELEVATION)
        
        # 載入TLE數據或下載最新的Starlink TLE
        if tle_file and os.path.exists(tle_file):
            self.load_tle(tle_file)
        else:
            self.download_latest_tle()
    
    def download_latest_tle(self):
        """下載最新的Starlink衛星TLE數據"""
        print("下載最新的Starlink TLE資料...")
        # Ensure skyfield.api.EarthSatellite is imported for type checking
        from skyfield.api import EarthSatellite

        try:
            # Attempt to load TLE data
            self.satellites = load.tle_file('https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle')
        except Exception as e:
            print(f"下載 TLE 數據時發生錯誤: {e}")
            print("將使用一個空的衛星列表繼續。")
            self.satellites = [] # Initialize with an empty list on failure
            return # Exit the method if TLE download fails

        print(f"已加載 {len(self.satellites)} 顆Starlink衛星")
        
        # 儲存TLE資料到本地
        with open(f"{self.output_dir}/starlink_latest.tle", 'w') as f:
            for sat_obj in self.satellites:
                # Ensure we are dealing with an EarthSatellite object
                if not isinstance(sat_obj, EarthSatellite):
                    print(f"警告: 偵測到非 EarthSatellite 物件並已跳過: {type(sat_obj)} - {sat_obj}")
                    continue

                f.write(f"{sat_obj.name}\\n")
                
                # For Skyfield 1.46, _tle_lines should be the primary way
                if hasattr(sat_obj, '_tle_lines') and isinstance(sat_obj._tle_lines, (list, tuple)) and len(sat_obj._tle_lines) == 2:
                    f.write(f"{sat_obj._tle_lines[0]}\\n")
                    f.write(f"{sat_obj._tle_lines[1]}\\n")
                # Fallback for very old Skyfield versions (less likely with skyfield==1.46)
                elif hasattr(sat_obj, 'model') and hasattr(sat_obj.model, 'line1') and hasattr(sat_obj.model, 'line2'):
                    f.write(f"{sat_obj.model.line1}\\n")
                    f.write(f"{sat_obj.model.line2}\\n")
                else:
                    # If TLE lines cannot be determined, write placeholders and a warning
                    print(f"警告: 無法獲取衛星 {sat_obj.name} (類型: {type(sat_obj)}) 的 TLE 行。")
                    print("這可能是由於 Skyfield 版本不兼容或 TLE 數據源問題。")
                    f.write("# TLE DATA UNAVAILABLE (check Skyfield version compatibility or TLE source)\\n")
                    f.write("# TLE DATA UNAVAILABLE\\n")
    
    def load_tle(self, tle_file):
        """從文件載入TLE數據"""
        print(f"從 {tle_file} 載入TLE資料...")
        self.satellites = load.tle_file(tle_file)
        print(f"已加載 {len(self.satellites)} 顆衛星")
    
    def analyze_24h_coverage(self, interval_minutes=1, n_processes=None):
        """分析24小時內的衛星覆蓋情況，支援多執行緒並行運算
        
        Args:
            interval_minutes: 分析間隔時間（分鐘）
            n_processes: 要使用的處理器數量，默認為 None（使用所有可用CPU）
        """
        # 設定時間範圍 (從當前時間開始的24小時)
        now = datetime.utcnow()
        start_time = self.ts.utc(now.year, now.month, now.day, now.hour, now.minute)
        
        # 創建時間點列表
        time_points = []
        for i in range(24 * 60 // interval_minutes):
            time_point = now + timedelta(minutes=i * interval_minutes)
            t = self.ts.utc(time_point.year, time_point.month, time_point.day, 
                           time_point.hour, time_point.minute, time_point.second)
            time_points.append((t, time_point))
        
        print(f"開始處理 {len(time_points)} 個時間點的分析...")
        
        # 設定台北的位置
        if hasattr(self.observer.elevation, 'km'):
            elevation_m = self.observer.elevation.m
        else:
            elevation_m = float(self.observer.elevation)
        
        taipei = wgs84.latlon(self.observer.latitude.degrees, self.observer.longitude.degrees, elevation_m)
        
        # 我們會使用concurrent.futures來並行處理衛星位置計算
        if n_processes is None or n_processes <= 0:
            n_processes = os.cpu_count()
        
        print(f"使用 {n_processes} 個CPU核心進行計算")
        
        # 定義處理每個時間點的函數
        def process_time_point(time_data):
            t, time_point = time_data
            visible_satellites = []
            
            # 檢查衛星是否是dict或list類型，並相應處理
            if hasattr(self.satellites, 'items'):
                # 處理字典型衛星列表
                for sat_name, sat in self.satellites.items():
                    try:
                        difference = sat - taipei
                        topocentric = difference.at(t)
                        alt, az, distance = topocentric.altaz()
                        
                        if alt.degrees > 25:
                            visible_satellites.append({
                                'name': sat_name,
                                'distance_km': distance.km,
                                'elevation': alt.degrees,
                                'azimuth': az.degrees,
                                'timestamp': time_point.strftime('%Y-%m-%d %H:%M:%S')
                            })
                    except Exception as e:
                        continue
            else:
                # 處理列表型衛星列表
                for sat in self.satellites:
                    try:
                        difference = sat - taipei
                        topocentric = difference.at(t)
                        alt, az, distance = topocentric.altaz()
                        
                        if alt.degrees > 25:
                            # 嘗試獲取衛星名稱
                            sat_name = getattr(sat, 'name', f"Unknown-{id(sat)}")
                            
                            visible_satellites.append({
                                'name': sat_name,
                                'distance_km': distance.km,
                                'elevation': alt.degrees,
                                'azimuth': az.degrees,
                                'timestamp': time_point.strftime('%Y-%m-%d %H:%M:%S')
                            })
                    except Exception as e:
                        continue
            
            # 找出最佳衛星（最高仰角）
            best_satellite = None
            max_elevation = 0
            
            for sat in visible_satellites:
                if sat['elevation'] > max_elevation:
                    max_elevation = sat['elevation']
                    best_satellite = sat
            
            # 返回可見衛星列表、數量和最佳衛星
            result = {
                'timestamp': time_point.strftime('%Y-%m-%d %H:%M:%S'),
                'visible_count': len(visible_satellites),
                'visible_satellites': visible_satellites
            }
            
            if best_satellite:
                result['elevation'] = best_satellite['elevation']
                result['best_satellite'] = best_satellite['name']
                result['distance_km'] = best_satellite['distance_km']
            else:
                result['elevation'] = 0
                result['best_satellite'] = None
                result['distance_km'] = 0
                
            return result
        
        # 使用線程池並行處理 (注意：這裡使用ThreadPoolExecutor而不是ProcessPoolExecutor
        # 因為多線程對於I/O密集和Python的GIL鎖問題更適合)
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_processes) as executor:
            # 提交所有任務並獲取Future物件
            future_to_timepoint = {executor.submit(process_time_point, tp): tp for tp in time_points}
            
            # 使用tqdm顯示進度條
            for future in tqdm(concurrent.futures.as_completed(future_to_timepoint), total=len(time_points)):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"處理時間點時發生錯誤: {e}")
        
        # 轉換結果為DataFrame
        self.coverage_df = pd.DataFrame(results)
        
        # 保存分析結果
        self.coverage_df.to_csv(f"{self.output_dir}/coverage_data.csv", index=False)
        
        # 計算和保存統計數據
        stats = {
            'avg_visible_count': float(self.coverage_df['visible_count'].mean()),
            'max_visible_count': int(self.coverage_df['visible_count'].max()),
            'min_visible_count': int(self.coverage_df['visible_count'].min())
        }
        
        if 'elevation' in self.coverage_df.columns:
            stats['avg_elevation'] = float(self.coverage_df['elevation'].mean())
            stats['max_elevation'] = float(self.coverage_df['elevation'].max())
        
        with open(f"{self.output_dir}/coverage_stats.json", 'w') as f:
            json.dump(stats, f, indent=4)
        
        print(f"分析完成，結果已保存至 {self.output_dir}/coverage_data.csv")
        print(f"統計數據已保存至 {self.output_dir}/coverage_stats.json")
        
        # 生成視覺化結果
        self.generate_visualizations()
        
        return self.coverage_df
    
    def generate_visualizations(self):
        """生成可視化結果"""
        # 檢查是否已執行分析
        if not hasattr(self, 'coverage_df'):
            print("請先執行分析")
            return

        # 檢查 DataFrame 是否有 elevation 列
        if 'elevation' not in self.coverage_df.columns:
            print("警告：缺少 elevation 數據，無法生成仰角圖")
            max_elevations = pd.DataFrame()
        else:
            # 生成衛星仰角圖
            plt.figure(figsize=(12, 6))
            plt.plot(self.coverage_df['timestamp'], self.coverage_df['elevation'])
            plt.title('衛星最大仰角隨時間變化')
            plt.xlabel('時間')
            plt.ylabel('最大仰角 (度)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/elevation_timeline.png", dpi=300)
            plt.close()

        # 生成可見衛星數量隨時間變化的圖形
        plt.figure(figsize=(12, 6))
        plt.plot(self.coverage_df['timestamp'], self.coverage_df['visible_count'])
        plt.title('台北市區可見 Starlink 衛星數量變化')
        plt.xlabel('時間點')
        plt.ylabel('可見衛星數量 (個)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/visible_satellites_timeline.png", dpi=300)
        plt.close()

        # 其他可視化
        # TODO: 添加更多有用的可視化
    
    def export_html_report(self):
        """生成HTML報告"""
        if not hasattr(self, 'coverage_df'):
            print("請先執行分析")
            return
        
        # 計算統計數據
        stats = {
            'total_time_points': len(self.coverage_df),
            'avg_visible_count': self.coverage_df['visible_count'].mean(),
            'max_visible_count': self.coverage_df['visible_count'].max(),
            'min_visible_count': self.coverage_df['visible_count'].min(),
            'avg_elevation': self.coverage_df['elevation'].mean() if 'elevation' in self.coverage_df.columns else 0,
            'max_elevation': self.coverage_df['elevation'].max() if 'elevation' in self.coverage_df.columns else 0,
            'coverage_percentage': (self.coverage_df['visible_count'] > 0).mean() * 100
        }
        
        # 計算不同衛星的可見時間
        satellite_visibility = {}
        # 只有當每個時間點的visible_satellites有效時才計算
        if all('visible_satellites' in result for _, result in self.coverage_df.iterrows()):
            for _, row in self.coverage_df.iterrows():
                for sat in row['visible_satellites']:
                    if isinstance(sat, dict) and 'name' in sat:
                        sat_name = sat['name']
                        if sat_name not in satellite_visibility:
                            satellite_visibility[sat_name] = 0
                        satellite_visibility[sat_name] += 1
        
        # 轉換為分鐘
        if satellite_visibility:
            interval_minutes = (24 * 60) / len(self.coverage_df)
            satellite_visibility_minutes = {k: v * interval_minutes for k, v in satellite_visibility.items()}
            stats['satellite_visibility_minutes'] = dict(sorted(
                satellite_visibility_minutes.items(), 
                key=lambda item: item[1], 
                reverse=True
            )[:10])  # 只取前10個
        else:
            stats['satellite_visibility_minutes'] = {}
        
        # 創建HTML報告
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>台北市 Starlink 衛星覆蓋分析報告</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #0066cc;
                }}
                .stats-container {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                .stat-card {{
                    background-color: #f5f5f5;
                    border-radius: 8px;
                    padding: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    flex: 1 1 200px;
                }}
                .stat-title {{
                    font-size: 0.9em;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .stat-value {{
                    font-size: 1.8em;
                    font-weight: bold;
                    color: #0066cc;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
            </style>
        </head>
        <body>
            <h1>台北市 Starlink 衛星覆蓋分析報告</h1>
            <p>分析時間: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            
            <h2>主要統計數據</h2>
            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-title">平均可見衛星數</div>
                    <div class="stat-value">{stats['avg_visible_count']:.1f}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">最大可見衛星數</div>
                    <div class="stat-value">{stats['max_visible_count']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">最小可見衛星數</div>
                    <div class="stat-value">{stats['min_visible_count']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">平均最佳仰角</div>
                    <div class="stat-value">{stats['avg_elevation']:.1f}°</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">最大仰角</div>
                    <div class="stat-value">{stats['max_elevation']:.1f}°</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">有衛星覆蓋時間比例</div>
                    <div class="stat-value">{stats['coverage_percentage']:.1f}%</div>
                </div>
            </div>
            
            <h2>衛星可見時間</h2>
            <table>
                <tr>
                    <th>衛星名稱</th>
                    <th>可見時間 (分鐘)</th>
                </tr>
                {''.join([f"<tr><td>{sat}</td><td>{minutes:.1f}</td></tr>" 
                          for sat, minutes in stats['satellite_visibility_minutes'].items()])}
            </table>
            
            <h2>視覺化結果</h2>
            <div>
                <h3>可見衛星數量時間線</h3>
                <img src="visible_satellites_timeline.png" alt="可見衛星數量時間線">
                
                <h3>最佳衛星仰角時間線</h3>
                <img src="elevation_timeline.png" alt="最佳衛星仰角時間線">
                
                <h3>互動式覆蓋熱力圖</h3>
                <iframe src="coverage_heatmap.html" width="100%" height="600px"></iframe>
            </div>
        </body>
        </html>
        """
        
        # 保存HTML報告
        with open(f"{self.output_dir}/report.html", "w") as f:
            f.write(html_content)
        
        print(f"HTML報告已保存至 {self.output_dir}/report.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Starlink衛星覆蓋分析工具')
    parser.add_argument('--tle', help='TLE文件路徑 (如未指定則下載最新數據)')
    parser.add_argument('--output', default='output', help='輸出目錄')
    parser.add_argument('--cpu', type=int, default=0, help='使用的CPU數量 (0表示使用所有可用CPU)')
    args = parser.parse_args()
    
    # 創建分析器物件
    analyzer = StarlinkAnalysis(tle_file=args.tle, output_dir=args.output)
    
    # 執行分析
    n_processes = None if args.cpu <= 0 else args.cpu
    analyzer.analyze_24h_coverage(n_processes=n_processes)
    
    # 打印分析結果
    if hasattr(analyzer, 'coverage_df'):
        print(f"\n==== 分析結果摘要 ====")
        print(f"平均可見衛星數量: {analyzer.coverage_df['visible_count'].mean():.2f}")
        print(f"最大可見衛星數量: {analyzer.coverage_df['visible_count'].max()}")
        print(f"最小可見衛星數量: {analyzer.coverage_df['visible_count'].min()}")
        print("============================\n") 