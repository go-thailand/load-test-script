#!/usr/bin/env python3
"""
Real-time Monitoring and Historical Analysis Dashboard System
=============================================================

Provides comprehensive dashboard capabilities for load testing results with:
- Real-time streaming of test metrics
- Historical trend analysis and comparison
- Interactive visualizations and drill-down capabilities
- Mobile-responsive design
- Automated alerting and threshold monitoring
- Performance baseline tracking and anomaly detection

Features:
- Live streaming dashboard during test execution
- Historical trend analysis with comparative views
- Performance baseline tracking
- Anomaly detection and alerting
- Mobile-optimized responsive design
- Export capabilities for reports
- Integration with monitoring systems
"""

import json
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
import statistics
import sqlite3
import threading
from collections import deque
import hashlib

# Optional dependencies for advanced features
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

@dataclass
class MetricPoint:
    """A single metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    
@dataclass
class AlertThreshold:
    """Alert threshold configuration"""
    metric_name: str
    operator: str  # gt, lt, eq, gte, lte
    value: float
    severity: str  # critical, warning, info
    duration: int = 0  # seconds - threshold must be breached for this duration
    
@dataclass
class Dashboard:
    """Dashboard configuration"""
    id: str
    title: str
    description: str
    layout: str  # grid, tabs, single
    widgets: List[Dict] = field(default_factory=list)
    refresh_interval: int = 30  # seconds
    auto_refresh: bool = True
    mobile_optimized: bool = True

class MetricsStorage:
    """Handles storage and retrieval of metrics data"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self.init_database()
        
        # In-memory cache for recent data
        self.cache_size = 1000
        self.metrics_cache = deque(maxlen=self.cache_size)
        self.cache_lock = threading.Lock()
    
    def init_database(self):
        """Initialize SQLite database for metrics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                tags TEXT,
                test_session_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                test_type TEXT,
                configuration TEXT,
                status TEXT DEFAULT 'running',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                baseline_value REAL NOT NULL,
                confidence_interval REAL,
                calculation_method TEXT,
                data_points INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                valid_until TEXT
            )
        ''')
        
        # Create indices for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_session ON metrics(test_session_id)')
        
        conn.commit()
        conn.close()
    
    def store_metric(self, metric: MetricPoint, test_session_id: str = None):
        """Store a single metric point"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO metrics (timestamp, metric_name, value, tags, test_session_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            metric.timestamp.isoformat(),
            metric.metric_name,
            metric.value,
            json.dumps(metric.tags),
            test_session_id
        ))
        
        conn.commit()
        conn.close()
        
        # Add to cache
        with self.cache_lock:
            self.metrics_cache.append((metric, test_session_id))
    
    def store_metrics_batch(self, metrics: List[MetricPoint], test_session_id: str = None):
        """Store multiple metrics efficiently"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = [
            (m.timestamp.isoformat(), m.metric_name, m.value, json.dumps(m.tags), test_session_id)
            for m in metrics
        ]
        
        cursor.executemany('''
            INSERT INTO metrics (timestamp, metric_name, value, tags, test_session_id)
            VALUES (?, ?, ?, ?, ?)
        ''', data)
        
        conn.commit()
        conn.close()
        
        # Add to cache
        with self.cache_lock:
            for metric in metrics:
                self.metrics_cache.append((metric, test_session_id))
    
    def get_metrics(self, metric_name: str = None, start_time: datetime = None, 
                   end_time: datetime = None, test_session_id: str = None,
                   limit: int = None) -> List[MetricPoint]:
        """Retrieve metrics with filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT timestamp, metric_name, value, tags FROM metrics WHERE 1=1"
        params = []
        
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if test_session_id:
            query += " AND test_session_id = ?"
            params.append(test_session_id)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metrics.append(MetricPoint(
                timestamp=datetime.fromisoformat(row[0]),
                metric_name=row[1],
                value=row[2],
                tags=json.loads(row[3]) if row[3] else {}
            ))
        
        return metrics
    
    def get_recent_metrics(self, metric_name: str = None, minutes: int = 60) -> List[MetricPoint]:
        """Get recent metrics from cache or database"""
        start_time = datetime.now() - timedelta(minutes=minutes)
        return self.get_metrics(metric_name=metric_name, start_time=start_time)

