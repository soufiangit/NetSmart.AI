#!/usr/bin/env python3
"""
SKMA-FON Monitoring Agent
Smart Kernel-Based Monitoring Agent for Fiber-Optimized Optical Networks

Author: Soufian Carson
License: MIT
"""

import os
import mmap
import struct
import json
import time
import logging
import requests
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, jsonify
import threading

# Configuration
PROC_PATH = "/proc/optifiber/myinfo"
BUFFER_SIZE = 4 * 4096  # 4 pages
NUM_SITES = 4
SITE_STRUCT_SIZE = 96  # Size of site_stats struct
UPDATE_INTERVAL = 1.0  # seconds
API_PORT = 8080

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('skma-fon-agent')

@dataclass
class SiteMetrics:
    """Site metrics data structure"""
    site_name: str
    timestamp: int
    throughput_gbps: int
    error_count: int
    ber_errors: int
    link_status: int
    utilization: float
    anomaly_score: float = 0.0
    forecast_gbps: int = 0

class KernelDataReader:
    """Handles reading data from kernel module via mmap"""
    
    def __init__(self, proc_path: str = PROC_PATH):
        self.proc_path = proc_path
        self.fd = None
        self.mapped_buffer = None
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def connect(self):
        """Connect to kernel module via mmap"""
        try:
            self.fd = os.open(self.proc_path, os.O_RDWR)
            self.mapped_buffer = mmap.mmap(self.fd, BUFFER_SIZE)
            logger.info(f"Connected to kernel module via {self.proc_path}")
        except Exception as e:
            logger.error(f"Failed to connect to kernel module: {e}")
            raise
            
    def disconnect(self):
        """Disconnect from kernel module"""
        if self.mapped_buffer:
            self.mapped_buffer.close()
        if self.fd:
            os.close(self.fd)
        logger.info("Disconnected from kernel module")
        
    def read_site_data(self, site_idx: int) -> Optional[SiteMetrics]:
        """Read data for a specific site from shared memory"""
        if not self.mapped_buffer:
            return None
            
        try:
            offset = site_idx * SITE_STRUCT_SIZE
            self.mapped_buffer.seek(offset)
            
            # Read struct data (matches kernel struct site_stats)
            raw_data = self.mapped_buffer.read(SITE_STRUCT_SIZE)
            
            # Unpack the structure
            # Format: 32s Q I I I I f 8I (site_name, timestamp, throughput, error_count, 
            #         ber_errors, link_status, utilization, reserved[8])
            unpacked = struct.unpack('32s Q I I I I f 8I', raw_data)
            
            site_name = unpacked[0].decode('utf-8').rstrip('\x00')
            timestamp = unpacked[1]
            throughput_gbps = unpacked[2]
            error_count = unpacked[3]
            ber_errors = unpacked[4]
            link_status = unpacked[5]
            utilization = unpacked[6]
            
            return SiteMetrics(
                site_name=site_name,
                timestamp=timestamp,
                throughput_gbps=throughput_gbps,
                error_count=error_count,
                ber_errors=ber_errors,
                link_status=link_status,
                utilization=utilization
            )
            
        except Exception as e:
            logger.error(f"Error reading site {site_idx} data: {e}")
            return None
            
    def read_all_sites(self) -> List[SiteMetrics]:
        """Read data for all sites"""
        sites = []
        for i in range(NUM_SITES):
            site_data = self.read_site_data(i)
            if site_data:
                sites.append(site_data)
        return sites

class AIInferenceEngine:
    """Simple AI inference for anomaly detection and forecasting"""
    
    def __init__(self):
        self.history = {}  # Store historical data for each site
        
    def update_history(self, site_metrics: SiteMetrics):
        """Update historical data for a site"""
        site_name = site_metrics.site_name
        if site_name not in self.history:
            self.history[site_name] = []
            
        self.history[site_name].append({
            'timestamp': site_metrics.timestamp,
            'throughput': site_metrics.throughput_gbps,
            'errors': site_metrics.error_count,
            'utilization': site_metrics.utilization
        })
        
        # Keep only last 60 data points (1 minute at 1s intervals)
        if len(self.history[site_name]) > 60:
            self.history[site_name] = self.history[site_name][-60:]
            
    def detect_anomaly(self, site_metrics: SiteMetrics) -> float:
        """Simple anomaly detection based on statistical thresholds"""
        site_name = site_metrics.site_name
        
        if site_name not in self.history or len(self.history[site_name]) < 10:
            return 0.0
            
        # Get recent throughput values
        recent_throughput = [d['throughput'] for d in self.history[site_name][-10:]]
        mean_throughput = np.mean(recent_throughput)
        std_throughput = np.std(recent_throughput)
        
        if std_throughput == 0:
            return 0.0
            
        # Calculate z-score
        z_score = abs(site_metrics.throughput_gbps - mean_throughput) / std_throughput
        
        # Convert to anomaly score (0-1)
        anomaly_score = min(z_score / 3.0, 1.0)  # 3-sigma rule
        
        # Check for error spikes
        if site_metrics.error_count > 10:
            anomaly_score = max(anomaly_score, 0.8)
            
        return anomaly_score
        
    def forecast_traffic(self, site_metrics: SiteMetrics) -> int:
        """Simple traffic forecasting using linear trend"""
        site_name = site_metrics.site_name
        
        if site_name not in self.history or len(self.history[site_name]) < 5:
            return site_metrics.throughput_gbps
            
        # Get recent throughput values
        recent_data = self.history[site_name][-5:]
        throughputs = [d['throughput'] for d in recent_data]
        timestamps = [d['timestamp'] for d in recent_data]
        
        # Simple linear regression
        if len(set(timestamps)) > 1:  # Avoid division by zero
            slope = (throughputs[-1] - throughputs[0]) / (timestamps[-1] - timestamps[0])
            # Forecast 15 minutes ahead (900 seconds)
            forecast = int(throughputs[-1] + slope * 900)
            return max(0, forecast)  # Ensure non-negative
        
        return site_metrics.throughput_gbps

