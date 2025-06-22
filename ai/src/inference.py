#!/usr/bin/env python3
"""
SKMA-FON AI Inference Engine
Advanced anomaly detection and traffic forecasting for optical networks

Author: Soufian Carson
License: MIT
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import joblib
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger('skma-fon-ai')

@dataclass
class NetworkFeatures:
    """Network features for AI inference"""
    throughput_mean: float
    throughput_std: float
    throughput_trend: float
    error_rate: float
    utilization_mean: float
    utilization_trend: float
    time_of_day: float
    day_of_week: float

class AnomalyDetector:
    """Isolation Forest-based anomaly detection"""
    
    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def extract_features(self, metrics_history: List[Dict]) -> NetworkFeatures:
        """Extract features from metrics history"""
        if len(metrics_history) < 2:
            return NetworkFeatures(0, 0, 0, 0, 0, 0, 0, 0)
            
        df = pd.DataFrame(metrics_history)
        
        # Throughput features
        throughput_mean = df['throughput'].mean()
        throughput_std = df['throughput'].std()
        
        # Calculate trend (simple linear regression slope)
        if len(df) > 1:
            x = np.arange(len(df)).reshape(-1, 1)
            y = df['throughput'].values
            reg = LinearRegression().fit(x, y)
            throughput_trend = reg.coef_[0]
        else:
            throughput_trend = 0
            
        # Error rate
        total_errors = df['errors'].sum()
        error_rate = total_errors / len(df) if len(df) > 0 else 0
        
        # Utilization features
        utilization_mean = df['utilization'].mean()
        
        # Utilization trend
        if len(df) > 1:
            x = np.arange(len(df)).reshape(-1, 1)
            y = df['utilization'].values
            reg = LinearRegression().fit(x, y)
            utilization_trend = reg.coef_[0]
        else:
            utilization_trend = 0
            
        # Time-based features
        now = datetime.now()
        time_of_day = now.hour + now.minute / 60.0  # 0-24
        day_of_week = now.weekday()  # 0-6
        
        return NetworkFeatures(
            throughput_mean=throughput_mean,
            throughput_std=throughput_std,
            throughput_trend=throughput_trend,
            error_rate=error_rate,
            utilization_mean=utilization_mean,
            utilization_trend=utilization_trend,
            time_of_day=time_of_day,
            day_of_week=day_of_week
        )
        
    def train(self, training_data: List[List[Dict]]):
        """Train the anomaly detection model"""
        logger.info("Training anomaly detection model...")
        
        features_list = []
        for site_history in training_data:
            if len(site_history) > 10:  # Minimum data requirement
                features = self.extract_features(site_history)
                features_list.append([
                    features.throughput_mean,
                    features.throughput_std,
                    features.throughput_trend,
                    features.error_rate,
                    features.utilization_mean,
                    features.utilization_trend,
                    features.time_of_day,
                    features.day_of_week
                ])
                
        if len(features_list) < 10:
            logger.warning("Insufficient training data, using default thresholds")
            return False
            
        X = np.array(features_list)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True
        
        logger.info(f"Model trained with {len(features_list)} samples")
        return True
        
    def predict(self, metrics_history: List[Dict]) -> float:
        """Predict anomaly score for current metrics"""
        if not self.is_trained:
            # Fallback to simple statistical detection
            return self._simple_anomaly_detection(metrics_history)
            
        features = self.extract_features(metrics_history)
        X = np.array([[
            features.throughput_mean,
            features.throughput_std,
            features.throughput_trend,
            features.error_rate,
            features.utilization_mean,
            features.utilization_trend,
            features.time_of_day,
            features.day_of_week
        ]])
        
        X_scaled = self.scaler.transform(X)
        
        # Get anomaly score (lower = more anomalous)
        score = self.model.decision_function(X_scaled)[0]
        
        # Convert to 0-1 scale (higher = more anomalous)
        anomaly_score = max(0, min(1, (0.5 - score) * 2))
        
        return anomaly_score
        
    def _simple_anomaly_detection(self, metrics_history: List[Dict]) -> float:
        """Simple fallback anomaly detection"""
        if len(metrics_history) < 10:
            return 0.0
            
        df = pd.DataFrame(metrics_history)
        recent_throughput = df['throughput'].iloc[-5:].mean()
        historical_mean = df['throughput'].iloc[:-5].mean()
        historical_std = df['throughput'].iloc[:-5].std()
        
        if historical_std == 0:
            return 0.0
            
        z_score = abs(recent_throughput - historical_mean) / historical_std
        return min(z_score / 3.0, 1.0)
        
    def save_model(self, filepath: str):
        """Save trained model to disk"""
        if self.is_trained:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
            
    def load_model(self, filepath: str) -> bool:
        """Load trained model from disk"""
        try:
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

class TrafficForecaster:
    """LSTM-based traffic forecasting"""
    
    def __init__(self, sequence_length: int = 30):
        self.sequence_length = sequence_length
        self.scaler = StandardScaler()
        self.model = None
        self.is_trained = False
        
    def prepare_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for training/prediction"""
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:(i + self.sequence_length)])
            y.append(data[i + self.sequence_length])
        return np.array(X), np.array(y)
        
    def train(self, training_data: List[List[Dict]]):
        """Train the forecasting model (simplified for MVP)"""
        logger.info("Training traffic forecasting model...")
        
        # For MVP, use simple linear regression instead of LSTM
        from sklearn.linear_model import LinearRegression
        
        all_sequences = []
        all_targets = []
        
        for site_history in training_data:
            if len(site_history) > self.sequence_length + 10:
                df = pd.DataFrame(site_history)
                throughput_data = df['throughput'].values
                
                # Normalize data
                throughput_scaled = self.scaler.fit_transform(
                    throughput_data.reshape(-1, 1)
                ).flatten()
                
                X, y = self.prepare_sequences(throughput_scaled)
                
                # Flatten sequences for linear regression
                X_flat = X.reshape(X.shape[0], -1)
                
                all_sequences.extend(X_flat)
                all_targets.extend(y)
                
        if len(all_sequences) < 10:
            logger.warning("Insufficient training data for forecasting")
            return False
            
        self.model = LinearRegression()
        self.model.fit(all_sequences, all_targets)
        self.is_trained = True
        
        logger.info(f"Forecasting model trained with {len(all_sequences)} sequences")
        return True
        
    def predict(self, metrics_history: List[Dict], forecast_minutes: int = 15) -> int:
        """Predict traffic for specified minutes ahead"""
        if not self.is_trained or len(metrics_history) < self.sequence_length:
            # Fallback to simple trend extrapolation
            return self._simple_forecast(metrics_history, forecast_minutes)
            
        df = pd.DataFrame(metrics_history)
        recent_data = df['throughput'].iloc[-self.sequence_length:].values
        
        # Normalize
        recent_scaled = self.scaler.transform(recent_data.reshape(-1, 1)).flatten()
        
        # Prepare sequence
        X = recent_scaled.reshape(1, -1)
        
        # Predict
        predicted_scaled = self.model.predict(X)[0]
        
        # Denormalize
        predicted = self.scaler.inverse_transform([[predicted_scaled]])[0][0]
        
        return max(0, int(predicted))
        
    def _simple_forecast(self, metrics_history: List[Dict], forecast_minutes: int) -> int:
        """Simple trend-based forecasting"""
        if len(metrics_history) < 5:
            return metrics_history[-1]['throughput'] if metrics_history else 1000
            
        df = pd.DataFrame(metrics_history)
        recent_throughput = df['throughput'].iloc[-5:].values
        
        # Calculate trend
        x = np.arange(len(recent_throughput))
        slope = np.polyfit(x, recent_throughput, 1)[0]
        
        # Forecast (assuming 1-second intervals)
        forecast_points = forecast_minutes * 60
        predicted = recent_throughput[-1] + slope * forecast_points
        
        return max(0, int(predicted))