class BaselineTracker:
    """Tracks performance baselines and detects anomalies"""
    
    def __init__(self, storage: MetricsStorage):
        self.storage = storage
        self.baselines = {}
        self.load_baselines()
    
    def load_baselines(self):
        """Load existing baselines from storage"""
        conn = sqlite3.connect(self.storage.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT metric_name, baseline_value, confidence_interval, calculation_method
            FROM baselines WHERE valid_until > datetime('now') OR valid_until IS NULL
        ''')
        
        for row in cursor.fetchall():
            self.baselines[row[0]] = {
                'value': row[1],
                'confidence_interval': row[2],
                'method': row[3]
            }
        
        conn.close()
    
    def calculate_baseline(self, metric_name: str, days_back: int = 30) -> Dict:
        """Calculate baseline for a metric using historical data"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        metrics = self.storage.get_metrics(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time
        )
        
        if len(metrics) < 10:
            return None  # Insufficient data
        
        values = [m.value for m in metrics]
        
        baseline = {
            'value': statistics.mean(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'confidence_interval': statistics.stdev(values) * 1.96 if len(values) > 1 else 0,  # 95% CI
            'data_points': len(values),
            'method': 'mean_with_confidence_interval',
            'calculated_at': datetime.now()
        }
        
        # Store baseline
        self.store_baseline(metric_name, baseline)
        self.baselines[metric_name] = baseline
        
        return baseline
    
    def store_baseline(self, metric_name: str, baseline: Dict):
        """Store baseline in database"""
        conn = sqlite3.connect(self.storage.db_path)
        cursor = conn.cursor()
        
        # Set expiry for 30 days from now
        valid_until = (datetime.now() + timedelta(days=30)).isoformat()
        
        cursor.execute('''
            INSERT INTO baselines (metric_name, baseline_value, confidence_interval, 
                                 calculation_method, data_points, valid_until)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            metric_name,
            baseline['value'],
            baseline['confidence_interval'],
            baseline['method'],
            baseline['data_points'],
            valid_until
        ))
        
        conn.commit()
        conn.close()
    
    def detect_anomalies(self, metric_name: str, current_value: float) -> Dict:
        """Detect if current value is an anomaly compared to baseline"""
        if metric_name not in self.baselines:
            baseline = self.calculate_baseline(metric_name)
            if not baseline:
                return {"is_anomaly": False, "reason": "insufficient_data"}
        else:
            baseline = self.baselines[metric_name]
        
        deviation = abs(current_value - baseline['value'])
        threshold = baseline['confidence_interval']
        
        is_anomaly = deviation > threshold
        severity = "high" if deviation > threshold * 2 else "medium" if is_anomaly else "low"
        
        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "deviation": deviation,
            "threshold": threshold,
            "baseline_value": baseline['value'],
            "current_value": current_value,
            "confidence_interval": baseline['confidence_interval']
        }

