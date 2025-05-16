#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from skyfield.api import load, wgs84, EarthSatellite
from tqdm import tqdm
import plotly.express as px
import plotly.graph_objects as go

# 台北市經緯度座標
TAIPEI_LAT = 25.0330
TAIPEI_LON = 121.5654
ELEVATION = 10.0  # 假設高度(公尺)

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
    
    def analyze_24h_coverage(self, interval_minutes=1):
        """分析24小時內的衛星覆蓋情況"""
        # 設定時間範圍 (從當前時間開始的24小時)
        now = datetime.utcnow()
        start_time = self.ts.utc(now.year, now.month, now.day, now.hour, now.minute)
        
        # 創建時間點列表
        time_points = []
        for i in range(int(24 * 60 / interval_minutes) + 1):
            time_points.append(start_time + i * (interval_minutes / 1440))
        
        # 初始化結果數據
        results = []
        visible_counts = []
        handovers = []
        last_best_sat = None
        
        # 追蹤每個時間點最佳衛星
        for t in tqdm(time_points, desc="分析24小時覆蓋度"):
            visible_sats = []
            
            for sat in self.satellites:
                # 計算衛星位置
                difference = sat - self.observer
                topocentric = difference.at(t)
                alt, az, distance = topocentric.altaz()
                
                # 若高度角 > 25度視為可見 (Starlink一般操作要求)
                if alt.degrees > 25:
                    visible_sats.append({
                        'name': sat.name, 
                        'alt': alt.degrees, 
                        'az': az.degrees,
                        'distance': distance.km,
                        'elevation_angle': alt.degrees
                    })
            
            # 記錄可見衛星數量
            visible_counts.append(len(visible_sats))
            
            # 找出最佳衛星 (高度角最高)
            best_sat = None
            if visible_sats:
                best_sat = max(visible_sats, key=lambda x: x['elevation_angle'])
                
                # 檢查handover
                if last_best_sat and best_sat['name'] != last_best_sat['name']:
                    handovers.append({
                        'time': t.utc_datetime(),
                        'from': last_best_sat['name'],
                        'to': best_sat['name'],
                        'from_alt': last_best_sat['elevation_angle'],
                        'to_alt': best_sat['elevation_angle']
                    })
            
            # 記錄結果
            results.append({
                'time': t.utc_datetime(),
                'visible_satellites': len(visible_sats),
                'best_satellite': best_sat['name'] if best_sat else None,
                'best_alt': best_sat['elevation_angle'] if best_sat else None,
                'best_az': best_sat['az'] if best_sat else None,
                'best_distance': best_sat['distance'] if best_sat else None
            })
            
            # 更新最佳衛星
            last_best_sat = best_sat
        
        # 在轉換為 DataFrame 前處理數據類型，確保一致性
        processed_results = []
        for res_dict in results:
            processed_dict = {}
            for key, value in res_dict.items():
                if isinstance(value, (np.float64, np.float32)):
                    processed_dict[key] = float(value) if value is not None else None
                elif isinstance(value, (np.int64, np.int32)):
                    processed_dict[key] = int(value) if value is not None else None
                elif value is None:
                    processed_dict[key] = None  # 或使用特定佔位符，如 np.nan 或 "N/A"
                else:
                    processed_dict[key] = value
            processed_results.append(processed_dict)

        # 轉換為DataFrame
        self.coverage_df = pd.DataFrame(processed_results)
        self.handovers_df = pd.DataFrame(handovers)
        
        # 計算統計數據
        stats = {
            'total_time_hours': 24,
            'avg_visible_satellites': np.mean(visible_counts),
            'max_visible_satellites': np.max(visible_counts),
            'min_visible_satellites': np.min(visible_counts),
            'handover_count': len(handovers),
            'avg_time_between_handovers_minutes': (24*60)/len(handovers) if handovers else 0,
            'coverage_percentage': sum(1 for x in visible_counts if x > 0) / len(visible_counts) * 100
        }
        
        # 保存結果
        self.coverage_df.to_csv(f"{self.output_dir}/satellite_coverage.csv", index=False)
        self.handovers_df.to_csv(f"{self.output_dir}/satellite_handovers.csv", index=False)
        
        with open(f"{self.output_dir}/coverage_stats.json", 'w') as f:
            json.dump(stats, f, indent=2)
        
        return stats, self.coverage_df, self.handovers_df
    
    def generate_visualizations(self):
        """生成視覺化圖表"""
        if not hasattr(self, 'coverage_df'):
            print("請先執行 analyze_24h_coverage() 來生成數據")
            return
        
        # 1. 可見衛星數量時間線圖
        plt.figure(figsize=(12, 6))
        plt.plot(self.coverage_df['time'], self.coverage_df['visible_satellites'])
        plt.title('24小時內可見Starlink衛星數量')
        plt.xlabel('時間 (UTC)')
        plt.ylabel('可見衛星數量')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/visible_satellites_timeline.png", dpi=300)
        
        # 2. 最佳衛星高度角時間線圖
        plt.figure(figsize=(12, 6))
        plt.plot(self.coverage_df['time'], self.coverage_df['best_alt'])
        plt.title('24小時內最佳衛星仰角')
        plt.xlabel('時間 (UTC)')
        plt.ylabel('仰角 (度)')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/best_satellite_elevation.png", dpi=300)
        
        # 3. Handover 時間線圖
        if not self.handovers_df.empty:
            plt.figure(figsize=(12, 6))
            for i, row in self.handovers_df.iterrows():
                plt.axvline(x=row['time'], color='r', linestyle='--', alpha=0.5)
            plt.plot(self.coverage_df['time'], self.coverage_df['best_alt'])
            plt.title('衛星Handover時間線 (紅線表示handover)')
            plt.xlabel('時間 (UTC)')
            plt.ylabel('仰角 (度)')
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/handover_timeline.png", dpi=300)
        
        # 4. 使用Plotly生成互動式熱力圖
        # 準備方位角和仰角數據矩陣
        az_bins = np.linspace(0, 360, 73)  # 5度一個bin
        el_bins = np.linspace(25, 90, 14)  # 5度一個bin
        
        # 創建一個網格計數密度
        heatmap = np.zeros((len(el_bins)-1, len(az_bins)-1))
        
        # 遍歷所有時間點
        visible_sat_positions = []
        for t in tqdm(self.ts.linspace(self.ts.utc(datetime.utcnow()), 
                                       self.ts.utc(datetime.utcnow() + timedelta(hours=24)), 
                                       360), desc="生成熱力圖資料"):
            for sat in self.satellites:
                difference = sat - self.observer
                topocentric = difference.at(t)
                alt, az, distance = topocentric.altaz()
                
                if alt.degrees > 25:
                    visible_sat_positions.append({
                        'az': az.degrees,
                        'alt': alt.degrees
                    })
        
        # 填充熱力圖
        for pos in visible_sat_positions:
            az_idx = np.digitize(pos['az'], az_bins) - 1
            el_idx = np.digitize(pos['alt'], el_bins) - 1
            if 0 <= az_idx < len(az_bins)-1 and 0 <= el_idx < len(el_bins)-1:
                heatmap[el_idx, az_idx] += 1
        
        # 創建極坐標熱力圖
        fig = go.Figure()
        
        # 調整網格中心點
        r = [(el_bins[i] + el_bins[i+1])/2 for i in range(len(el_bins)-1)]
        theta = [(az_bins[i] + az_bins[i+1])/2 for i in range(len(az_bins)-1)]
        
        # 將仰角轉換為極坐標中的半徑 (90度在中心)
        r_polar = [90 - r_val for r_val in r]
        
        # 創建熱力圖
        fig.add_trace(go.Heatmap(
            z=heatmap,
            x=theta,
            y=r,
            colorscale='Viridis',
            colorbar=dict(title='衛星出現頻率')
        ))
        
        fig.update_layout(
            title='24小時衛星覆蓋熱力圖 (方位角vs仰角)',
            xaxis_title='方位角 (度)',
            yaxis_title='仰角 (度)',
            width=800,
            height=600
        )
        
        fig.write_html(f"{self.output_dir}/coverage_heatmap.html")
        
        print(f"所有視覺化圖表已保存至 {self.output_dir} 目錄")
    
    def export_html_report(self):
        """生成HTML格式的報告"""
        if not hasattr(self, 'coverage_df'):
            print("請先執行 analyze_24h_coverage() 來生成數據")
            return
            
        with open(f"{self.output_dir}/coverage_stats.json", 'r') as f:
            stats = json.load(f)
        
        # 生成HTML報告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>台北市Starlink衛星覆蓋分析報告</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #3498db; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #3498db; color: white; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .stats {{ display: flex; flex-wrap: wrap; }}
                .stat-box {{ background-color: #ecf0f1; border-radius: 5px; padding: 15px; margin: 10px; flex: 1; min-width: 200px; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
                .stat-label {{ color: #7f8c8d; }}
                img {{ max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>台北市Starlink衛星覆蓋分析報告</h1>
                <p>分析位置: 台北市 (緯度: {TAIPEI_LAT}, 經度: {TAIPEI_LON})</p>
                <p>分析時間: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                
                <h2>24小時覆蓋統計</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{stats['avg_visible_satellites']:.1f}</div>
                        <div class="stat-label">平均可見衛星數量</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats['max_visible_satellites']}</div>
                        <div class="stat-label">最大可見衛星數量</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats['min_visible_satellites']}</div>
                        <div class="stat-label">最小可見衛星數量</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats['coverage_percentage']:.1f}%</div>
                        <div class="stat-label">衛星覆蓋百分比</div>
                    </div>
                </div>
                
                <h2>Handover統計</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{stats['handover_count']}</div>
                        <div class="stat-label">24小時內Handover次數</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats['avg_time_between_handovers_minutes']:.1f}</div>
                        <div class="stat-label">平均Handover間隔(分鐘)</div>
                    </div>
                </div>
                
                <h2>視覺化圖表</h2>
                <h3>可見衛星數量時間線</h3>
                <img src="visible_satellites_timeline.png" alt="可見衛星數量時間線">
                
                <h3>最佳衛星仰角時間線</h3>
                <img src="best_satellite_elevation.png" alt="最佳衛星仰角時間線">
                
                <h3>Handover時間線</h3>
                <img src="handover_timeline.png" alt="Handover時間線">
                
                <h3>互動式覆蓋熱力圖</h3>
                <p><a href="coverage_heatmap.html" target="_blank">開啟互動式熱力圖</a></p>
                
                <h2>Handover詳細資料</h2>
                <table>
                    <tr>
                        <th>時間 (UTC)</th>
                        <th>From衛星</th>
                        <th>To衛星</th>
                        <th>From仰角</th>
                        <th>To仰角</th>
                    </tr>
        """
        
        for _, row in self.handovers_df.iterrows():
            html_content += f"""
                    <tr>
                        <td>{row['time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                        <td>{row['from']}</td>
                        <td>{row['to']}</td>
                        <td>{row['from_alt']:.2f}°</td>
                        <td>{row['to_alt']:.2f}°</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
        </body>
        </html>
        """
        
        # 保存HTML報告
        with open(f"{self.output_dir}/starlink_coverage_report.html", 'w') as f:
            f.write(html_content)
        
        print(f"HTML報告已生成: {self.output_dir}/starlink_coverage_report.html")
        
        return f"{self.output_dir}/starlink_coverage_report.html"


if __name__ == "__main__":
    # 建立分析對象
    analyzer = StarlinkAnalysis()
    
    # 分析24小時覆蓋情況
    stats, coverage_df, handovers_df = analyzer.analyze_24h_coverage()
    
    # 生成視覺化圖表
    analyzer.generate_visualizations()
    
    # 生成HTML報告
    report_path = analyzer.export_html_report()
    
    # 輸出結果摘要
    print("\n===== 分析結果摘要 =====")
    print(f"平均可見衛星數量: {stats['avg_visible_satellites']:.1f}")
    print(f"最大可見衛星數量: {stats['max_visible_satellites']}")
    print(f"最小可見衛星數量: {stats['min_visible_satellites']}")
    print(f"衛星覆蓋百分比: {stats['coverage_percentage']:.1f}%")
    print(f"24小時內Handover次數: {stats['handover_count']}")
    print(f"平均Handover間隔: {stats['avg_time_between_handovers_minutes']:.1f}分鐘")
    print(f"詳細報告已保存至: {report_path}") 