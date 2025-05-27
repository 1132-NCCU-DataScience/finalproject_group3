#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib # Import matplotlib
# Suppress Matplotlib font warnings early
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
import matplotlib.pyplot as plt
import argparse
import requests
from skyfield.api import load, wgs84, EarthSatellite, utc
from tqdm import tqdm
import plotly.express as px
import plotly.graph_objects as go
import concurrent.futures
import matplotlib.font_manager as fm
import time
import sys

# 定義台北市的經緯度常數
TAIPEI_LAT = 25.0330  # 台北市緯度
TAIPEI_LON = 121.5654  # 台北市經度
ELEVATION = 10.0  # 假設高度(公尺)

# 改進的中文字型設定
def setup_chinese_fonts():
    """設定中文字型，避免字型警告"""
    import matplotlib.font_manager as fm
    
    # 獲取系統可用的中文字型
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # 優先順序的中文字型列表
    preferred_fonts = [
        'Noto Sans CJK TC', 
        'Noto Sans CJK SC',
        'Noto Serif CJK TC',
        'Noto Serif CJK SC',
        'SimHei',
        'Microsoft YaHei',
        'DejaVu Sans'  # 備用字型
    ]
    
    # 找到第一個可用的中文字型
    selected_font = None
    for font in preferred_fonts:
        if font in available_fonts:
            selected_font = font
            break
    
    if selected_font:
        plt.rcParams['font.sans-serif'] = [selected_font]
        print(f"使用字型: {selected_font}")
    else:
        # 使用預設字型，不設定中文字型以避免警告
        print("警告: 未找到合適的中文字型，將使用系統預設字型")
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    
    plt.rcParams['axes.unicode_minus'] = False  # 解決負號顯示問題
    return selected_font

# 設定字型
chinese_font = setup_chinese_fonts()

# 定義中文文字繪製函數
def plot_with_chinese_font(title, xlabel, ylabel):
    """繪製帶英文標籤的圖表（避免字型問題）"""
    # 統一使用英文標籤以避免字型警告
    title_en = title.replace('台北市區可見 Starlink 衛星數量變化', 'Visible Starlink Satellites in Taipei')
    title_en = title_en.replace('衛星最大仰角隨時間變化', 'Maximum Satellite Elevation Over Time')
    title_en = title_en.replace('台北市區可見 Starlink 衛星數量變化 (無數據)', 'Visible Starlink Satellites in Taipei (No Data)')
    title_en = title_en.replace('衛星最大仰角隨時間變化 (無數據)', 'Maximum Satellite Elevation Over Time (No Data)')
    
    xlabel_en = xlabel.replace('時間 (分鐘)', 'Time (minutes)').replace('時間', 'Time').replace('時間點', 'Time Point')
    ylabel_en = ylabel.replace('可見衛星數量 (個)', 'Number of Visible Satellites')
    ylabel_en = ylabel_en.replace('最大仰角 (度)', 'Maximum Elevation (degrees)')
    
    plt.title(title_en)
    plt.xlabel(xlabel_en)
    plt.ylabel(ylabel_en)

