#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from skyfield.api import load, wgs84, EarthSatellite
from itertools import groupby

def parse_tle_data(tle_lines):
    """
    解析多行TLE數據
    """
    satellites = []
    
    # 每三行一組解析TLE
    for i in range(0, len(tle_lines), 3):
        if i+2 < len(tle_lines):
            name = tle_lines[i].strip()
            line1 = tle_lines[i+1].strip()
            line2 = tle_lines[i+2].strip()
            
            if line1.startswith('1 ') and line2.startswith('2 '):
                satellites.append(EarthSatellite(line1, line2, name))
    
    return satellites

def compute_visibility(tle_lines, lat, lon, elevation=0, interval_minutes=1, duration_hours=24, min_elevation=25):
    """
    計算特定位置的衛星可見度
    
    參數:
    tle_lines -- TLE數據行列表
    lat -- 觀測點緯度
    lon -- 觀測點經度
    elevation -- 觀測點海拔(公尺)
    interval_minutes -- 時間間隔(分鐘)
    duration_hours -- 總時長(小時)
    min_elevation -- 最小可見仰角(度)
    
    返回:
    包含可見性數據的DataFrame
    """
    # 加載天體資料
    ts = load.timescale()
    
    # 解析TLE數據
    satellites = parse_tle_data(tle_lines)
    print(f"已加載 {len(satellites)} 顆衛星")
    
    # 設定觀測點
    observer = wgs84.latlon(lat, lon, elevation)
    
    # 設定時間範圍
    now = datetime.utcnow()
    start_time = ts.utc(now.year, now.month, now.day, now.hour, now.minute)
    
    # 創建時間點列表
    time_points = []
    for i in range(int(duration_hours * 60 / interval_minutes) + 1):
        time_points.append(start_time + i * (interval_minutes / 1440))
    
    # 初始化結果列表
    results = []
    
    # 追蹤每個時間點每顆衛星
    for t in time_points:
        # 轉換為datetime格式，便於pd.DataFrame
        dt = t.utc_datetime()
        
        for sat in satellites:
            # 計算衛星位置
            difference = sat - observer
            topocentric = difference.at(t)
            alt, az, distance = topocentric.altaz()
            
            # 若仰角 > 最小可見仰角，記錄結果
            if alt.degrees > min_elevation:
                results.append({
                    'time': dt,
                    'satellite': sat.name,
                    'elev': alt.degrees,  # 仰角
                    'az': az.degrees,     # 方位角
                    'distance': distance.km,
                    'direction': get_direction(az.degrees)
                })
    
    # 轉換為DataFrame
    df = pd.DataFrame(results)
    
    # 增加天氣模擬數據
    df['rain'] = np.random.choice([0, 1], size=len(df), p=[0.8, 0.2])  # 80%無雨，20%有雨
    
    return df

def get_direction(azimuth):
    """將方位角轉換為方向名稱"""
    directions = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]
    index = round(azimuth / 45) % 8
    return directions[index]

# 測試用主函數
if __name__ == "__main__":
    # 測試代碼
    from skyfield.api import load
    
    # 下載TLE數據
    print("下載Starlink TLE數據...")
    tle_lines = load.tle_file('https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle')
    
    # 轉換為文本列表
    tle_text = []
    for sat in tle_lines:
        tle_text.append(sat.name)
        tle_text.append(sat.model.line1)
        tle_text.append(sat.model.line2)
    
    # 計算台北的可見性
    result = compute_visibility(tle_text, 25.0330, 121.5654, 10.0)
    
    print(f"計算了 {len(result)} 條可見記錄")
    print(result.head()) 