class RealTimeDashboard:
    """Real-time dashboard for streaming metrics"""
    
    def __init__(self, storage: MetricsStorage, baseline_tracker: BaselineTracker):
        self.storage = storage
        self.baseline_tracker = baseline_tracker
        self.alert_thresholds = {}
        self.active_alerts = {}
        self.subscribers = set()
        
        # Dashboard configurations
        self.dashboards = {}
        self.initialize_default_dashboards()
        
        # Real-time data streams
        self.live_streams = {}
        self.stream_buffers = {}
        
        # Flask app for web interface
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            self.setup_flask_routes()
        
    def initialize_default_dashboards(self):
        """Initialize default dashboard configurations"""
        
        # Executive Dashboard
        self.dashboards["executive"] = Dashboard(
            id="executive",
            title="Executive Dashboard",
            description="High-level overview for executives",
            layout="grid",
            widgets=[
                {
                    "id": "kpi_summary",
                    "type": "kpi_cards",
                    "title": "Key Performance Indicators",
                    "metrics": ["avg_fps", "concurrent_streams", "system_health_score"],
                    "position": {"row": 0, "col": 0, "width": 12, "height": 3}
                },
                {
                    "id": "performance_trend",
                    "type": "line_chart",
                    "title": "Performance Trend (24h)",
                    "metrics": ["avg_fps", "cpu_usage"],
                    "timespan": "24h",
                    "position": {"row": 1, "col": 0, "width": 8, "height": 6}
                },
                {
                    "id": "alert_summary",
                    "type": "alert_list",
                    "title": "Active Alerts",
                    "max_items": 5,
                    "position": {"row": 1, "col": 8, "width": 4, "height": 6}
                },
                {
                    "id": "capacity_gauge",
                    "type": "gauge",
                    "title": "System Capacity",
                    "metric": "system_utilization",
                    "position": {"row": 2, "col": 0, "width": 6, "height": 4}
                },
                {
                    "id": "availability",
                    "type": "uptime",
                    "title": "System Availability",
                    "timespan": "30d",
                    "position": {"row": 2, "col": 6, "width": 6, "height": 4}
                }
            ],
            refresh_interval=30
        )
        
        # Technical Dashboard
        self.dashboards["technical"] = Dashboard(
            id="technical",
            title="Technical Dashboard",
            description="Detailed technical metrics for engineers",
            layout="grid",
            widgets=[
                {
                    "id": "system_metrics",
                    "type": "multi_line_chart",
                    "title": "System Resource Utilization",
                    "metrics": ["cpu_usage", "memory_usage", "network_io", "disk_io"],
                    "timespan": "4h",
                    "position": {"row": 0, "col": 0, "width": 12, "height": 6}
                },
                {
                    "id": "stream_performance",
                    "type": "scatter_plot",
                    "title": "Individual Stream Performance",
                    "x_metric": "camera_id",
                    "y_metric": "avg_fps",
                    "color_metric": "reconnections",
                    "position": {"row": 1, "col": 0, "width": 8, "height": 6}
                },
                {
                    "id": "error_analysis",
                    "type": "heatmap",
                    "title": "Error Patterns",
                    "metrics": ["error_count_by_type"],
                    "position": {"row": 1, "col": 8, "width": 4, "height": 6}
                },
                {
                    "id": "latency_distribution",
                    "type": "histogram",
                    "title": "Response Time Distribution",
                    "metric": "response_time",
                    "bins": 20,
                    "position": {"row": 2, "col": 0, "width": 6, "height": 4}
                },
                {
                    "id": "throughput_analysis",
                    "type": "area_chart",
                    "title": "Data Throughput",
                    "metrics": ["bytes_per_second", "frames_per_second"],
                    "position": {"row": 2, "col": 6, "width": 6, "height": 4}
                }
            ],
            refresh_interval=15
        )
        
        # Operations Dashboard
        self.dashboards["operations"] = Dashboard(
            id="operations",
            title="Operations Dashboard",
            description="Real-time operational monitoring",
            layout="grid",
            widgets=[
                {
                    "id": "live_status",
                    "type": "status_board",
                    "title": "Live System Status",
                    "services": ["camera_service", "streaming_service", "database", "monitoring"],
                    "position": {"row": 0, "col": 0, "width": 6, "height": 4}
                },
                {
                    "id": "alert_timeline",
                    "type": "timeline",
                    "title": "Alert Timeline (24h)",
                    "timespan": "24h",
                    "position": {"row": 0, "col": 6, "width": 6, "height": 4}
                },
                {
                    "id": "real_time_metrics",
                    "type": "live_line_chart",
                    "title": "Real-time Performance",
                    "metrics": ["avg_fps", "active_streams", "cpu_usage"],
                    "timespan": "1h",
                    "position": {"row": 1, "col": 0, "width": 12, "height": 6}
                },
                {
                    "id": "top_issues",
                    "type": "issue_list",
                    "title": "Top Issues",
                    "max_items": 10,
                    "position": {"row": 2, "col": 0, "width": 8, "height": 6}
                },
                {
                    "id": "sla_status",
                    "type": "sla_tracker",
                    "title": "SLA Status",
                    "sla_targets": {"uptime": 99.9, "response_time": 2000, "error_rate": 0.1},
                    "position": {"row": 2, "col": 8, "width": 4, "height": 6}
                }
            ],
            refresh_interval=10
        )
    
    def setup_flask_routes(self):
        """Setup Flask routes for web interface"""
        
        @self.app.route('/')
        def index():
            return self.render_dashboard("executive")
        
        @self.app.route('/dashboard/<dashboard_id>')
        def dashboard(dashboard_id):
            return self.render_dashboard(dashboard_id)
        
        @self.app.route('/api/metrics/<metric_name>')
        def get_metric_data(metric_name):
            minutes = request.args.get('minutes', 60, type=int)
            metrics = self.storage.get_recent_metrics(metric_name, minutes)
            
            return jsonify({
                "metric_name": metric_name,
                "data": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "value": m.value,
                        "tags": m.tags
                    }
                    for m in metrics
                ]
            })
        
        @self.app.route('/api/dashboard/<dashboard_id>/config')
        def get_dashboard_config(dashboard_id):
            if dashboard_id in self.dashboards:
                return jsonify(asdict(self.dashboards[dashboard_id]))
            return jsonify({"error": "Dashboard not found"}), 404
        
        @self.app.route('/api/alerts')
        def get_alerts():
            return jsonify({
                "active_alerts": list(self.active_alerts.values()),
                "alert_count": len(self.active_alerts)
            })
        
        @self.app.route('/api/baselines/<metric_name>')
        def get_baseline(metric_name):
            if metric_name in self.baseline_tracker.baselines:
                return jsonify(self.baseline_tracker.baselines[metric_name])
            
            # Calculate new baseline
            baseline = self.baseline_tracker.calculate_baseline(metric_name)
            return jsonify(baseline) if baseline else jsonify({"error": "Insufficient data"}), 404
        
        # WebSocket events for real-time updates
        @self.socketio.on('connect')
        def handle_connect():
            print(f"Client connected: {request.sid}")
            self.subscribers.add(request.sid)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"Client disconnected: {request.sid}")
            self.subscribers.discard(request.sid)
        
        @self.socketio.on('subscribe_metric')
        def handle_subscribe(data):
            metric_name = data.get('metric_name')
            if metric_name:
                if metric_name not in self.live_streams:
                    self.live_streams[metric_name] = set()
                self.live_streams[metric_name].add(request.sid)
    
    def render_dashboard(self, dashboard_id: str) -> str:
        """Render dashboard HTML"""
        if dashboard_id not in self.dashboards:
            return f"<h1>Dashboard '{dashboard_id}' not found</h1>"
        
        dashboard = self.dashboards[dashboard_id]
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{dashboard.title}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
            <style>
                {self._get_dashboard_css()}
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <header class="dashboard-header">
                    <h1>{dashboard.title}</h1>
                    <div class="dashboard-controls">
                        <button onclick="toggleAutoRefresh()">Auto Refresh: ON</button>
                        <select onchange="changeDashboard(this.value)">
                            <option value="executive">Executive</option>
                            <option value="technical">Technical</option>
                            <option value="operations">Operations</option>
                        </select>
                    </div>
                </header>
                
                <main class="dashboard-grid" id="dashboard-grid">
                    {self._render_widgets(dashboard.widgets)}
                </main>
            </div>
            
            <script>
                {self._get_dashboard_javascript(dashboard)}
            </script>
        </body>
        </html>
        """
        
        return html
    
    def _get_dashboard_css(self) -> str:
        """Get CSS styles for dashboard"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        
        .dashboard-container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .dashboard-header {
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .dashboard-controls {
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        
        .dashboard-controls button, .dashboard-controls select {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            background: #3498db;
            color: white;
            cursor: pointer;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1rem;
            padding: 2rem;
            flex: 1;
        }
        
        .widget {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 1rem;
            display: flex;
            flex-direction: column;
        }
        
        .widget-title {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 1rem;
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 0.5rem;
        }
        
        .widget-content {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .kpi-card {
            text-align: center;
            padding: 1rem;
            border-radius: 6px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0.5rem;
        }
        
        .kpi-value {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        
        .kpi-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        
        .status-healthy { background: #27ae60; }
        .status-warning { background: #f39c12; }
        .status-critical { background: #e74c3c; }
        
        .alert-item {
            padding: 0.5rem;
            border-left: 4px solid #e74c3c;
            background: #fff5f5;
            margin-bottom: 0.5rem;
            border-radius: 4px;
        }
        
        .alert-item.warning {
            border-left-color: #f39c12;
            background: #fffbf0;
        }
        
        .alert-item.info {
            border-left-color: #3498db;
            background: #f0f8ff;
        }
        
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
                padding: 1rem;
            }
            
            .dashboard-header {
                flex-direction: column;
                gap: 1rem;
            }
            
            .widget {
                min-height: 200px;
            }
        }
        """
    
    def _render_widgets(self, widgets: List[Dict]) -> str:
        """Render dashboard widgets"""
        html = ""
        
        for widget in widgets:
            position = widget.get("position", {})
            style = f"""
                grid-column: {position.get('col', 0) + 1} / span {position.get('width', 6)};
                grid-row: {position.get('row', 0) + 1} / span {position.get('height', 4)};
            """
            
            widget_html = f"""
            <div class="widget" style="{style}" id="widget-{widget['id']}">
                <div class="widget-title">{widget['title']}</div>
                <div class="widget-content" id="content-{widget['id']}">
                    {self._render_widget_content(widget)}
                </div>
            </div>
            """
            
            html += widget_html
        
        return html
    
    def _render_widget_content(self, widget: Dict) -> str:
        """Render content for a specific widget type"""
        widget_type = widget.get("type", "text")
        
        if widget_type == "kpi_cards":
            return self._render_kpi_cards(widget)
        elif widget_type == "line_chart":
            return f'<div id="chart-{widget["id"]}" style="width:100%;height:100%;"></div>'
        elif widget_type == "gauge":
            return f'<div id="gauge-{widget["id"]}" style="width:100%;height:100%;"></div>'
        elif widget_type == "status_board":
            return self._render_status_board(widget)
        elif widget_type == "alert_list":
            return self._render_alert_list(widget)
        else:
            return f'<div>Widget type "{widget_type}" not implemented</div>'
    
    def _render_kpi_cards(self, widget: Dict) -> str:
        """Render KPI cards widget"""
        metrics = widget.get("metrics", [])
        
        # Get latest values for each metric
        cards_html = ""
        for metric in metrics:
            recent_metrics = self.storage.get_recent_metrics(metric, minutes=5)
            value = recent_metrics[0].value if recent_metrics else 0
            
            cards_html += f"""
            <div class="kpi-card">
                <div class="kpi-value" id="kpi-{metric}">{value:.1f}</div>
                <div class="kpi-label">{metric.replace('_', ' ').title()}</div>
            </div>
            """
        
        return f'<div style="display: flex; flex-wrap: wrap; width: 100%;">{cards_html}</div>'
    
    def _render_status_board(self, widget: Dict) -> str:
        """Render status board widget"""
        services = widget.get("services", [])
        
        status_html = ""
        for service in services:
            # Determine service status (simplified)
            status = "healthy"  # In real implementation, check actual service status
            
            status_html += f"""
            <div style="margin-bottom: 1rem;">
                <span class="status-indicator status-{status}"></span>
                <strong>{service.replace('_', ' ').title()}</strong>
                <div style="margin-left: 1.5rem; font-size: 0.9rem; color: #666;">
                    Status: {status.title()}
                </div>
            </div>
            """
        
        return status_html
    
    def _render_alert_list(self, widget: Dict) -> str:
        """Render alert list widget"""
        max_items = widget.get("max_items", 5)
        
        # Get recent alerts (simplified)
        alerts_html = ""
        for i, alert in enumerate(list(self.active_alerts.values())[:max_items]):
            severity = alert.get("severity", "info")
            
            alerts_html += f"""
            <div class="alert-item {severity}">
                <strong>{alert.get('title', 'Alert')}</strong>
                <div style="font-size: 0.9rem; margin-top: 0.25rem;">
                    {alert.get('message', 'No details available')}
                </div>
            </div>
            """
        
        if not alerts_html:
            alerts_html = '<div style="text-align: center; color: #666;">No active alerts</div>'
        
        return alerts_html
    
    def _get_dashboard_javascript(self, dashboard: Dashboard) -> str:
        """Get JavaScript for dashboard functionality"""
        return f"""
        let socket = io();
        let autoRefresh = true;
        let refreshInterval = {dashboard.refresh_interval * 1000};
        
        // Connect to WebSocket
        socket.on('connect', function() {{
            console.log('Connected to server');
            
            // Subscribe to metrics for widgets
            {self._generate_metric_subscriptions(dashboard.widgets)}
        }});
        
        // Handle real-time metric updates
        socket.on('metric_update', function(data) {{
            updateWidget(data.metric_name, data.value, data.timestamp);
        }});
        
        // Initialize charts
        {self._generate_chart_initialization(dashboard.widgets)}
        
        // Auto-refresh functionality
        function toggleAutoRefresh() {{
            autoRefresh = !autoRefresh;
            document.querySelector('.dashboard-controls button').textContent = 
                'Auto Refresh: ' + (autoRefresh ? 'ON' : 'OFF');
        }}
        
        function changeDashboard(dashboardId) {{
            window.location.href = '/dashboard/' + dashboardId;
        }}
        
        function updateWidget(metricName, value, timestamp) {{
            // Update KPI cards
            const kpiElement = document.getElementById('kpi-' + metricName);
            if (kpiElement) {{
                kpiElement.textContent = value.toFixed(1);
            }}
            
            // Update charts
            updateCharts(metricName, value, timestamp);
        }}
        
        function updateCharts(metricName, value, timestamp) {{
            // Chart update logic would go here
            console.log('Updating chart for', metricName, value);
        }}
        
        // Refresh data periodically
        if (autoRefresh) {{
            setInterval(function() {{
                if (autoRefresh) {{
                    refreshDashboard();
                }}
            }}, refreshInterval);
        }}
        
        function refreshDashboard() {{
            // Fetch latest data for all widgets
            {self._generate_refresh_logic(dashboard.widgets)}
        }}
        
        // Initial data load
        refreshDashboard();
        """
    
    def _generate_metric_subscriptions(self, widgets: List[Dict]) -> str:
        """Generate JavaScript for metric subscriptions"""
        subscriptions = []
        
        for widget in widgets:
            if "metrics" in widget:
                for metric in widget["metrics"]:
                    subscriptions.append(f"socket.emit('subscribe_metric', {{metric_name: '{metric}'}});")
            elif "metric" in widget:
                subscriptions.append(f"socket.emit('subscribe_metric', {{metric_name: '{widget['metric']}'}});")
        
        return "\n            ".join(subscriptions)
    
    def _generate_chart_initialization(self, widgets: List[Dict]) -> str:
        """Generate JavaScript for chart initialization"""
        init_code = []
        
        for widget in widgets:
            if widget.get("type") in ["line_chart", "multi_line_chart"]:
                init_code.append(f"""
                // Initialize {widget['id']} chart
                Plotly.newPlot('chart-{widget['id']}', [], {{
                    title: '{widget['title']}',
                    responsive: true
                }});
                """)
            elif widget.get("type") == "gauge":
                init_code.append(f"""
                // Initialize {widget['id']} gauge
                var gaugeData = [{{
                    type: "indicator",
                    mode: "gauge+number",
                    value: 0,
                    gauge: {{
                        axis: {{ range: [null, 100] }},
                        bar: {{ color: "darkblue" }},
                        steps: [
                            {{ range: [0, 50], color: "lightgray" }},
                            {{ range: [50, 85], color: "gray" }}
                        ],
                        threshold: {{
                            line: {{ color: "red", width: 4 }},
                            thickness: 0.75,
                            value: 90
                        }}
                    }}
                }}];
                
                Plotly.newPlot('gauge-{widget['id']}', gaugeData, {{
                    responsive: true
                }});
                """)
        
        return "\n        ".join(init_code)
    
    def _generate_refresh_logic(self, widgets: List[Dict]) -> str:
        """Generate JavaScript for dashboard refresh"""
        refresh_code = []
        
        for widget in widgets:
            if "metrics" in widget:
                for metric in widget["metrics"]:
                    refresh_code.append(f"""
                    fetch('/api/metrics/{metric}?minutes=60')
                        .then(response => response.json())
                        .then(data => updateChartData('{widget['id']}', data));
                    """)
        
        return "\n            ".join(refresh_code)
    
    def add_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None, 
                  test_session_id: str = None):
        """Add a new metric point and broadcast to subscribers"""
        metric = MetricPoint(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            tags=tags or {}
        )
        
        # Store in database
        self.storage.store_metric(metric, test_session_id)
        
        # Check for anomalies
        anomaly_result = self.baseline_tracker.detect_anomalies(metric_name, value)
        if anomaly_result["is_anomaly"]:
            self._trigger_anomaly_alert(metric_name, value, anomaly_result)
        
        # Check alert thresholds
        self._check_alert_thresholds(metric_name, value)
        
        # Broadcast to real-time subscribers
        self._broadcast_metric_update(metric)
    
    def _broadcast_metric_update(self, metric: MetricPoint):
        """Broadcast metric update to WebSocket subscribers"""
        if FLASK_AVAILABLE and hasattr(self, 'socketio'):
            self.socketio.emit('metric_update', {
                'metric_name': metric.metric_name,
                'value': metric.value,
                'timestamp': metric.timestamp.isoformat(),
                'tags': metric.tags
            })
    
    def _check_alert_thresholds(self, metric_name: str, value: float):
        """Check if metric value breaches any alert thresholds"""
        if metric_name in self.alert_thresholds:
            threshold = self.alert_thresholds[metric_name]
            
            is_breach = False
            if threshold.operator == "gt" and value > threshold.value:
                is_breach = True
            elif threshold.operator == "lt" and value < threshold.value:
                is_breach = True
            elif threshold.operator == "gte" and value >= threshold.value:
                is_breach = True
            elif threshold.operator == "lte" and value <= threshold.value:
                is_breach = True
            elif threshold.operator == "eq" and value == threshold.value:
                is_breach = True
            
            if is_breach:
                self._trigger_threshold_alert(metric_name, value, threshold)
    
    def _trigger_anomaly_alert(self, metric_name: str, value: float, anomaly_result: Dict):
        """Trigger alert for detected anomaly"""
        alert_id = f"anomaly_{metric_name}_{int(time.time())}"
        
        alert = {
            "id": alert_id,
            "type": "anomaly",
            "metric_name": metric_name,
            "title": f"Anomaly detected in {metric_name}",
            "message": f"Value {value:.2f} deviates significantly from baseline {anomaly_result['baseline_value']:.2f}",
            "severity": anomaly_result["severity"],
            "timestamp": datetime.now().isoformat(),
            "data": anomaly_result
        }
        
        self.active_alerts[alert_id] = alert
        self._broadcast_alert(alert)
    
    def _trigger_threshold_alert(self, metric_name: str, value: float, threshold: AlertThreshold):
        """Trigger alert for threshold breach"""
        alert_id = f"threshold_{metric_name}_{int(time.time())}"
        
        alert = {
            "id": alert_id,
            "type": "threshold",
            "metric_name": metric_name,
            "title": f"Threshold breach: {metric_name}",
            "message": f"Value {value:.2f} {threshold.operator} {threshold.value}",
            "severity": threshold.severity,
            "timestamp": datetime.now().isoformat(),
            "threshold": asdict(threshold)
        }
        
        self.active_alerts[alert_id] = alert
        self._broadcast_alert(alert)
    
    def _broadcast_alert(self, alert: Dict):
        """Broadcast alert to subscribers"""
        if FLASK_AVAILABLE and hasattr(self, 'socketio'):
            self.socketio.emit('alert', alert)
    
    def add_alert_threshold(self, threshold: AlertThreshold):
        """Add a new alert threshold"""
        self.alert_thresholds[threshold.metric_name] = threshold
    
    def start_web_server(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Start the web server for dashboards"""
        if not FLASK_AVAILABLE:
            raise ImportError("Flask and Flask-SocketIO required for web dashboard")
        
        print(f"Starting dashboard server on http://{host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)
    
    def export_historical_data(self, metric_name: str, start_time: datetime, 
                             end_time: datetime, format: str = "csv") -> str:
        """Export historical data for analysis"""
        metrics = self.storage.get_metrics(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time
        )
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "metric_name", "value", "tags"])
            
            for metric in metrics:
                writer.writerow([
                    metric.timestamp.isoformat(),
                    metric.metric_name,
                    metric.value,
                    json.dumps(metric.tags)
                ])
            
            return output.getvalue()
        
        elif format == "json":
            return json.dumps([
                {
                    "timestamp": m.timestamp.isoformat(),
                    "metric_name": m.metric_name,
                    "value": m.value,
                    "tags": m.tags
                }
                for m in metrics
            ], indent=2)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_performance_report(self, start_time: datetime, end_time: datetime) -> Dict:
        """Generate comprehensive performance report"""
        # Get all metrics in time range
        all_metrics = self.storage.get_metrics(start_time=start_time, end_time=end_time)
        
        # Group metrics by name
        metrics_by_name = {}
        for metric in all_metrics:
            if metric.metric_name not in metrics_by_name:
                metrics_by_name[metric.metric_name] = []
            metrics_by_name[metric.metric_name].append(metric.value)
        
        # Calculate statistics
        report = {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_hours": (end_time - start_time).total_seconds() / 3600
            },
            "metrics_summary": {},
            "anomalies_detected": 0,
            "alerts_triggered": len(self.active_alerts),
            "data_points": len(all_metrics)
        }
        
        for metric_name, values in metrics_by_name.items():
            if values:
                report["metrics_summary"][metric_name] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "range": max(values) - min(values)
                }
        
        return report
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old metrics data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        conn = sqlite3.connect(self.storage.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logging.info(f"Cleaned up {deleted_count} old metric records")
        return deleted_count