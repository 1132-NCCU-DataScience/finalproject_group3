#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多時間尺度預測服務
結合物理模型和深度學習進行衛星軌道和覆蓋率預測
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging
from pathlib import Path

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiScalePredictionService:
    """多時間尺度預測服務"""
    
    def __init__(self):
        self.prediction_horizons = {
            'short_term': {'hours': 1, 'interval_minutes': 5},    # 短期：1小時，5分鐘間隔
            'medium_term': {'hours': 24, 'interval_minutes': 30},  # 中期：24小時，30分鐘間隔
            'long_term': {'hours': 168, 'interval_minutes': 60}    # 長期：7天，1小時間隔
        }
        
        self.prediction_cache = {}
        self.model_weights = {
            'physics_model': 0.7,    # 物理模型權重
            'ml_model': 0.3          # 機器學習模型權重
        }
    
    def predict_satellite_coverage(self, 
                                 observer_lat: float, 
                                 observer_lon: float,
                                 prediction_type: str = 'medium_term',
                                 satellites_subset: Optional[List[str]] = None) -> Dict:
        """
        預測衛星覆蓋率
        
        Args:
            observer_lat: 觀測者緯度
            observer_lon: 觀測者經度
            prediction_type: 預測類型 ('short_term', 'medium_term', 'long_term')
            satellites_subset: 要分析的衛星子集
            
        Returns:
            預測結果字典
        """
        if prediction_type not in self.prediction_horizons:
            raise ValueError(f"不支援的預測類型: {prediction_type}")
        
        config = self.prediction_horizons[prediction_type]
        
        # 生成預測時間點
        start_time = datetime.now()
        time_points = []
        for i in range(0, config['hours'] * 60, config['interval_minutes']):
            time_points.append(start_time + timedelta(minutes=i))
        
        # 執行預測
        predictions = {
            'prediction_type': prediction_type,
            'start_time': start_time.isoformat(),
            'observer_location': {'lat': observer_lat, 'lon': observer_lon},
            'time_points': len(time_points),
            'predictions': []
        }
        
        for time_point in time_points:
            coverage_prediction = self._predict_coverage_at_time(
                time_point, observer_lat, observer_lon, satellites_subset
            )
            predictions['predictions'].append(coverage_prediction)
        
        # 計算統計信息
        predictions['statistics'] = self._calculate_prediction_statistics(predictions['predictions'])
        
        return predictions
    
    def _predict_coverage_at_time(self, 
                                time_point: datetime, 
                                lat: float, 
                                lon: float,
                                satellites_subset: Optional[List[str]] = None) -> Dict:
        """預測特定時間點的覆蓋情況"""
        
        # 模擬預測結果（實際實現中會調用真實的預測模型）
        base_satellites = np.random.randint(25, 50)
        time_factor = (time_point.hour % 24) / 24.0
        seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * time_point.timetuple().tm_yday / 365.25)
        
        predicted_satellites = int(base_satellites * seasonal_factor * (0.9 + 0.2 * time_factor))
        predicted_elevation = 35 + 25 * np.random.random()
        
        # 預測不確定性
        uncertainty = self._calculate_prediction_uncertainty(time_point)
        
        return {
            'timestamp': time_point.isoformat(),
            'predicted_satellites': predicted_satellites,
            'predicted_elevation': predicted_elevation,
            'coverage_probability': min(100, predicted_satellites * 2.5),
            'uncertainty': uncertainty,
            'confidence_interval': {
                'lower': max(0, predicted_satellites - uncertainty['satellites']),
                'upper': predicted_satellites + uncertainty['satellites']
            }
        }
    
    def _calculate_prediction_uncertainty(self, time_point: datetime) -> Dict:
        """計算預測不確定性"""
        now = datetime.now()
        hours_ahead = (time_point - now).total_seconds() / 3600
        
        # 不確定性隨時間增加
        base_uncertainty = 2.0
        time_factor = min(hours_ahead / 24.0, 5.0)  # 最多5倍不確定性
        
        return {
            'satellites': base_uncertainty * (1 + time_factor),
            'elevation': 2.5 * (1 + time_factor * 0.5),
            'coverage': 5.0 * (1 + time_factor * 0.3)
        }
    
    def _calculate_prediction_statistics(self, predictions: List[Dict]) -> Dict:
        """計算預測統計信息"""
        satellites_count = [p['predicted_satellites'] for p in predictions]
        elevations = [p['predicted_elevation'] for p in predictions]
        coverage_probs = [p['coverage_probability'] for p in predictions]
        
        return {
            'satellites': {
                'mean': np.mean(satellites_count),
                'max': np.max(satellites_count),
                'min': np.min(satellites_count),
                'std': np.std(satellites_count)
            },
            'elevation': {
                'mean': np.mean(elevations),
                'max': np.max(elevations),
                'min': np.min(elevations)
            },
            'coverage': {
                'mean': np.mean(coverage_probs),
                'availability_percentage': len([p for p in coverage_probs if p > 80]) / len(coverage_probs) * 100
            }
        }
    
    def predict_optimal_observation_windows(self, 
                                          observer_lat: float, 
                                          observer_lon: float,
                                          duration_hours: int = 24,
                                          min_satellites: int = 30) -> List[Dict]:
        """
        預測最佳觀測時段
        
        Args:
            observer_lat: 觀測者緯度
            observer_lon: 觀測者經度
            duration_hours: 預測時長（小時）
            min_satellites: 最少衛星數量閾值
            
        Returns:
            最佳觀測時段列表
        """
        # 預測所有時段
        predictions = self.predict_satellite_coverage(
            observer_lat, observer_lon, 'medium_term'
        )
        
        # 找出滿足條件的時段
        optimal_windows = []
        current_window = None
        
        for pred in predictions['predictions']:
            if pred['predicted_satellites'] >= min_satellites:
                if current_window is None:
                    current_window = {
                        'start_time': pred['timestamp'],
                        'end_time': pred['timestamp'],
                        'avg_satellites': pred['predicted_satellites'],
                        'max_elevation': pred['predicted_elevation'],
                        'duration_minutes': 0
                    }
                else:
                    current_window['end_time'] = pred['timestamp']
                    current_window['avg_satellites'] = (
                        current_window['avg_satellites'] + pred['predicted_satellites']
                    ) / 2
                    current_window['max_elevation'] = max(
                        current_window['max_elevation'], pred['predicted_elevation']
                    )
                    start_dt = datetime.fromisoformat(current_window['start_time'])
                    end_dt = datetime.fromisoformat(current_window['end_time'])
                    current_window['duration_minutes'] = int((end_dt - start_dt).total_seconds() / 60)
            else:
                if current_window and current_window['duration_minutes'] >= 30:  # 至少30分鐘
                    optimal_windows.append(current_window)
                current_window = None
        
        # 添加最後一個窗口
        if current_window and current_window['duration_minutes'] >= 30:
            optimal_windows.append(current_window)
        
        # 按平均衛星數量排序
        optimal_windows.sort(key=lambda x: x['avg_satellites'], reverse=True)
        
        return optimal_windows
    
    def generate_prediction_report(self, 
                                 observer_lat: float, 
                                 observer_lon: float,
                                 output_path: str = "output/prediction_report.json") -> str:
        """
        生成完整的預測報告
        
        Args:
            observer_lat: 觀測者緯度
            observer_lon: 觀測者經度
            output_path: 輸出檔案路徑
            
        Returns:
            報告檔案路徑
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'observer_location': {'lat': observer_lat, 'lon': observer_lon},
            'predictions': {}
        }
        
        # 生成各種時間尺度的預測
        for pred_type in ['short_term', 'medium_term', 'long_term']:
            print(f"生成 {pred_type} 預測...")
            report['predictions'][pred_type] = self.predict_satellite_coverage(
                observer_lat, observer_lon, pred_type
            )
        
        # 生成最佳觀測窗口
        report['optimal_windows'] = self.predict_optimal_observation_windows(
            observer_lat, observer_lon
        )
        
        # 預測趨勢分析
        report['trend_analysis'] = self._analyze_prediction_trends(report['predictions'])
        
        # 保存報告
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 自定義 JSON 編碼器處理 numpy 類型
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NumpyEncoder, self).default(obj)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        
        print(f"預測報告已保存到: {output_path}")
        return output_path
    
    def _analyze_prediction_trends(self, predictions: Dict) -> Dict:
        """分析預測趨勢"""
        trends = {}
        
        for pred_type, pred_data in predictions.items():
            if 'statistics' in pred_data:
                stats = pred_data['statistics']
                trends[pred_type] = {
                    'satellite_trend': 'stable',  # 可以根據實際數據計算趨勢
                    'coverage_quality': 'good' if stats['coverage']['mean'] > 85 else 'moderate',
                    'reliability_score': min(100, stats['satellites']['mean'] * 2),
                    'peak_performance_hours': self._find_peak_hours(pred_data['predictions'])
                }
        
        return trends
    
    def _find_peak_hours(self, predictions: List[Dict]) -> List[int]:
        """找出峰值表現小時"""
        hourly_performance = {}
        
        for pred in predictions:
            hour = datetime.fromisoformat(pred['timestamp']).hour
            if hour not in hourly_performance:
                hourly_performance[hour] = []
            hourly_performance[hour].append(pred['predicted_satellites'])
        
        # 計算每小時平均表現
        avg_performance = {
            hour: np.mean(values) for hour, values in hourly_performance.items()
        }
        
        # 找出表現最好的前3個小時
        sorted_hours = sorted(avg_performance.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]

# 全域實例
prediction_service = MultiScalePredictionService()

def get_prediction_service() -> MultiScalePredictionService:
    """獲取預測服務實例"""
    return prediction_service

if __name__ == "__main__":
    # 測試預測服務
    service = MultiScalePredictionService()
    
    # 台北位置
    taipei_lat, taipei_lon = 25.0330, 121.5654
    
    print("=== 測試多時間尺度預測 ===")
    
    # 短期預測
    short_pred = service.predict_satellite_coverage(
        taipei_lat, taipei_lon, 'short_term'
    )
    print(f"短期預測 - 預測點數: {short_pred['time_points']}")
    print(f"平均衛星數: {short_pred['statistics']['satellites']['mean']:.1f}")
    
    # 最佳觀測窗口
    windows = service.predict_optimal_observation_windows(taipei_lat, taipei_lon)
    print(f"\n找到 {len(windows)} 個最佳觀測窗口")
    for i, window in enumerate(windows[:3]):  # 顯示前3個
        print(f"窗口 {i+1}: {window['duration_minutes']} 分鐘, "
              f"平均 {window['avg_satellites']:.1f} 顆衛星")
    
    # 生成完整報告
    report_path = service.generate_prediction_report(taipei_lat, taipei_lon)
    print(f"\n完整報告已生成: {report_path}") 