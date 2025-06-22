#!/usr/bin/env python3
"""
SKMA-FON Cloud API Service
REST API for ingesting and serving optical network monitoring data

Author: Soufian Carson
License: MIT
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dataclasses import dataclass, asdict
import sqlite3
import threading
from contextlib import contextmanager

# Configuration
API_PORT = 5000
DB_PATH = "skma_fon.db"
RETENTION_DAYS = 30

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('skma-fon-api')

@dataclass
class MetricRecord:
    """Database record for metrics"""
    id: Optional[int] = None
    timestamp: int = 0
    site_name: str = ""
    throughput_gbps: int = 0
    error_count: int = 0
    ber_errors: int = 0
    link_status: int = 1
    utilization: float = 0.0
    anomaly_score: float = 0.0
    forecast_gbps: int = 0

class DatabaseManager:
    """SQLite database manager for storing metrics"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
        
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    site_name TEXT NOT NULL,
                    throughput_gbps INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    ber_errors INTEGER NOT NULL,
                    link_status INTEGER NOT NULL,
                    utilization REAL NOT NULL,
                    anomaly_score REAL NOT NULL DEFAULT 0.0,
                    forecast_gbps INTEGER NOT NULL DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON metrics(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_site_timestamp 
                ON metrics(site_name, timestamp)
            """)
            
            conn.commit()
            logger.info("Database initialized")
            
    def insert_metrics(self, metrics: List[MetricRecord]):
        """Insert multiple metric records"""
        with self.get_connection() as conn:
            for metric in metrics:
                conn.execute("""
                    INSERT INTO metrics (
                        timestamp, site_name, throughput_gbps, error_count,
                        ber_errors, link_status, utilization, anomaly_score, forecast_gbps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.timestamp, metric.site_name, metric.throughput_gbps,
                    metric.error_count, metric.ber_errors, metric.link_status,
                    metric.utilization, metric.anomaly_score, metric.forecast_gbps
                ))
            conn.commit()
            
    def get_latest_metrics(self, limit: int = 100) -> List[MetricRecord]:
        """Get latest metrics for all sites"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM metrics 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            records = []
            for row in cursor.fetchall():
                records.append(MetricRecord(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    site_name=row['site_name'],
                    throughput_gbps=row['throughput_gbps'],
                    error_count=row['error_count'],
                    ber_errors=row['ber_errors'],
                    link_status=row['link_status'],
                    utilization=row['utilization'],
                    anomaly_score=row['anomaly_score'],
                    forecast_gbps=row['forecast_gbps']
                ))
            return records
            
    def get_site_metrics(self, site_name: str, hours: int = 24) -> List[MetricRecord]:
        """Get metrics for a specific site"""
        start_time = int(time.time()) - (hours * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM metrics 
                WHERE site_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (site_name, start_time))
            
            records = []
            for row in cursor.fetchall():
                records.append(MetricRecord(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    site_name=row['site_name'],
                    throughput_gbps=row['throughput_gbps'],
                    error_count=row['error_count'],
                    ber_errors=row['ber_errors'],
                    link_status=row['link_status'],
                    utilization=row['utilization'],
                    anomaly_score=row['anomaly_score'],
                    forecast_gbps=row['forecast_gbps']
                ))
            return records
            
    def get_anomalies(self, threshold: float = 0.8, hours: int = 24) -> List[MetricRecord]:
        """Get anomalous metrics"""
        start_time = int(time.time()) - (hours * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM metrics 
                WHERE anomaly_score >= ? AND timestamp >= ?
                ORDER BY anomaly_score DESC, timestamp DESC
            """, (threshold, start_time))
            
            records = []
            for row in cursor.fetchall():
                records.append(MetricRecord(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    site_name=row['site_name'],
                    throughput_gbps=row['throughput_gbps'],
                    error_count=row['error_count'],
                    ber_errors=row['ber_errors'],
                    link_status=row['link_status'],
                    utilization=row['utilization'],
                    anomaly_score=row['anomaly_score'],
                    forecast_gbps=row['forecast_gbps']
                ))
            return records
            
    def cleanup_old_data(self):
        """Remove old data beyond retention period"""
        cutoff_time = int(time.time()) - (RETENTION_DAYS * 24 * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM metrics WHERE timestamp < ?
            """, (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old records")

class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alert_thresholds = {
            'anomaly_score': 0.8,
            'utilization': 90.0,
            'error_rate': 10
        }
        self.recent_alerts = []
        
    def check_alerts(self, metrics: List[MetricRecord]) -> List[Dict]:
        """Check for alert conditions"""
        alerts = []
        
        for metric in metrics:
            # Anomaly alert
            if metric.anomaly_score >= self.alert_thresholds['anomaly_score']:
                alerts.append({
                    'type': 'anomaly',
                    'site': metric.site_name,
                    'severity': 'high',
                    'message': f"Anomaly detected at {metric.site_name} (score: {metric.anomaly_score:.2f})",
                    'timestamp': metric.timestamp,
                    'value': metric.anomaly_score
                })
                
            # High utilization alert
            if metric.utilization >= self.alert_thresholds['utilization']:
                alerts.append({
                    'type': 'utilization',
                    'site': metric.site_name,
                    'severity': 'warning',
                    'message': f"High utilization at {metric.site_name} ({metric.utilization:.1f}%)",
                    'timestamp': metric.timestamp,
                    'value': metric.utilization
                })
                
            # Error count alert
            if metric.error_count >= self.alert_thresholds['error_rate']:
                alerts.append({
                    'type': 'errors',
                    'site': metric.site_name,
                    'severity': 'medium',
                    'message': f"High error count at {metric.site_name} ({metric.error_count} errors)",
                    'timestamp': metric.timestamp,
                    'value': metric.error_count
                })
                
        # Store recent alerts
        self.recent_alerts.extend(alerts)
        
        # Keep only recent alerts (last hour)
        cutoff_time = int(time.time()) - 3600
        self.recent_alerts = [
            alert for alert in self.recent_alerts 
            if alert['timestamp'] >= cutoff_time
        ]
        
        return alerts
        
    def get_recent_alerts(self, hours: int = 1) -> List[Dict]:
        """Get recent alerts"""
        cutoff_time = int(time.time()) - (hours * 3600)
        return [
            alert for alert in self.recent_alerts 
            if alert['timestamp'] >= cutoff_time
        ]

def create_app():
    """Create Flask application"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for dashboard
    
    # Initialize components
    db_manager = DatabaseManager()
    alert_manager = AlertManager()
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': int(time.time()),
            'version': '1.0.0'
        })
        
    @app.route('/api/metrics', methods=['POST'])
    def ingest_metrics():
        """Ingest metrics from monitoring agent"""
        try:
            data = request.get_json()
            
            if not data or 'sites' not in data:
                return jsonify({'error': 'Invalid data format'}), 400
                
            # Convert to metric records
            records = []
            for site_data in data['sites']:
                record = MetricRecord(
                    timestamp=site_data.get('timestamp', int(time.time())),
                    site_name=site_data.get('site_name', ''),
                    throughput_gbps=site_data.get('throughput_gbps', 0),
                    error_count=site_data.get('error_count', 0),
                    ber_errors=site_data.get('ber_errors', 0),
                    link_status=site_data.get('link_status', 1),
                    utilization=site_data.get('utilization', 0.0),
                    anomaly_score=site_data.get('anomaly_score', 0.0),
                    forecast_gbps=site_data.get('forecast_gbps', 0)
                )
                records.append(record)
                
            # Store in database
            db_manager.insert_metrics(records)
            
            # Check for alerts
            alerts = alert_manager.check_alerts(records)
            
            # Log alerts
            for alert in alerts:
                logger.warning(f"ALERT: {alert['message']}")
                
            return jsonify({
                'status': 'success',
                'records_processed': len(records),
                'alerts_generated': len(alerts)
            })
            
        except Exception as e:
            logger.error(f"Error ingesting metrics: {e}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/metrics')
    def get_metrics():
        """Get latest metrics"""
        try:
            limit = request.args.get('limit', 100, type=int)
            records = db_manager.get_latest_metrics(limit)
            
            return jsonify({
                'timestamp': int(time.time()),
                'metrics': [asdict(record) for record in records]
            })
            
        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/sites/<site_name>/metrics')
    def get_site_metrics(site_name):
        """Get metrics for a specific site"""
        try:
            hours = request.args.get('hours', 24, type=int)
            records = db_manager.get_site_metrics(site_name, hours)
            
            return jsonify({
                'site': site_name,
                'hours': hours,
                'metrics': [asdict(record) for record in records]
            })
            
        except Exception as e:
            logger.error(f"Error retrieving site metrics: {e}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/anomalies')
    def get_anomalies():
        """Get anomalous metrics"""
        try:
            threshold = request.args.get('threshold', 0.8, type=float)
            hours = request.args.get('hours', 24, type=int)
            
            records = db_manager.get_anomalies(threshold, hours)
            
            return jsonify({
                'threshold': threshold,
                'hours': hours,
                'anomalies': [asdict(record) for record in records]
            })
            
        except Exception as e:
            logger.error(f"Error retrieving anomalies: {e}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/alerts')
    def get_alerts():
        """Get recent alerts"""
        try:
            hours = request.args.get('hours', 1, type=int)
            alerts = alert_manager.get_recent_alerts(hours)
            
            return jsonify({
                'hours': hours,
                'alerts': alerts
            })
            
        except Exception as e:
            logger.error(f"Error retrieving alerts: {e}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/sites')
    def get_sites():
        """Get list of monitored sites"""
        try:
            # Get distinct site names from recent data
            with db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT site_name, 
                           MAX(timestamp) as last_seen,
                           COUNT(*) as record_count
                    FROM metrics 
                    WHERE timestamp >= ?
                    GROUP BY site_name
                    ORDER BY last_seen DESC
                """, (int(time.time()) - 86400,))  # Last 24 hours
                
                sites = []
                for row in cursor.fetchall():
                    sites.append({
                        'name': row['site_name'],
                        'last_seen': row['last_seen'],
                        'record_count': row['record_count']
                    })
                    
            return jsonify({
                'sites': sites,
                'count': len(sites)
            })
            
        except Exception as e:
            logger.error(f"Error retrieving sites: {e}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/')
    def dashboard():
        """Serve dashboard page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SKMA-FON Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .metric-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
                .metric-value { font-size: 2em; font-weight: bold; color: #27ae60; }
                .alert { background: #e74c3c; color: white; padding: 10px; margin: 5px 0; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>SKMA-FON Monitoring Dashboard</h1>
                <p>Smart Kernel-Based Monitoring Agent for Fiber-Optimized Optical Networks</p>
            </div>
            
            <div id="dashboard">
                <p>Loading dashboard...</p>
            </div>
            
            <script>
                function loadDashboard() {
                    fetch('/api/metrics?limit=20')
                        .then(response => response.json())
                        .then(data => {
                            updateDashboard(data.metrics);
                        })
                        .catch(error => {
                            document.getElementById('dashboard').innerHTML = 
                                '<p style="color: red;">Error loading data: ' + error + '</p>';
                        });
                }
                
                function updateDashboard(metrics) {
                    if (!metrics || metrics.length === 0) {
                        document.getElementById('dashboard').innerHTML = 
                            '<p>No metrics available. Make sure the monitoring agent is running.</p>';
                        return;
                    }
                    
                    // Group metrics by site
                    const sites = {};
                    metrics.forEach(metric => {
                        if (!sites[metric.site_name]) {
                            sites[metric.site_name] = [];
                        }
                        sites[metric.site_name].push(metric);
                    });
                    
                    let html = '<div class="metrics">';
                    
                    Object.keys(sites).forEach(siteName => {
                        const latestMetric = sites[siteName][0]; // Most recent
                        const timestamp = new Date(latestMetric.timestamp * 1000).toLocaleString();
                        
                        html += `
                            <div class="metric-card">
                                <h3>${siteName}</h3>
                                <div class="metric-value">${latestMetric.throughput_gbps} Gbps</div>
                                <p>Utilization: ${latestMetric.utilization.toFixed(1)}%</p>
                                <p>Errors: ${latestMetric.error_count}</p>
                                <p>Anomaly Score: ${latestMetric.anomaly_score.toFixed(3)}</p>
                                <p>Forecast: ${latestMetric.forecast_gbps} Gbps</p>
                                <small>Last updated: ${timestamp}</small>
                                ${latestMetric.anomaly_score >= 0.8 ? '<div class="alert">ANOMALY DETECTED!</div>' : ''}
                                ${latestMetric.utilization >= 90 ? '<div class="alert">HIGH UTILIZATION!</div>' : ''}
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    document.getElementById('dashboard').innerHTML = html;
                }
                
                // Load dashboard initially and refresh every 5 seconds
                loadDashboard();
                setInterval(loadDashboard, 5000);
            </script>
        </body>
        </html>
        """
        
    return app

def cleanup_worker(db_manager):
    """Background worker for cleanup tasks"""
    while True:
        try:
            time.sleep(3600)  # Run every hour
            db_manager.cleanup_old_data()
        except Exception as e:
            logger.error(f"Cleanup worker error: {e}")

def main():
    """Main entry point"""
    app = create_app()
    
    # Start cleanup worker
    db_manager = DatabaseManager()
    cleanup_thread = threading.Thread(target=cleanup_worker, args=(db_manager,))
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    logger.info(f"Starting SKMA-FON Cloud API on port {API_PORT}")
    app.run(host='0.0.0.0', port=API_PORT, debug=False)

if __name__ == '__main__':
    main()