class AIInferenceService:
    """Main AI inference service"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.anomaly_detector = AnomalyDetector()
        self.traffic_forecaster = TrafficForecaster()
        self.site_histories = {}
        
        # Create models directory
        os.makedirs(models_dir, exist_ok=True)
        
        # Try to load existing models
        self.load_models()
        
    def update_site_history(self, site_name: str, metrics: Dict):
        """Update historical data for a site"""
        if site_name not in self.site_histories:
            self.site_histories[site_name] = []
            
        self.site_histories[site_name].append({
            'timestamp': metrics.get('timestamp', 0),
            'throughput': metrics.get('throughput_gbps', 0),
            'errors': metrics.get('error_count', 0),
            'utilization': metrics.get('utilization', 0)
        })
        
        # Keep only recent history (24 hours at 1-second intervals)
        max_history = 24 * 60 * 60
        if len(self.site_histories[site_name]) > max_history:
            self.site_histories[site_name] = self.site_histories[site_name][-max_history:]
            
    def detect_anomaly(self, site_name: str) -> float:
        """Detect anomaly for a site"""
        if site_name not in self.site_histories:
            return 0.0
            
        return self.anomaly_detector.predict(self.site_histories[site_name])
        
    def forecast_traffic(self, site_name: str, forecast_minutes: int = 15) -> int:
        """Forecast traffic for a site"""
        if site_name not in self.site_histories:
            return 1000  # Default value
            
        return self.traffic_forecaster.predict(
            self.site_histories[site_name], 
            forecast_minutes
        )
        
    def train_models(self):
        """Train all AI models with available data"""
        if not self.site_histories:
            logger.warning("No historical data available for training")
            return False
            
        training_data = list(self.site_histories.values())
        
        # Train anomaly detector
        anomaly_success = self.anomaly_detector.train(training_data)
        
        # Train traffic forecaster
        forecast_success = self.traffic_forecaster.train(training_data)
        
        if anomaly_success or forecast_success:
            self.save_models()
            logger.info("AI models training completed")
            return True
            
        return False
        
    def save_models(self):
        """Save trained models to disk"""
        try:
            self.anomaly_detector.save_model(
                os.path.join(self.models_dir, "anomaly_model.joblib")
            )
            
            # Save forecaster model
            if self.traffic_forecaster.is_trained:
                joblib.dump(
                    {
                        'model': self.traffic_forecaster.model,
                        'scaler': self.traffic_forecaster.scaler,
                        'sequence_length': self.traffic_forecaster.sequence_length,
                        'is_trained': self.traffic_forecaster.is_trained
                    },
                    os.path.join(self.models_dir, "forecast_model.joblib")
                )
                
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
            
    def load_models(self):
        """Load trained models from disk"""
        try:
            # Load anomaly model
            anomaly_path = os.path.join(self.models_dir, "anomaly_model.joblib")
            if os.path.exists(anomaly_path):
                self.anomaly_detector.load_model(anomaly_path)
                
            # Load forecast model
            forecast_path = os.path.join(self.models_dir, "forecast_model.joblib")
            if os.path.exists(forecast_path):
                model_data = joblib.load(forecast_path)
                self.traffic_forecaster.model = model_data['model']
                self.traffic_forecaster.scaler = model_data['scaler']
                self.traffic_forecaster.sequence_length = model_data['sequence_length']
                self.traffic_forecaster.is_trained = model_data['is_trained']
                
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")

def main():
    """Test the AI inference service"""
    ai_service = AIInferenceService()
    
    # Generate some test data
    import random
    import time
    
    sites = ['MicrosoftDC', 'Dallas', 'Dobbins', 'Stone']
    
    for i in range(100):
        for site in sites:
            metrics = {
                'timestamp': int(time.time()) + i,
                'throughput_gbps': random.randint(800, 2000),
                'error_count': random.randint(0, 5),
                'utilization': random.uniform(60, 95)
            }
            ai_service.update_site_history(site, metrics)
            
    # Train models
    ai_service.train_models()
    
    # Test inference
    for site in sites:
        anomaly_score = ai_service.detect_anomaly(site)
        forecast = ai_service.forecast_traffic(site)
        
        print(f"{site}: Anomaly={anomaly_score:.3f}, Forecast={forecast} Gbps")

if __name__ == '__main__':
    main()