# 將 process_time_point_worker 移至頂層
def process_time_point_worker(time_data_tuple, worker_tle_list_of_tuples, worker_observer_lat, worker_observer_lon, worker_observer_elev, worker_ts_init_args, min_elevation_threshold=25):
    t_skyfield, time_point_datetime = time_data_tuple # 解包時間元組
    visible_satellites = []
    
    # 從傳入的經緯度和高度重新創建觀測者位置
    observer_pos = wgs84.latlon(worker_observer_lat, worker_observer_lon, elevation_m=worker_observer_elev)

    # 重新創建 timescale 物件
    # worker_ts_init_args 應該是一個元組或字典，包含初始化 timescale 所需的參數
    # 例如，如果 ts = load.timescale()，那麼 worker_ts_init_args 可以是 None 或空字典
    # 如果 ts = load.timescale(builtin=True)，那麼 worker_ts_init_args 可以是 {'builtin': True}
    # 這裡假設 load.timescale() 不需要特定參數，如果需要，必須從調用者傳遞
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
                # 修正衛星位置計算方法
                geocentric = sat_obj.at(t_skyfield)
                subpoint = wgs84.subpoint(geocentric)
                difference = sat_obj - observer_pos
                topocentric = difference.at(t_skyfield)
                alt, az, distance = topocentric.altaz()
                
                if alt.degrees > min_elevation_threshold: # 使用傳入的仰角閾值
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
    def __init__(self, output_dir="output", progress_output=False):
        """初始化分析類別並下載最新的 TLE 數據"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.progress_output = progress_output
        
        # 初始化 skyfield 的時間尺度
        self.ts = load.timescale()
        
        # 設置觀察者位置（預設為台北市）
        self.observer = wgs84.latlon(TAIPEI_LAT, TAIPEI_LON, elevation_m=ELEVATION)
        
        # 初始化衛星列表並下載 TLE 數據
        self.satellites = []
        self.download_tle_data()
        
    def _print_progress(self, percentage, message):
        if self.progress_output:
            print(f"PROGRESS:{percentage}")
            print(f"MESSAGE:{message}")
            sys.stdout.flush() # Ensure immediate output

    def _print_output_file(self, filename):
        if self.progress_output:
            print(f"OUTPUT_FILE:{filename}")
            sys.stdout.flush()

    def set_observer_location(self, lat, lon, elevation_m=10.0):
        """設置觀察者位置"""
        self.observer = wgs84.latlon(lat, lon, elevation_m=elevation_m)
    
    def download_tle_data(self):
        """下載最新的 Starlink TLE 數據，包含重試機制和本地文件備用"""
        if self.progress_output: self._print_progress(0, "正在下載 TLE 數據...")
        print("正在下載 Starlink TLE 數據...")
        
        # 檢查是否有現有的 TLE 文件
        tle_file_path = os.path.join(self.output_dir, 'starlink_latest.tle')
        
        # TLE 數據源列表，提供備用選項
        tle_sources = [
            'https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle',
            'https://celestrak.org/NORAD/elements/supplemental/starlink.txt',
            'https://celestrak.org/NORAD/elements/starlink.txt'  # 新增的備用 URL
        ]
        
        max_retries = 3
        retry_delay = 5  # 秒
        
        # 初始化用於並行處理的原始 TLE 數據列表
        self.raw_tle_data = [] # [(name, line1, line2), ...]
        self.satellites = [] # EarthSatellite 物件列表 (如果仍需用於非並行部分)

        # 嘗試從網路下載
        download_success = False
        for source_url in tle_sources:
            for attempt in range(max_retries):
                try:
                    print(f"嘗試從 {source_url} 下載 (第 {attempt + 1} 次)")
                    
                    response = requests.get(source_url, timeout=30)
                    if response.status_code != 200:
                        raise Exception(f"HTTP {response.status_code}: {response.reason}")
                        
                    tle_data_text = response.text.strip().split('\n')
                    if len(tle_data_text) < 3: # 至少需要一個完整的 TLE (3行)
                        raise Exception("TLE 數據格式錯誤或數據不完整")
                    
                    # 解析 TLE 數據
                    parse_errors = 0
                    temp_satellites = [] # 臨時列表，用於構建 EarthSatellite
                    temp_raw_tle = []    # 臨時列表，用於構建 raw_tle_data
                    
                    for i in range(0, len(tle_data_text) -2, 3): # 確保 i+2 不越界
                        name = tle_data_text[i].strip()
                        line1 = tle_data_text[i + 1].strip()
                        line2 = tle_data_text[i + 2].strip()
                        
                        if not name or not line1 or not line2: # 跳過不完整的 TLE 條目
                            print(f"警告: 在索引 {i} 處發現不完整的 TLE 數據，已跳過。")
                            parse_errors +=1
                            continue

                        try:
                            # 創建 EarthSatellite 物件 (主要用於非並行計算或驗證)
                            satellite = EarthSatellite(line1, line2, name, self.ts)
                            temp_satellites.append(satellite)
                            # 儲存原始 TLE 元組用於並行處理
                            temp_raw_tle.append((name, line1, line2))
                        except Exception as e:
                            parse_errors += 1
                            if parse_errors <= 10:  # 只顯示前10個錯誤
                                print(f"無法解析衛星 {name}: {str(e)}")
                    
                    if parse_errors > 10:
                        print(f"... 還有 {parse_errors - 10} 個衛星解析錯誤 (已省略顯示)")
                    
                    if len(temp_satellites) < 100:  # 正常情況下應該有數百顆衛星
                        raise Exception(f"解析的衛星數量異常少: {len(temp_satellites)} 顆 ({len(temp_raw_tle)} 組 TLE 元組)")
                    
                    # 如果成功，將臨時列表賦值給實例變量
                    self.satellites = temp_satellites
                    self.raw_tle_data = temp_raw_tle

                    if self.progress_output: self._print_progress(5, f"TLE 數據下載完成 ({len(self.satellites)} 顆衛星)")
                    print(f"成功下載並解析 {len(self.satellites)} 顆 Starlink 衛星的 TLE 數據")
                    print(f"原始 TLE 元組數量: {len(self.raw_tle_data)}")
                    print(f"解析錯誤: {parse_errors} 個")
                    
                    # 保存 TLE 數據到文件 (使用原始文本)
                    with open(tle_file_path, 'w', encoding='utf-8') as f:
                        f.write(response.text) # 直接寫入原始下載的文本數據
                    
                    file_size = os.path.getsize(tle_file_path) / 1024  # KB
                    print(f"TLE 數據已保存到 {tle_file_path} ({file_size:.1f} KB)")
                    if self.progress_output: self._print_output_file(tle_file_path)
                    download_success = True
                    return  # 成功下載，退出函數
                    
                except Exception as e:
                    print(f"下載失敗: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"等待 {retry_delay} 秒後重試...")
                        time.sleep(retry_delay)
                    else:
                        print(f"從 {source_url} 下載失敗，嘗試下一個數據源")
        
        # 如果網路下載失敗，嘗試使用現有的本地文件
        if not download_success and os.path.exists(tle_file_path):
            print(f"網路下載失敗，嘗試使用現有的 TLE 文件: {tle_file_path}")
            try:
                with open(tle_file_path, 'r', encoding='utf-8') as f:
                    tle_data_text = f.read().strip().split('\n')
                
                if len(tle_data_text) < 3:
                    raise Exception("本地 TLE 文件格式錯誤或數據不完整")
                
                # 解析本地 TLE 數據
                parse_errors = 0
                temp_satellites = []
                temp_raw_tle = []
                
                for i in range(0, len(tle_data_text) -2, 3):
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
                        if parse_errors <= 10:
                            print(f"無法解析衛星 {name}: {str(e)}")
                
                if len(temp_satellites) < 100:
                    raise Exception(f"本地文件解析的衛星數量異常少: {len(temp_satellites)} 顆")
                
                # 成功解析本地文件
                self.satellites = temp_satellites
                self.raw_tle_data = temp_raw_tle
                
                file_size = os.path.getsize(tle_file_path) / 1024
                print(f"成功使用本地 TLE 文件，解析 {len(self.satellites)} 顆衛星 ({file_size:.1f} KB)")
                print(f"⚠️  注意：使用的是本地緩存的 TLE 數據，可能不是最新的")
                
                if self.progress_output: 
                    self._print_progress(5, f"使用本地 TLE 數據 ({len(self.satellites)} 顆衛星)")
                    self._print_output_file(tle_file_path)
                return
                
            except Exception as e:
                print(f"讀取本地 TLE 文件失敗: {str(e)}")
        
        # 如果所有方法都失敗
        print("錯誤: 無法從任何來源獲取 TLE 數據。")
        if self.progress_output: self._print_progress(5, "TLE 數據獲取失敗。")
        # 確保 self.satellites 和 self.raw_tle_data 為空列表，而不是未定義
        self.satellites = []
        self.raw_tle_data = []
    
    def analyze_24h_coverage(self, interval_minutes=1, analysis_duration_minutes=60, num_cpus=None, min_elevation_threshold=25):
        """分析指定時間段內的衛星覆蓋情況，使用並行處理"""
        if not self.satellites:
            print("錯誤: 衛星列表為空。請先下載 TLE 數據。")
            return pd.DataFrame()

        if self.progress_output: self._print_progress(10, f"開始分析 {analysis_duration_minutes} 分鐘的覆蓋情況...")
        print(f"開始分析 {analysis_duration_minutes} 分鐘的衛星覆蓋情況，時間間隔 {interval_minutes} 分鐘，最小仰角 {min_elevation_threshold}°...")

        start_time_dt = datetime.now(utc) # 使用 timezone-aware datetime
        num_time_points = int(analysis_duration_minutes // interval_minutes)  # 確保是整數
        time_points_dt = [start_time_dt + timedelta(minutes=i * interval_minutes) for i in range(num_time_points)]
        time_points_skyfield = [self.ts.utc(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time_points_dt]

        # 準備傳遞給 worker 的 TLE 數據 (元組列表: (name, line1, line2))
        tle_tuples_list = []
        for sat in self.satellites:
            # EarthSatellite 物件通常沒有直接的 line1, line2 屬性
            # 我們需要在下載時保存原始 TLE 行，或者從 sat.model (sgp4lib.Satrec) 中提取（如果可能）
            # 最簡單的方式是在 download_tle_data 時就保存這些信息
            # 假設 self.raw_tle_data 是一個 [(name, line1, line2), ...] 的列表
            # 現在暫時無法直接獲取，需要在 download_tle_data 中修改以儲存
            # 為了能繼續，我們假設 self.raw_tle_data 已經存在
            # 這部分需要與 download_tle_data 的修改配合
            # 我們可以從 satellite 物件中提取模型參數來重建，但不直接是 line1, line2
            # 更好的方法是確保 self.satellites 存儲的是 (name, line1, line2)
            # 或者在 download_tle_data 中創建一個平行的 self.raw_tle_data 列表

            # 由於 EarthSatellite 物件本身不存儲原始 TLE line1 和 line2
            # 我們需要在下載 TLE 時就將它們與衛星名稱一起存儲。
            # 此處假設 self.tle_tuples 已經在 __init__ 或 download_tle_data 中被正確填充
            # 例如: self.tle_tuples = [(s.name, s._sgp4_satellite.tle_line1, s._sgp4_satellite.tle_line2) for s in self.satellites]
            # 注意: _sgp4_satellite 和其屬性可能是內部實現，使用需謹慎或查找 Skyfield API 提供的正式方法
            # Skyfield 的 EarthSatellite 並不直接暴露 TLE lines。
            # 我們需要在 download_tle_data 時就將原始 TLE lines 與衛星對應起來。
            # 暫時，我們將在 download_tle_data 中增加一個 self.raw_tle_data 列表來儲存 (name, line1, line2)
            pass # 這行只是佔位符，下面會在 download_tle_data 中實現 raw_tle_data

        if not hasattr(self, 'raw_tle_data') or not self.raw_tle_data:
            print("錯誤: 原始 TLE 數據 (self.raw_tle_data) 未被正確加載。無法進行並行分析。")
            print("請檢查 download_tle_data 方法以確保其存儲 (name, line1, line2) 元組。")
            # 作為臨時解決方案，如果 raw_tle_data 不存在，則禁用並行處理
            # 這不是長久之計，但可以避免程序崩潰，並提示問題所在
            print("警告: 將退回單核處理模式。")
            num_cpus = 1 
            # 如果退回單核，我們仍然需要 EarthSatellite 物件，而不是 TLE 元組
            # 這使得問題變得複雜，最根本的解決辦法是讓 process_time_point_worker 能處理 EarthSatellite
            # 或者確保 TLE 元組能被正確傳遞並在 worker 中重建。

        # 獲取 timescale 的初始化參數，假設是空字典
        # 如果 timescale 的創建有特定參數，需要在這裡傳遞
        # 例如: ts_init_args = {'builtin': True} or {'delta_t': 0} 等
        # 預設情況下 load.timescale() 可能不需要參數或使用內建數據
        ts_init_args = {} # 假設 load.timescale() 的預設行為適用

        results = []
        if num_cpus is None:
            num_cpus = os.cpu_count()
        
        print(f"使用 {num_cpus} 個 CPU 核心進行並行計算...")

        # 將時間點元組列表與 TLE 數據列表打包
        # 注意：functools.partial 不能很好地用於ProcessPoolExecutor的序列化
        # 我們需要將所有參數都傳遞給 worker
        
        # 創建 time_data_tuples 列表
        time_data_tuples = list(zip(time_points_skyfield, time_points_dt))

        if num_cpus > 1 and hasattr(self, 'raw_tle_data') and self.raw_tle_data:
            try:
                with concurrent.futures.ProcessPoolExecutor(max_workers=num_cpus) as executor:
                    # 將固定的參數與每個時間點一起傳遞
                    # process_time_point_worker 的參數順序是:
                    # (time_data_tuple, worker_tle_list_of_tuples, worker_observer_lat, worker_observer_lon, worker_observer_elev, worker_ts_init_args, min_elevation_threshold)
                    
                    # 準備 future 列表
                    futures = [executor.submit(process_time_point_worker, 
                                              time_data, 
                                              self.raw_tle_data, # 傳遞 TLE 元組列表
                                              self.observer.latitude.degrees, 
                                              self.observer.longitude.degrees, 
                                              self.observer.elevation.m,
                                              ts_init_args, # 傳遞 timescale 初始化參數
                                              min_elevation_threshold)
                               for time_data in time_data_tuples]
                    
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        try:
                            results.append(future.result())
                        except Exception as e:
                            # 在這裡可以獲取到具體的處理時間點
                            failed_time_point_dt = time_points_dt[futures.index(future)] # 這可能不準確如果 futures 順序被打亂
                                                                                        # 更好的做法是讓 worker 返回它處理的時間點
                            print(f"處理時間點時發生錯誤 (來自 future.result()): {e}") # 這裡的時間點資訊不夠精確
                        
                        if self.progress_output:
                            progress_percentage = int(((i + 1) / len(time_points_dt)) * 80) + 10 # 10% for TLE, 80% for analysis
                            self._print_progress(progress_percentage, f"已處理 {i+1}/{len(time_points_dt)} 個時間點...")
                
                # 按時間戳排序結果，因為並行處理可能導致順序錯亂
                results.sort(key=lambda r: r.get('timestamp', ''))

            except Exception as e: # 捕獲 ProcessPoolExecutor 的潛在錯誤
                print(f"並行處理過程中發生嚴重錯誤: {e}")
                print("將嘗試使用單核處理...")
                # 如果並行失敗，退回到單核處理 (並行處理前的邏輯)
                results = [] # 清空可能的部分結果
                num_cpus = 1 # 觸發下面的單核邏輯
        
        # 如果 num_cpus 為 1 (包括並行失敗退回的情況) 或初始設定為1
        if num_cpus == 1:
            print("使用單核處理模式...")
            # 如果是單核，直接使用 self.satellites (EarthSatellite 物件列表)
            # 這意味著 process_time_point_worker 需要能同時處理 EarthSatellite 列表和 TLE 元組列表
            # 或者我們在這裡將 TLE 元組轉換回 EarthSatellite 物件 (不推薦)
            # 或者我們有兩個版本的 worker (一個用於並行，一個用於單核)
            # 目前 process_time_point_worker 已修改為接收 TLE 元組，所以我們需要傳遞 self.raw_tle_data
            # 即使在單核模式下，如果 worker 期望 TLE 元組。
            # 但如果 worker 需要 EarthSatellites，這裡就需要傳 self.satellites
            
            # 根據 process_time_point_worker 最新的簽名，它期望 worker_tle_list_of_tuples
            # 因此，即使是單核，我們也應該傳遞 self.raw_tle_data
            
            # 然而，如果沒有 self.raw_tle_data (例如在之前的警告中 num_cpus 被設為 1)
            # 這種情況下，我們必須找到一種方法來處理。
            # 最好的方法是確保 self.raw_tle_data 總是可用的。

            if not hasattr(self, 'raw_tle_data') or not self.raw_tle_data:
                 print("錯誤: 單核模式也需要 self.raw_tle_data，但其未被加載。分析中止。")
                 return pd.DataFrame() # 返回空 DataFrame

            for i, time_data in enumerate(tqdm(time_data_tuples, desc="處理時間點", unit="step", disable=self.progress_output)):
                try:
                    # 單核調用 process_time_point_worker
                    # 參數與並行版本一致
                    result = process_time_point_worker(time_data, 
                                                       self.raw_tle_data, # 傳遞 TLE 元組列表
                                                       self.observer.latitude.degrees, 
                                                       self.observer.longitude.degrees, 
                                                       self.observer.elevation.m,
                                                       ts_init_args, # 傳遞 timescale 初始化參數
                                                       min_elevation_threshold)
                    results.append(result)
                except Exception as e:
                    # 這裡可以獲取到具體的處理時間點
                    failed_time_point_dt = time_data[1] # time_data_tuple 是 (t_skyfield, time_point_datetime)
                    print(f"處理時間點 {failed_time_point_dt.strftime('%Y-%m-%d %H:%M:%S')} 時發生錯誤: {e}")
                
                if self.progress_output:
                    progress_percentage = int(((i + 1) / len(time_points_dt)) * 80) + 10
                    self._print_progress(progress_percentage, f"已處理 {i+1}/{len(time_points_dt)} 個時間點...")

        if not results:
            print("警告: 分析未產生任何結果。")
            if self.progress_output: self._print_progress(95, "分析完成，但無結果。")
            return pd.DataFrame()

        coverage_df = pd.DataFrame(results)
        if coverage_df.empty:
            print("警告: 分析結果 DataFrame 為空。")
            if self.progress_output: self._print_progress(95, "分析結果為空。")
            return coverage_df
        
        # 確保 'timestamp' 列是 datetime 對象並排序
        coverage_df['timestamp'] = pd.to_datetime(coverage_df['timestamp'])
        coverage_df = coverage_df.sort_values(by='timestamp').reset_index(drop=True)

        if self.progress_output: self._print_progress(95, "結果聚合完成。")
        print("分析完成。")
        return coverage_df
    
    def save_results(self, coverage_df=None, stats=None):
        if self.progress_output: self._print_progress(91, "正在保存結果...")
        # 保存覆蓋率數據
        if coverage_df is not None:
            csv_path = os.path.join(self.output_dir, 'coverage_data.csv')
            coverage_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"詳細數據已保存到 {csv_path}")
            if self.progress_output: self._print_output_file('coverage_data.csv')
        
        # 保存統計數據
        if stats is not None:
            stats_path = os.path.join(self.output_dir, 'coverage_stats.json')
            # Ensure all serializable types for JSON
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
            print(f"統計數據已保存到 {stats_path}")
            if self.progress_output: self._print_output_file('coverage_stats.json')
        if self.progress_output: self._print_progress(92, "結果保存完成")
    
    def generate_visualizations(self):
        if self.progress_output: self._print_progress(90, "正在生成視覺化圖表...")
        print("正在生成視覺化圖表...")
        
        # 確保覆蓋數據已載入
        if not hasattr(self, 'coverage_df') or self.coverage_df.empty:
            print("警告: 覆蓋數據為空或未載入，無法生成圖表。")
            self._generate_empty_plot("visible_satellites_timeline.png", "可見衛星數量時間序列圖 (無數據)")
            self._generate_empty_plot("elevation_timeline.png", "衛星最大仰角時間序列圖 (無數據)")
            return

        self._generate_timeline_plot(
            self.coverage_df, 
            'visible_count', 
            '可見衛星數量時間序列圖', 
            '可見衛星數量 (個)', 
            'visible_satellites_timeline.png'
        )
        self._generate_timeline_plot(
            self.coverage_df, 
            'elevation', 
            '衛星最大仰角時間序列圖', 
            '最大仰角 (度)', 
            'elevation_timeline.png'
        )
        
        # 熱力圖相關邏輯已移除
        # self._generate_heatmap(self.coverage_df)

        print("視覺化圖表生成完成。")
        if self.progress_output: self._print_progress(95, "視覺化圖表生成完成。")

    def _generate_timeline_plot(self, coverage_df, column, title, xlabel, filename):
        if self.progress_output: self._print_progress(96, f"正在生成 {title}...")
        try:
            # 檢查正確的欄位
            if column in coverage_df.columns and not coverage_df[column].isnull().all():
                plt.figure(figsize=(12, 6))
                # 創建時間索引
                time_indices = range(len(coverage_df))
                plt.plot(time_indices, coverage_df[column])
                # 使用中文字體函數
                plot_with_chinese_font(title, xlabel, 'Number of Visible Satellites')
                plt.grid(True, linestyle='--', alpha=0.7)
                
                # 設置X軸刻度，每5分鐘一個刻度
                if len(coverage_df) > 20:
                    step = max(1, len(coverage_df) // 10)  # 不超過10個刻度
                    plt.xticks(time_indices[::step])
                
                plt.tight_layout()
                timeline_plot_path = os.path.join(self.output_dir, filename)
                plt.savefig(timeline_plot_path)
                plt.close()
                print(f"{title}已保存到 {timeline_plot_path}")
                if self.progress_output: self._print_output_file(filename)
            else:
                print(f"警告：缺少 {column} 數據，無法生成 {title}")
        except Exception as e:
            print(f"生成{title}時出錯: {e}")
            import traceback
            traceback.print_exc()  # 添加詳細錯誤信息
            # 創建一個簡單的錯誤頁面
            with open(f"{self.output_dir}/{filename}", 'w') as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{title}</title>
                    <style>
                        body { 
                            font-family: 'Noto Sans TC', Arial, sans-serif; 
                            text-align: center; 
                            margin-top: 50px;
                            background-color: #f8f9fa;
                        }
                        .error-box {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 8px;
                            padding: 30px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        }}
                        h2 {{
                            color: #e74c3c;
                        }}
                    </style>
                </head>
                <body>
                    <div class="error-box">
                        <h2>{title}</h2>
                        <p>生成圖表時發生錯誤。請檢查日誌了解詳情。</p>
                        <p>錯誤信息: """ + str(e) + """</p>
                    </div>
                </body>
                </html>
                """)
        if self.progress_output: self._print_progress(97, f"{title}生成完成")

    def export_html_report(self):
        if self.progress_output: self._print_progress(98, "正在導出HTML報告...")
        # 嘗試從文件載入覆蓋率數據
        coverage_file = os.path.join(self.output_dir, 'coverage_data.csv')
        stats_file = os.path.join(self.output_dir, 'coverage_stats.json')
        
        if os.path.exists(coverage_file):
            coverage_df = pd.read_csv(coverage_file)
        else:
            # 檢查是否已執行分析
            if not hasattr(self, 'coverage_df'):
                print("請先執行分析或確保 coverage_data.csv 文件存在")
                report_path = os.path.join(self.output_dir, 'report.html') # 保持 report.html
                self._generate_empty_report(report_path)
                return report_path
            coverage_df = self.coverage_df
            
        # 載入統計數據
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        else:
            # 計算統計數據
            stats = self._calculate_stats(coverage_df)
            
        # 檢查資料是否為空
        if coverage_df.empty:
            print("警告：資料為空，無法生成 HTML 報告")
            report_path = os.path.join(self.output_dir, 'report.html') # 保持 report.html
            self._generate_empty_report(report_path)
            return report_path
            
        # 生成HTML報告
        report_path = os.path.join(self.output_dir, 'report.html') # 保持 report.html
        # _generate_html_report 不再需要 heatmap_filename 參數
        self._generate_html_report(report_path, coverage_df, stats)
        print(f"HTML報告已保存至 {report_path}")
        if self.progress_output: self._print_output_file('report.html')
        return report_path
        
    def _generate_empty_report(self, report_path):
        """生成空報告"""
        empty_html = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>台北市 Starlink 衛星覆蓋分析報告</title>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
            <style>
                body {{
                    font-family: 'Noto Sans TC', sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    color: #333;
                    background-color: #f5f7fa;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                header {{
                    background-color: #e74c3c;
                    color: white;
                    padding: 20px 0;
                    margin-bottom: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 700;
                }}
                .warning-box {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 40px auto;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    text-align: center;
                    max-width: 600px;
                }}
                .warning-icon {{
                    font-size: 60px;
                    color: #e74c3c;
                    margin-bottom: 20px;
                }}
                .warning {{
                    color: #e74c3c;
                    font-size: 1.5em;
                    font-weight: 700;
                    margin-bottom: 20px;
                }}
                .message {{
                    font-size: 1.1em;
                    color: #7f8c8d;
                }}
                footer {{
                    text-align: center;
                    margin-top: 50px;
                    padding: 20px;
                    color: #7f8c8d;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>台北市 Starlink 衛星覆蓋分析報告</h1>
                </header>

                <div class="warning-box">
                    <div class="warning-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="warning">無法生成報告</div>
                    <div class="message">分析結果為空，請檢查日誌以獲取更多信息</div>
                </div>

                <footer>
                    生成於 """ + datetime.now(utc).strftime('%Y-%m-%d %H:%M:%S') + """ · 台北市 Starlink 衛星分析系統
                </footer>
            </div>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(empty_html)
        print(f"空報告已生成至 {report_path}")
        
    def _calculate_stats(self, coverage_df):
        """從覆蓋率數據計算統計數據"""
        try:
            # 檢查使用哪個欄位來計算統計數據
            if 'visible_count' in coverage_df.columns:
                count_column = 'visible_count'
            elif 'visible_satellites' in coverage_df.columns:
                # 如果只有 visible_satellites，嘗試解析
                print("警告：使用 visible_satellites 欄位計算統計數據，這可能不準確")
                def count_satellites(sat_string):
                    try:
                        if pd.isna(sat_string) or sat_string == '':
                            return 0
                        if sat_string.startswith('[') and sat_string.endswith(']'):
                            return sat_string.count("'name':")
                        return 0
                    except:
                        return 0
                coverage_df['visible_count'] = coverage_df['visible_satellites'].apply(count_satellites)
                count_column = 'visible_count'
            else:
                raise ValueError("找不到可見衛星數量數據")
            
            stats = {
                'avg_visible_satellites': float(coverage_df[count_column].mean()),
                'max_visible_satellites': int(coverage_df[count_column].max()),
                'min_visible_satellites': int(coverage_df[count_column].min()),
                'coverage_percentage': float((coverage_df[count_column] > 0).mean() * 100)
            }
            
            # 如果有最佳仰角數據
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
                'max_elevation': 0
            }
            
    def _generate_html_report(self, report_path, coverage_df, stats):
        """生成HTML報告"""
        # 獲取輸出目錄的絕對路徑
        abs_output_dir = os.path.abspath(self.output_dir)
        
        html_content = f"""<!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>台北市 Starlink 衛星覆蓋分析報告</title>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
            <style>
                body {{
                    font-family: 'Noto Sans TC', sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    color: #333;
                    background-color: #f5f7fa;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                header {{
                    background-color: #3498db;
                    color: white;
                    padding: 20px 0;
                    margin-bottom: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 700;
                }}
                .analysis-time {{
                    margin-top: 10px;
                    font-style: italic;
                    opacity: 0.8;
                }}
                h2 {{
                    color: #2980b9;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #eee;
                    margin-top: 40px;
                    margin-bottom: 30px;
                }}
                h3 {{
                    color: #3498db;
                    margin-top: 30px;
                }}
                .stats-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background-color: #fff;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    text-align: center;
                }}
                .stat-title {{
                    font-size: 1.1em;
                    color: #555;
                    margin-bottom: 10px;
                }}
                .stat-title i {{
                    margin-right: 8px;
                    color: #3498db;
                }}
                .stat-value {{
                    font-size: 2em;
                    font-weight: 700;
                    color: #3498db;
                }}
                .visualization-container {{
                    margin-bottom: 40px;
                    padding: 20px;
                    background-color: #fff;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                }}
                .visualization-container img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 8px;
                    display: block;
                    margin: 20px auto;
                    border: 1px solid #eee;
                }}
                .analysis-params {{
                    background-color: #eef2f5;
                    border-radius: 8px;
                    padding: 15px;
                    margin-top: 20px;
                    margin-bottom: 30px;
                }}
                .param-title {{
                    font-weight: 700;
                    color: #34495e;
                    display: inline-block;
                    width: 180px;
                }}
                footer {{
                    text-align: center;
                    margin-top: 50px;
                    padding: 20px;
                    color: #7f8c8d;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>台北市 Starlink 衛星覆蓋分析報告</h1>
                    <div class="analysis-time">分析時間: {datetime.now(utc).strftime('%Y-%m-%d %H:%M:%S')} UTC</div>
                </header>
                
                <div class="analysis-params">
                    <div><span class="param-title">分析持續時間:</span> {stats.get('analysis_duration_minutes', 60)} 分鐘</div>
                    <div><span class="param-title">觀測位置:</span> 緯度 {self.observer.latitude.degrees:.4f}°, 經度 {self.observer.longitude.degrees:.4f}°</div>
                </div>
                
                <h2><i class="fas fa-chart-bar"></i> 主要統計數據</h2>
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-title"><i class="fas fa-satellite"></i> 平均可見衛星數</div>
                        <div class="stat-value">{stats.get('avg_visible_satellites', 0):.1f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title"><i class="fas fa-satellite-dish"></i> 最大可見衛星數</div>
                        <div class="stat-value">{stats.get('max_visible_satellites', 0)}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title"><i class="fas fa-satellite"></i> 最小可見衛星數</div>
                        <div class="stat-value">{stats.get('min_visible_satellites', 0)}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title"><i class="fas fa-angle-up"></i> 平均最佳仰角</div>
                        <div class="stat-value">{stats.get('avg_elevation', 0):.1f}°</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title"><i class="fas fa-angle-double-up"></i> 最大仰角</div>
                        <div class="stat-value">{stats.get('max_elevation', 0):.1f}°</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title"><i class="fas fa-signal"></i> 衛星覆蓋率</div>
                        <div class="stat-value">{stats.get('coverage_percentage', 0):.1f}%</div>
                    </div>
                </div>
                
                <h2><i class="fas fa-chart-line"></i> 視覺化結果</h2>
                
                <div class="visualization-container">
                    <h3><i class="fas fa-satellite"></i> 可見衛星數量時間線</h3>
                    <img src="./visible_satellites_timeline.png" alt="可見衛星數量時間線">
                </div>
                
                <div class="visualization-container">
                    <h3><i class="fas fa-angle-up"></i> 最佳衛星仰角時間線</h3>
                    <img src="./elevation_timeline.png" alt="最佳衛星仰角時間線">
                </div>
                
                <footer>
                    生成於 {datetime.now(utc).strftime('%Y-%m-%d %H:%M:%S')} · 台北市 Starlink 衛星分析系統
                </footer>
            </div>
        </body>
        </html>
        """
        
        with open(report_path, "w") as f:
            f.write(html_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Starlink 衛星覆蓋分析工具")
    parser.add_argument('--duration', type=int, default=60, help="分析持續時間（分鐘）")
    parser.add_argument('--interval', type=float, default=1.0, help="分析時間間隔（分鐘）")
    parser.add_argument('--lat', type=float, default=TAIPEI_LAT, help="觀察者緯度")
    parser.add_argument('--lon', type=float, default=TAIPEI_LON, help="觀察者經度")
    parser.add_argument('--elev', type=float, default=ELEVATION, help="觀察者海拔（米）")
    parser.add_argument('--min_elevation', type=float, default=25.0, help="最小衛星仰角閾值（度）")
    parser.add_argument('--output', type=str, default="output", help="輸出目錄")
    parser.add_argument('--cpu', type=int, default=None, help="用於並行處理的 CPU 核心數")
    parser.add_argument('--progress_output', action='store_true', help="啟用進度輸出到 stdout")

    args = parser.parse_args()
    
    # Import sys for stdout.flush() if progress_output is True
    if args.progress_output:
        import sys

    try:
        analyzer = StarlinkAnalysis(output_dir=args.output, progress_output=args.progress_output)
        analyzer.set_observer_location(args.lat, args.lon, args.elev)
        
        # 執行分析
        coverage_results_df = analyzer.analyze_24h_coverage(
            interval_minutes=args.interval,
            analysis_duration_minutes=args.duration,
            num_cpus=args.cpu,
            min_elevation_threshold=args.min_elevation
        )

        if not coverage_results_df.empty:
            # 計算統計數據
            stats_summary = analyzer._calculate_stats(coverage_results_df)
            # 保存結果
            analyzer.save_results(coverage_df=coverage_results_df, stats=stats_summary)
            # 生成視覺化圖表
            analyzer.generate_visualizations()
            # 導出 HTML 報告
            analyzer.export_html_report()
            if args.progress_output: analyzer._print_progress(100, "分析全部完成")
            print("✅ 分析完成！所有結果已保存在輸出目錄中。")
        else:
            if args.progress_output: analyzer._print_progress(100, "分析完成但無結果")
            print("⚠️ 分析完成，但沒有生成任何結果。請檢查 TLE 數據和分析參數。")

    except Exception as e:
        if args.progress_output:
            # Ensure progress is marked as 100 to stop polling, but message indicates error
            print("PROGRESS:100") 
            print(f"MESSAGE:分析出錯: {type(e).__name__}")
            # It's also good to print the error to stderr for app.py to catch
            print(f"❌ 分析過程中發生錯誤: {e}", file=sys.stderr)
            sys.stdout.flush()
            sys.stderr.flush()
        else:
            print(f"❌ 分析過程中發生錯誤: {e}")
        sys.exit(1) 