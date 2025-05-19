#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from satellite_analysis import StarlinkAnalysis

def main():
    """重新生成台北市 Starlink 衛星覆蓋分析圖表"""
    print("開始重新生成圖表...")
    
    # 指定存檔的輸出目錄為 output/20250519_154149
    output_dir = "output/20250519_154149"
    
    # 創建分析器但不執行數據分析
    analyzer = StarlinkAnalysis(output_dir=output_dir)
    
    # 只生成可視化圖表
    print("使用既有數據生成圖表...")
    analyzer.generate_visualizations()
    
    print("圖表生成完成！請檢查目錄：" + output_dir)

if __name__ == "__main__":
    main() 