class MonitoringAgent:
    """Main monitoring agent"""
    
    def __init__(self):
        self.running = False
        self.data_reader = None
        self.ai_engine = AIInferenceEngine()
        self.latest_metrics = []
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()
        
    def setup_flask_routes(self):
        """Setup Flask API routes"""
        @self.flask_app.route('/metrics')
        def get_metrics():
            """Return latest metrics as JSON"""
            return jsonify({
                'timestamp': int(time.time()),
                'sites': [asdict(metric) for metric in self.latest_metrics]
            })
            
        @self.flask_app.route('/health')
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'agent_running': self.running,
                'sites_monitored': len(self.latest_metrics)
            })
            
        @self.flask_app.route('/anomalies')
        def get_anomalies():
            """Return sites with high anomaly scores"""
            anomalous_sites = [
                asdict(metric) for metric in self.latest_metrics 
                if metric.anomaly_score >= 0.8
            ]
            return jsonify({
                'timestamp': int(time.time()),
                'anomalous_sites': anomalous_sites,
                'count': len(anomalous_sites)
            })
            
    def process_metrics(self, raw_metrics: List[SiteMetrics]) -> List[SiteMetrics]:
        """Process raw metrics with AI inference"""
        processed_metrics = []
        
        for metric in raw_metrics:
            # Update historical data
            self.ai_engine.update_history(metric)
            
            # Run AI inference
            metric.anomaly_score = self.ai_engine.detect_anomaly(metric)
            metric.forecast_gbps = self.ai_engine.forecast_traffic(metric)
            
            processed_metrics.append(metric)
            
        return processed_metrics
        
    def send_to_cloud(self, metrics: List[SiteMetrics]):
        """Send metrics to cloud (placeholder)"""
        # In a real implementation, this would send to InfluxDB Cloud
        try:
            payload = {
                'timestamp': int(time.time()),
                'metrics': [asdict(metric) for metric in metrics]
            }
            
            # For MVP, just log the data that would be sent
            logger.info(f"Would send to cloud: {len(metrics)} site metrics")
            
            # Check for high anomaly scores or utilization
            for metric in metrics:
                if metric.anomaly_score >= 0.8:
                    logger.warning(f"ANOMALY DETECTED: {metric.site_name} - Score: {metric.anomaly_score:.2f}")
                    
                if metric.utilization >= 90.0:
                    logger.warning(f"HIGH UTILIZATION: {metric.site_name} - {metric.utilization:.1f}%")
                    
        except Exception as e:
            logger.error(f"Error sending to cloud: {e}")
            
    def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop")
        
        try:
            with KernelDataReader() as reader:
                self.data_reader = reader
                
                while self.running:
                    try:
                        # Read raw data from kernel
                        raw_metrics = reader.read_all_sites()
                        
                        if raw_metrics:
                            # Process with AI
                            processed_metrics = self.process_metrics(raw_metrics)
                            
                            # Update latest metrics
                            self.latest_metrics = processed_metrics
                            
                            # Send to cloud
                            self.send_to_cloud(processed_metrics)
                            
                            # Log summary
                            logger.info(f"Processed {len(processed_metrics)} sites")
                            
                        time.sleep(UPDATE_INTERVAL)
                        
                    except Exception as e:
                        logger.error(f"Error in monitoring loop: {e}")
                        time.sleep(5)  # Wait before retrying
                        
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            
    def start(self):
        """Start the monitoring agent"""
        logger.info("Starting SKMA-FON Monitoring Agent")
        self.running = True
        
        # Start monitoring in separate thread
        monitoring_thread = threading.Thread(target=self.monitoring_loop)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        
        # Start Flask API
        logger.info(f"Starting API server on port {API_PORT}")
        self.flask_app.run(host='0.0.0.0', port=API_PORT, debug=False)
        
    def stop(self):
        """Stop the monitoring agent"""
        logger.info("Stopping monitoring agent")
        self.running = False

def main():
    """Main entry point"""
    agent = MonitoringAgent()
    
    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        agent.stop()

if __name__ == '__main__':
    main()