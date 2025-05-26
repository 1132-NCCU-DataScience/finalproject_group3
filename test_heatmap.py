#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試熱力圖功能是否正常工作
"""

import requests
import os
import subprocess
import time

def test_heatmap():
    print("🔥 測試覆蓋率熱力圖功能")
    print("=" * 50)
    
    # 檢查文件是否存在
    heatmap_file = "app/static/coverage_heatmap.html"
    if os.path.exists(heatmap_file):
        file_size = os.path.getsize(heatmap_file)
        print(f"✅ 熱力圖文件存在: {heatmap_file}")
        print(f"📁 文件大小: {file_size / 1024:.1f} KB")
        
        # 檢查文件內容
        with open(heatmap_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '<script type="text/javascript">' in content and 'Plotly' in content:
                print("✅ 文件包含 Plotly 圖表內容")
            else:
                print("❌ 文件可能不是有效的 Plotly 圖表")
                return False
                
        # 測試通過Web訪問
        try:
            response = requests.get("http://localhost:8081/static/coverage_heatmap.html", timeout=10)
            if response.status_code == 200:
                print(f"✅ Web 訪問成功 (HTTP {response.status_code})")
                print(f"📄 響應大小: {len(response.content) / 1024:.1f} KB")
            else:
                print(f"❌ Web 訪問失敗 (HTTP {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ Web 訪問失敗: {e}")
            return False
            
    else:
        print(f"❌ 熱力圖文件不存在: {heatmap_file}")
        return False
    
    # 檢查統計數據
    stats_file = "app/static/coverage_stats.json"
    if os.path.exists(stats_file):
        print(f"✅ 統計數據文件存在: {stats_file}")
        
        # 讀取統計數據
        import json
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
            print(f"📊 平均可見衛星數: {stats.get('avg_visible_satellites', 'N/A')}")
            print(f"📊 最大可見衛星數: {stats.get('max_visible_satellites', 'N/A')}")
            print(f"📊 覆蓋率: {stats.get('coverage_percentage', 'N/A')}%")
            
            # 檢查數值是否合理
            if (stats.get('avg_visible_satellites', 0) > 0 and 
                stats.get('max_visible_satellites', 0) > 0 and
                stats.get('coverage_percentage', 0) > 0):
                print("✅ 統計數據看起來正常")
            else:
                print("❌ 統計數據異常，所有值都是 0")
                return False
    else:
        print(f"❌ 統計數據文件不存在: {stats_file}")
        return False
    
    print("-" * 50)
    print("🎉 熱力圖功能測試通過！")
    print("\n🌐 您可以訪問以下網址查看熱力圖:")
    print("   http://localhost:8081/static/coverage_heatmap.html")
    print("   或在主頁面中查看完整報告")
    
    return True

if __name__ == "__main__":
    success = test_heatmap()
    exit(0 if success else 1) 