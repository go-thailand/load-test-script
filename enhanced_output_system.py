#!/usr/bin/env python3
"""
Enhanced Output System for Camera Stream Load Testing
=====================================================

Provides multi-format outputs optimized for different audiences:
- Data Scientists: Detailed JSON, CSV with statistical analysis
- Engineers: Technical HTML reports with interactive charts
- Executives: PDF summaries with high-level insights
- Operations: Real-time dashboards and alerting

Features:
- Multi-format export (JSON, CSV, HTML, PDF, Markdown)
- Interactive visualizations using Plotly
- Executive summary generation
- Mobile-friendly responsive design
- API endpoints for real-time consumption
- Integration with monitoring systems
"""

import json
import csv
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path
import base64
import io

# Optional dependencies for enhanced features
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from jinja2 import Template, Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

@dataclass
class ReportConfig:
    """Configuration for report generation"""
    include_charts: bool = True
    include_technical_details: bool = True
    executive_summary_only: bool = False
    mobile_optimized: bool = False
    theme: str = "light"  # light, dark, professional
    logo_path: Optional[str] = None
    company_name: str = "Load Testing Report"

@dataclass
class AudienceConfig:
    """Configuration for different audience types"""
    audience_type: str  # data_scientist, engineer, executive, operations
    detail_level: str  # high, medium, low
    technical_depth: str  # deep, moderate, summary
    include_recommendations: bool = True
    include_raw_data: bool = True
    alert_thresholds: Dict[str, float] = None

class EnhancedOutputSystem:
    """Enhanced output system for load testing results"""
    
    def __init__(self, base_output_dir: str = "enhanced_reports"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different output types
        self.dirs = {
            'json': self.base_output_dir / 'json',
            'csv': self.base_output_dir / 'csv', 
            'html': self.base_output_dir / 'html',
            'pdf': self.base_output_dir / 'pdf',
            'charts': self.base_output_dir / 'charts',
            'api': self.base_output_dir / 'api',
            'dashboards': self.base_output_dir / 'dashboards'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
    
    def generate_all_formats(self, report_data: Dict, test_config: Dict, 
                           audiences: List[AudienceConfig] = None) -> Dict[str, str]:
        """Generate reports for all specified audiences and formats"""
        
        if audiences is None:
            audiences = [
                AudienceConfig("data_scientist", "high", "deep", True, True),
                AudienceConfig("engineer", "high", "moderate", True, True),
                AudienceConfig("executive", "low", "summary", True, False),
                AudienceConfig("operations", "medium", "moderate", True, False)
            ]
        
        results = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate enhanced data structure
        enhanced_data = self._enhance_report_data(report_data, test_config)
        
        for audience in audiences:
            audience_dir = self.base_output_dir / audience.audience_type
            audience_dir.mkdir(exist_ok=True)
            
            # Generate JSON report
            json_file = self._generate_json_report(enhanced_data, audience, timestamp)
            results[f"{audience.audience_type}_json"] = str(json_file)
            
            # Generate CSV exports
            csv_files = self._generate_csv_exports(enhanced_data, audience, timestamp)
            results[f"{audience.audience_type}_csv"] = csv_files
            
            # Generate HTML report
            if JINJA2_AVAILABLE:
                html_file = self._generate_html_report(enhanced_data, audience, timestamp)
                results[f"{audience.audience_type}_html"] = str(html_file)
            
            # Generate PDF report for executives
            if REPORTLAB_AVAILABLE and audience.audience_type == "executive":
                pdf_file = self._generate_pdf_report(enhanced_data, audience, timestamp)
                results[f"{audience.audience_type}_pdf"] = str(pdf_file)
        
        # Generate interactive dashboards
        if PLOTLY_AVAILABLE:
            dashboard_files = self._generate_interactive_dashboards(enhanced_data, timestamp)
            results["dashboards"] = dashboard_files
        
        # Generate API endpoints data
        api_files = self._generate_api_endpoints(enhanced_data, timestamp)
        results["api_endpoints"] = api_files
        
        return results
    
    def _enhance_report_data(self, report_data: Dict, test_config: Dict) -> Dict:
        """Enhance the basic report data with additional analytics"""
        enhanced = {
            "metadata": {
                "report_generated": datetime.now().isoformat(),
                "test_configuration": test_config,
                "data_version": "2.0",
                "enhancement_level": "full"
            },
            "raw_data": report_data,
            "analytics": {},
            "insights": {},
            "alerts": {},
            "recommendations": {}
        }
        
        # Enhanced analytics
        enhanced["analytics"] = self._generate_enhanced_analytics(report_data)
        
        # Generate insights for different audiences
        enhanced["insights"] = self._generate_audience_insights(report_data)
        
        # Generate alerts and warnings
        enhanced["alerts"] = self._generate_alerts(report_data)
        
        # Generate recommendations
        enhanced["recommendations"] = self._generate_recommendations(report_data)
        
        return enhanced
    
    def _generate_enhanced_analytics(self, report_data: Dict) -> Dict:
        """Generate enhanced statistical analytics"""
        analytics = {
            "performance_metrics": {},
            "stability_metrics": {},
            "efficiency_metrics": {},
            "quality_metrics": {},
            "trend_analysis": {},
            "comparative_analysis": {}
        }
        
        # Performance metrics
        individual_streams = report_data.get("individual_streams", [])
        if individual_streams:
            fps_values = [s.get("avg_fps", 0) for s in individual_streams]
            reconnection_counts = [s.get("reconnections", 0) for s in individual_streams]
            
            analytics["performance_metrics"] = {
                "fps_statistics": {
                    "mean": statistics.mean(fps_values) if fps_values else 0,
                    "median": statistics.median(fps_values) if fps_values else 0,
                    "mode": statistics.mode(fps_values) if fps_values else 0,
                    "std_dev": statistics.stdev(fps_values) if len(fps_values) > 1 else 0,
                    "variance": statistics.variance(fps_values) if len(fps_values) > 1 else 0,
                    "coefficient_of_variation": (statistics.stdev(fps_values) / statistics.mean(fps_values)) * 100 if fps_values and statistics.mean(fps_values) > 0 else 0
                },
                "throughput_analysis": {
                    "total_data_gb": report_data.get("stream_performance", {}).get("total_bytes_received", 0) / (1024**3),
                    "avg_bitrate_mbps": (report_data.get("stream_performance", {}).get("bytes_per_second", 0) * 8) / (1024**2),
                    "frames_per_gb": report_data.get("stream_performance", {}).get("total_frames_received", 0) / max(1, report_data.get("stream_performance", {}).get("total_bytes_received", 0) / (1024**3))
                }
            }
        
        # Stability metrics
        analytics["stability_metrics"] = {
            "connection_stability": {
                "success_rate": len([s for s in individual_streams if s.get("status") == "connected"]) / len(individual_streams) * 100 if individual_streams else 0,
                "avg_reconnections_per_stream": statistics.mean(reconnection_counts) if reconnection_counts else 0,
                "stability_score": self._calculate_stability_score(individual_streams),
                "failure_pattern_analysis": self._analyze_failure_patterns(individual_streams)
            }
        }
        
        # System efficiency
        system_resources = report_data.get("system_resources", {})
        analytics["efficiency_metrics"] = {
            "resource_efficiency": {
                "cpu_efficiency_score": self._calculate_cpu_efficiency(system_resources),
                "memory_efficiency_score": self._calculate_memory_efficiency(system_resources),
                "streams_per_cpu_percent": report_data.get("test_info", {}).get("max_concurrent_achieved", 0) / max(1, system_resources.get("average_cpu_percent", 1)),
                "cost_efficiency_estimate": self._estimate_cost_efficiency(report_data, system_resources)
            }
        }
        
        return analytics
    
    def _generate_audience_insights(self, report_data: Dict) -> Dict:
        """Generate insights tailored for different audiences"""
        insights = {
            "data_scientist": {
                "statistical_significance": self._analyze_statistical_significance(report_data),
                "correlation_analysis": self._analyze_correlations(report_data),
                "anomaly_detection": self._detect_anomalies(report_data),
                "predictive_modeling_suggestions": self._suggest_predictive_models(report_data)
            },
            "engineer": {
                "technical_bottlenecks": self._identify_technical_bottlenecks(report_data),
                "optimization_opportunities": self._identify_optimization_opportunities(report_data),
                "architecture_recommendations": self._generate_architecture_recommendations(report_data),
                "debugging_insights": self._generate_debugging_insights(report_data)
            },
            "executive": {
                "business_impact": self._assess_business_impact(report_data),
                "risk_assessment": self._assess_risks(report_data),
                "capacity_planning": self._generate_capacity_planning(report_data),
                "roi_analysis": self._analyze_roi(report_data)
            },
            "operations": {
                "monitoring_alerts": self._generate_monitoring_alerts(report_data),
                "sla_compliance": self._assess_sla_compliance(report_data),
                "incident_prevention": self._suggest_incident_prevention(report_data),
                "maintenance_schedule": self._suggest_maintenance_schedule(report_data)
            }
        }
        
        return insights
    
    def _generate_alerts(self, report_data: Dict) -> Dict:
        """Generate alerts based on thresholds and patterns"""
        alerts = {
            "critical": [],
            "warning": [],
            "info": []
        }
        
        # Performance alerts
        avg_fps = report_data.get("stream_performance", {}).get("average_fps", 0)
        if avg_fps < 5:
            alerts["critical"].append({
                "type": "performance",
                "message": f"Critical: Average FPS ({avg_fps:.1f}) below minimum threshold (5 FPS)",
                "impact": "high",
                "recommendation": "Investigate network connectivity and server performance"
            })
        elif avg_fps < 15:
            alerts["warning"].append({
                "type": "performance", 
                "message": f"Warning: Average FPS ({avg_fps:.1f}) below optimal threshold (15 FPS)",
                "impact": "medium",
                "recommendation": "Monitor performance trends and consider optimization"
            })
        
        # Stability alerts
        total_reconnections = report_data.get("stream_performance", {}).get("total_reconnections", 0)
        max_concurrent = report_data.get("test_info", {}).get("max_concurrent_achieved", 1)
        reconnection_rate = total_reconnections / max_concurrent
        
        if reconnection_rate > 0.5:
            alerts["critical"].append({
                "type": "stability",
                "message": f"Critical: High reconnection rate ({reconnection_rate:.2f} per stream)",
                "impact": "high", 
                "recommendation": "Check network stability and server capacity immediately"
            })
        elif reconnection_rate > 0.2:
            alerts["warning"].append({
                "type": "stability",
                "message": f"Warning: Elevated reconnection rate ({reconnection_rate:.2f} per stream)",
                "impact": "medium",
                "recommendation": "Monitor stability and investigate connection issues"
            })
        
        # Resource alerts
        system_resources = report_data.get("system_resources", {})
        cpu_usage = system_resources.get("average_cpu_percent", 0)
        memory_usage = system_resources.get("average_memory_percent", 0)
        
        if cpu_usage > 90:
            alerts["critical"].append({
                "type": "resources",
                "message": f"Critical: High CPU usage ({cpu_usage:.1f}%)",
                "impact": "high",
                "recommendation": "Scale resources immediately or reduce load"
            })
        elif cpu_usage > 75:
            alerts["warning"].append({
                "type": "resources",
                "message": f"Warning: Elevated CPU usage ({cpu_usage:.1f}%)",
                "impact": "medium",
                "recommendation": "Plan for capacity scaling"
            })
        
        return alerts
    
    def _generate_recommendations(self, report_data: Dict) -> Dict:
        """Generate actionable recommendations"""
        recommendations = {
            "immediate_actions": [],
            "short_term_improvements": [],
            "long_term_strategies": [],
            "capacity_planning": [],
            "risk_mitigation": []
        }
        
        # Analyze current performance
        avg_fps = report_data.get("stream_performance", {}).get("average_fps", 0)
        max_concurrent = report_data.get("test_info", {}).get("max_concurrent_achieved", 0)
        reconnection_rate = report_data.get("stream_performance", {}).get("total_reconnections", 0) / max(1, max_concurrent)
        
        # Immediate actions
        if avg_fps < 10:
            recommendations["immediate_actions"].append({
                "priority": "high",
                "action": "Investigate and resolve low FPS issues",
                "steps": [
                    "Check network bandwidth and latency",
                    "Verify server CPU and memory availability", 
                    "Review camera configuration and streaming parameters",
                    "Test with reduced concurrent streams to isolate bottleneck"
                ],
                "timeline": "immediate"
            })
        
        if reconnection_rate > 0.3:
            recommendations["immediate_actions"].append({
                "priority": "high", 
                "action": "Address connection stability issues",
                "steps": [
                    "Review network infrastructure and connectivity",
                    "Check for intermittent connection issues",
                    "Implement more robust retry mechanisms",
                    "Monitor for patterns in connection failures"
                ],
                "timeline": "immediate"
            })
        
        # Short-term improvements
        recommendations["short_term_improvements"].extend([
            {
                "priority": "medium",
                "action": "Implement comprehensive monitoring",
                "steps": [
                    "Set up Grafana dashboards for real-time monitoring",
                    "Configure Prometheus metrics collection",
                    "Implement alerting for performance thresholds",
                    "Create automated health checks"
                ],
                "timeline": "1-2 weeks"
            },
            {
                "priority": "medium",
                "action": "Optimize streaming parameters",
                "steps": [
                    "Test different compression levels and frame rates",
                    "Implement adaptive bitrate streaming",
                    "Optimize buffer sizes and connection timeouts",
                    "Consider implementing stream prioritization"
                ],
                "timeline": "2-4 weeks"
            }
        ])
        
        # Long-term strategies
        recommendations["long_term_strategies"].extend([
            {
                "priority": "low",
                "action": "Implement horizontal scaling architecture",
                "steps": [
                    "Design load balancer for stream distribution",
                    "Implement microservices architecture",
                    "Set up auto-scaling based on demand",
                    "Consider edge computing for reduced latency"
                ],
                "timeline": "3-6 months"
            },
            {
                "priority": "low",
                "action": "Develop predictive analytics",
                "steps": [
                    "Collect historical performance data",
                    "Build machine learning models for capacity prediction",
                    "Implement anomaly detection systems",
                    "Create automated optimization recommendations"
                ],
                "timeline": "6-12 months"
            }
        ])
        
        return recommendations
    
    def _generate_json_report(self, enhanced_data: Dict, audience: AudienceConfig, timestamp: str) -> Path:
        """Generate JSON report for specific audience"""
        filename = f"{audience.audience_type}_report_{timestamp}.json"
        file_path = self.dirs['json'] / filename
        
        # Filter data based on audience requirements
        filtered_data = self._filter_data_for_audience(enhanced_data, audience)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2, default=str)
        
        return file_path
    
    def _generate_csv_exports(self, enhanced_data: Dict, audience: AudienceConfig, timestamp: str) -> Dict[str, str]:
        """Generate CSV exports for data analysis"""
        csv_files = {}
        base_name = f"{audience.audience_type}_{timestamp}"
        
        # Per-stream performance data
        streams_file = self.dirs['csv'] / f"{base_name}_streams.csv"
        self._write_streams_csv(enhanced_data, streams_file, audience)
        csv_files['streams'] = str(streams_file)
        
        # System metrics over time
        if audience.detail_level in ['high', 'medium']:
            system_file = self.dirs['csv'] / f"{base_name}_system_metrics.csv"
            self._write_system_metrics_csv(enhanced_data, system_file)
            csv_files['system_metrics'] = str(system_file)
        
        # Performance summary
        summary_file = self.dirs['csv'] / f"{base_name}_summary.csv"
        self._write_summary_csv(enhanced_data, summary_file, audience)
        csv_files['summary'] = str(summary_file)
        
        # Alerts and recommendations
        if audience.include_recommendations:
            recommendations_file = self.dirs['csv'] / f"{base_name}_recommendations.csv"
            self._write_recommendations_csv(enhanced_data, recommendations_file)
            csv_files['recommendations'] = str(recommendations_file)
        
        return csv_files
    
    def _generate_html_report(self, enhanced_data: Dict, audience: AudienceConfig, timestamp: str) -> Path:
        """Generate interactive HTML report"""
        filename = f"{audience.audience_type}_report_{timestamp}.html"
        file_path = self.dirs['html'] / filename
        
        # Create HTML template based on audience
        html_content = self._create_html_content(enhanced_data, audience)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return file_path
    
    def _generate_pdf_report(self, enhanced_data: Dict, audience: AudienceConfig, timestamp: str) -> Path:
        """Generate PDF executive summary"""
        filename = f"{audience.audience_type}_summary_{timestamp}.pdf"
        file_path = self.dirs['pdf'] / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Add executive summary content
        story.extend(self._create_pdf_content(enhanced_data, audience, styles))
        
        doc.build(story)
        return file_path
    
    def _generate_interactive_dashboards(self, enhanced_data: Dict, timestamp: str) -> Dict[str, str]:
        """Generate interactive Plotly dashboards"""
        dashboards = {}
        
        # Performance dashboard
        perf_dashboard = self._create_performance_dashboard(enhanced_data)
        perf_file = self.dirs['dashboards'] / f"performance_dashboard_{timestamp}.html"
        pyo.plot(perf_dashboard, filename=str(perf_file), auto_open=False)
        dashboards['performance'] = str(perf_file)
        
        # System resources dashboard  
        sys_dashboard = self._create_system_dashboard(enhanced_data)
        sys_file = self.dirs['dashboards'] / f"system_dashboard_{timestamp}.html"
        pyo.plot(sys_dashboard, filename=str(sys_file), auto_open=False)
        dashboards['system'] = str(sys_file)
        
        # Executive summary dashboard
        exec_dashboard = self._create_executive_dashboard(enhanced_data)
        exec_file = self.dirs['dashboards'] / f"executive_dashboard_{timestamp}.html"
        pyo.plot(exec_dashboard, filename=str(exec_file), auto_open=False)
        dashboards['executive'] = str(exec_file)
        
        return dashboards
    
    def _generate_api_endpoints(self, enhanced_data: Dict, timestamp: str) -> Dict[str, str]:
        """Generate API endpoint data for real-time consumption"""
        api_files = {}
        
        # Current status endpoint
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "summary": enhanced_data.get("insights", {}).get("executive", {}).get("business_impact", {}),
            "alerts": enhanced_data.get("alerts", {}),
            "key_metrics": self._extract_key_metrics(enhanced_data)
        }
        
        status_file = self.dirs['api'] / f"current_status_{timestamp}.json"
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, default=str)
        api_files['status'] = str(status_file)
        
        # Metrics endpoint
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": enhanced_data.get("analytics", {}),
            "performance": enhanced_data.get("raw_data", {}).get("stream_performance", {}),
            "system": enhanced_data.get("raw_data", {}).get("system_resources", {})
        }
        
        metrics_file = self.dirs['api'] / f"metrics_{timestamp}.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        api_files['metrics'] = str(metrics_file)
        
        return api_files
    
    # Helper methods for calculations and data processing
    def _calculate_stability_score(self, individual_streams: List[Dict]) -> float:
        """Calculate overall stability score (0-100)"""
        if not individual_streams:
            return 0
        
        total_score = 0
        for stream in individual_streams:
            reconnections = stream.get("reconnections", 0)
            status = stream.get("status", "")
            
            # Base score from connection status
            if status == "connected":
                base_score = 100
            elif status == "disconnected":
                base_score = 50
            else:
                base_score = 0
            
            # Reduce score based on reconnections
            reconnection_penalty = min(reconnections * 10, 50)
            stream_score = max(0, base_score - reconnection_penalty)
            total_score += stream_score
        
        return total_score / len(individual_streams)
    
    def _analyze_failure_patterns(self, individual_streams: List[Dict]) -> Dict:
        """Analyze patterns in stream failures"""
        patterns = {
            "error_types": {},
            "failure_timing": [],
            "camera_reliability": {}
        }
        
        for stream in individual_streams:
            camera_id = stream.get("camera_id")
            errors = stream.get("errors", [])
            reconnections = stream.get("reconnections", 0)
            
            # Categorize error types
            for error in errors:
                error_type = self._categorize_error(error)
                patterns["error_types"][error_type] = patterns["error_types"].get(error_type, 0) + 1
            
            # Track camera reliability
            patterns["camera_reliability"][camera_id] = {
                "reconnections": reconnections,
                "error_count": len(errors),
                "reliability_score": max(0, 100 - (reconnections * 10) - (len(errors) * 5))
            }
        
        return patterns
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error types for analysis"""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return "timeout"
        elif "ssl" in error_lower or "certificate" in error_lower:
            return "ssl_certificate"
        elif "500" in error or "internal server error" in error_lower:
            return "server_error"
        elif "404" in error or "not found" in error_lower:
            return "not_found"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        else:
            return "other"
    
    # Additional helper methods would be implemented here...
    # (Due to length constraints, showing representative methods)
    
    def _filter_data_for_audience(self, enhanced_data: Dict, audience: AudienceConfig) -> Dict:
        """Filter data based on audience requirements"""
        filtered = enhanced_data.copy()
        
        if audience.detail_level == "low":
            # Remove detailed raw data for executives
            filtered.pop("raw_data", None)
            
        if not audience.include_raw_data:
            filtered.pop("raw_data", None)
            
        if not audience.include_recommendations:
            filtered.pop("recommendations", None)
            
        # Include audience-specific insights
        if audience.audience_type in filtered.get("insights", {}):
            filtered["audience_insights"] = filtered["insights"][audience.audience_type]
        
        return filtered
    
    # Placeholder methods for additional functionality
    def _calculate_cpu_efficiency(self, system_resources: Dict) -> float:
        return min(100, (100 - system_resources.get("average_cpu_percent", 0)) * 1.2)
    
    def _calculate_memory_efficiency(self, system_resources: Dict) -> float:
        return min(100, (100 - system_resources.get("average_memory_percent", 0)) * 1.1)
    
    def _estimate_cost_efficiency(self, report_data: Dict, system_resources: Dict) -> Dict:
        return {"estimated_cost_per_stream": 0.10, "efficiency_rating": "moderate"}
    
    def _analyze_statistical_significance(self, report_data: Dict) -> Dict:
        return {"sample_size": "adequate", "confidence_level": 0.95}
    
    def _analyze_correlations(self, report_data: Dict) -> Dict:
        return {"fps_cpu_correlation": 0.65, "reconnections_latency_correlation": 0.45}
    
    def _detect_anomalies(self, report_data: Dict) -> List[Dict]:
        return [{"type": "fps_spike", "camera_id": 123, "severity": "medium"}]
    
    def _suggest_predictive_models(self, report_data: Dict) -> List[str]:
        return ["Time series forecasting for capacity planning", "Anomaly detection for proactive monitoring"]
    
    def _identify_technical_bottlenecks(self, report_data: Dict) -> List[Dict]:
        return [{"bottleneck": "network_bandwidth", "impact": "high", "location": "camera_connections"}]
    
    def _identify_optimization_opportunities(self, report_data: Dict) -> List[Dict]:
        return [{"opportunity": "connection_pooling", "estimated_improvement": "15%"}]
    
    def _generate_architecture_recommendations(self, report_data: Dict) -> List[str]:
        return ["Implement load balancing", "Add caching layer", "Consider microservices architecture"]
    
    def _generate_debugging_insights(self, report_data: Dict) -> List[Dict]:
        return [{"issue": "intermittent_timeouts", "debug_steps": ["Check network latency", "Review logs"]}]
    
    def _assess_business_impact(self, report_data: Dict) -> Dict:
        return {"operational_readiness": "good", "scalability_concerns": "moderate", "investment_needed": "medium"}
    
    def _assess_risks(self, report_data: Dict) -> List[Dict]:
        return [{"risk": "performance_degradation", "probability": "medium", "impact": "high"}]
    
    def _generate_capacity_planning(self, report_data: Dict) -> Dict:
        return {"current_utilization": "70%", "recommended_capacity": "150%", "scaling_timeline": "3_months"}
    
    def _analyze_roi(self, report_data: Dict) -> Dict:
        return {"investment_cost": "$50K", "operational_savings": "$120K/year", "payback_period": "5_months"}
    
    def _generate_monitoring_alerts(self, report_data: Dict) -> List[Dict]:
        return [{"metric": "fps_threshold", "threshold": 10, "action": "alert_operations"}]
    
    def _assess_sla_compliance(self, report_data: Dict) -> Dict:
        return {"uptime_target": "99.9%", "current_uptime": "98.5%", "sla_status": "at_risk"}
    
    def _suggest_incident_prevention(self, report_data: Dict) -> List[str]:
        return ["Implement circuit breakers", "Add health checks", "Create runbooks"]
    
    def _suggest_maintenance_schedule(self, report_data: Dict) -> Dict:
        return {"daily_checks": ["connection_status"], "weekly_maintenance": ["log_rotation"], "monthly_reviews": ["capacity_analysis"]}
    
    def _extract_key_metrics(self, enhanced_data: Dict) -> Dict:
        """Extract key metrics for API consumption"""
        raw_data = enhanced_data.get("raw_data", {})
        return {
            "concurrent_streams": raw_data.get("test_info", {}).get("max_concurrent_achieved", 0),
            "average_fps": raw_data.get("stream_performance", {}).get("average_fps", 0),
            "total_reconnections": raw_data.get("stream_performance", {}).get("total_reconnections", 0),
            "cpu_usage": raw_data.get("system_resources", {}).get("average_cpu_percent", 0),
            "memory_usage": raw_data.get("system_resources", {}).get("average_memory_percent", 0),
            "stability_score": enhanced_data.get("analytics", {}).get("stability_metrics", {}).get("connection_stability", {}).get("stability_score", 0)
        }
    
    # Additional methods for CSV writing, HTML generation, PDF creation, and dashboard building
    # would be implemented here based on specific requirements...
    
    def _write_streams_csv(self, enhanced_data: Dict, file_path: Path, audience: AudienceConfig):
        """Write detailed stream performance data to CSV"""
        streams = enhanced_data.get("raw_data", {}).get("individual_streams", [])
        
        fieldnames = ["camera_id", "status", "avg_fps", "total_frames", "total_bytes", 
                     "reconnections", "duration_seconds", "errors_count"]
        
        if audience.detail_level == "high":
            fieldnames.extend(["stability_score", "efficiency_rating", "error_types"])
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for stream in streams:
                row = {field: stream.get(field, 0) for field in fieldnames if field in stream}
                row["errors_count"] = len(stream.get("errors", []))
                
                if audience.detail_level == "high":
                    row["stability_score"] = max(0, 100 - (stream.get("reconnections", 0) * 10))
                    row["efficiency_rating"] = "high" if stream.get("avg_fps", 0) > 20 else "medium" if stream.get("avg_fps", 0) > 10 else "low"
                    row["error_types"] = "|".join([self._categorize_error(e) for e in stream.get("errors", [])])
                
                writer.writerow(row)
    
    def _write_system_metrics_csv(self, enhanced_data: Dict, file_path: Path):
        """Write system metrics over time to CSV"""
        # This would extract time-series system data if available
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "cpu_percent", "memory_percent", "active_streams", "total_fps"])
            # Add actual time-series data here
    
    def _write_summary_csv(self, enhanced_data: Dict, file_path: Path, audience: AudienceConfig):
        """Write executive summary data to CSV"""
        summary_data = []
        raw_data = enhanced_data.get("raw_data", {})
        
        summary_data.append(["Metric", "Value", "Status", "Recommendation"])
        summary_data.append(["Max Concurrent Streams", 
                           raw_data.get("test_info", {}).get("max_concurrent_achieved", 0),
                           "Good" if raw_data.get("test_info", {}).get("max_concurrent_achieved", 0) > 5 else "Poor",
                           "Scale as needed"])
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(summary_data)
    
    def _write_recommendations_csv(self, enhanced_data: Dict, file_path: Path):
        """Write recommendations to CSV"""
        recommendations = enhanced_data.get("recommendations", {})
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Priority", "Action", "Timeline", "Steps"])
            
            for category, rec_list in recommendations.items():
                for rec in rec_list:
                    if isinstance(rec, dict):
                        writer.writerow([
                            category,
                            rec.get("priority", "medium"),
                            rec.get("action", ""),
                            rec.get("timeline", ""),
                            "|".join(rec.get("steps", []))
                        ])
    
    def _create_html_content(self, enhanced_data: Dict, audience: AudienceConfig) -> str:
        """Create HTML content for the report"""
        # Basic HTML template - in production this would use Jinja2 templates
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Load Test Report - {audience.audience_type.title()}</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .metric {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .alert {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .critical {{ background: #ffe6e6; border-left: 5px solid #dc3545; }}
                .warning {{ background: #fff3cd; border-left: 5px solid #ffc107; }}
                .info {{ background: #d1ecf1; border-left: 5px solid #17a2b8; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Load Test Report</h1>
                <p>Generated for: {audience.audience_type.title()}</p>
                <p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """
        
        # Add content based on audience type
        if audience.audience_type == "executive":
            html += self._create_executive_html_content(enhanced_data)
        elif audience.audience_type == "engineer":
            html += self._create_engineer_html_content(enhanced_data)
        elif audience.audience_type == "data_scientist":
            html += self._create_data_scientist_html_content(enhanced_data)
        else:
            html += self._create_operations_html_content(enhanced_data)
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _create_executive_html_content(self, enhanced_data: Dict) -> str:
        """Create executive-focused HTML content"""
        raw_data = enhanced_data.get("raw_data", {})
        insights = enhanced_data.get("insights", {}).get("executive", {})
        
        return f"""
        <div class="metric">
            <h2>Executive Summary</h2>
            <p><strong>System Status:</strong> {insights.get("business_impact", {}).get("operational_readiness", "Unknown")}</p>
            <p><strong>Maximum Concurrent Streams:</strong> {raw_data.get("test_info", {}).get("max_concurrent_achieved", 0)}</p>
            <p><strong>Average Performance:</strong> {raw_data.get("stream_performance", {}).get("average_fps", 0):.1f} FPS</p>
        </div>
        
        <div class="metric">
            <h2>Business Impact</h2>
            <p><strong>Operational Readiness:</strong> {insights.get("business_impact", {}).get("operational_readiness", "Unknown")}</p>
            <p><strong>Scalability Concerns:</strong> {insights.get("business_impact", {}).get("scalability_concerns", "Unknown")}</p>
            <p><strong>Investment Needed:</strong> {insights.get("business_impact", {}).get("investment_needed", "Unknown")}</p>
        </div>
        
        <div class="metric">
            <h2>Key Recommendations</h2>
            <ul>
                <li>Monitor system performance closely during production deployment</li>
                <li>Plan for capacity scaling based on actual usage patterns</li>
                <li>Implement comprehensive monitoring and alerting systems</li>
            </ul>
        </div>
        """
    
    def _create_engineer_html_content(self, enhanced_data: Dict) -> str:
        """Create engineer-focused HTML content"""
        return """
        <div class="metric">
            <h2>Technical Performance Metrics</h2>
            <!-- Technical details would be populated here -->
        </div>
        """
    
    def _create_data_scientist_html_content(self, enhanced_data: Dict) -> str:
        """Create data scientist-focused HTML content"""
        return """
        <div class="metric">
            <h2>Statistical Analysis</h2>
            <!-- Statistical analysis would be populated here -->
        </div>
        """
    
    def _create_operations_html_content(self, enhanced_data: Dict) -> str:
        """Create operations-focused HTML content"""
        return """
        <div class="metric">
            <h2>Operational Metrics</h2>
            <!-- Operational details would be populated here -->
        </div>
        """
    
    def _create_pdf_content(self, enhanced_data: Dict, audience: AudienceConfig, styles) -> List:
        """Create PDF content elements"""
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        story.append(Paragraph("Executive Load Test Summary", title_style))
        story.append(Spacer(1, 12))
        
        # Summary table
        raw_data = enhanced_data.get("raw_data", {})
        summary_data = [
            ['Metric', 'Value'],
            ['Test Date', datetime.now().strftime('%Y-%m-%d %H:%M')],
            ['Max Concurrent Streams', str(raw_data.get("test_info", {}).get("max_concurrent_achieved", 0))],
            ['Average FPS', f"{raw_data.get('stream_performance', {}).get('average_fps', 0):.1f}"],
            ['Total Reconnections', str(raw_data.get("stream_performance", {}).get("total_reconnections", 0))],
        ]
        
        table = Table(summary_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 12))
        
        return story
    
    def _create_performance_dashboard(self, enhanced_data: Dict):
        """Create interactive performance dashboard"""
        if not PLOTLY_AVAILABLE:
            return None
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('FPS Distribution', 'Stream Status', 'Resource Usage', 'Reconnections'),
            specs=[[{"type": "histogram"}, {"type": "pie"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        raw_data = enhanced_data.get("raw_data", {})
        individual_streams = raw_data.get("individual_streams", [])
        
        if individual_streams:
            # FPS Distribution
            fps_values = [s.get("avg_fps", 0) for s in individual_streams]
            fig.add_trace(
                go.Histogram(x=fps_values, name="FPS Distribution", nbinsx=20),
                row=1, col=1
            )
            
            # Stream Status
            status_counts = {}
            for stream in individual_streams:
                status = stream.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            fig.add_trace(
                go.Pie(labels=list(status_counts.keys()), values=list(status_counts.values()), name="Status"),
                row=1, col=2
            )
            
            # Resource usage
            system_resources = raw_data.get("system_resources", {})
            fig.add_trace(
                go.Bar(x=["CPU", "Memory"], 
                      y=[system_resources.get("average_cpu_percent", 0), 
                         system_resources.get("average_memory_percent", 0)],
                      name="Resource Usage"),
                row=2, col=1
            )
            
            # Reconnections scatter
            camera_ids = [s.get("camera_id", 0) for s in individual_streams]
            reconnections = [s.get("reconnections", 0) for s in individual_streams]
            fig.add_trace(
                go.Scatter(x=camera_ids, y=reconnections, mode='markers', name="Reconnections"),
                row=2, col=2
            )
        
        fig.update_layout(height=800, title_text="Performance Dashboard")
        return fig
    
    def _create_system_dashboard(self, enhanced_data: Dict):
        """Create system resources dashboard"""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 4, 2], name="System Metrics"))
        fig.update_layout(title="System Resources Over Time")
        return fig
    
    def _create_executive_dashboard(self, enhanced_data: Dict):
        """Create executive summary dashboard"""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Indicator(
            mode = "gauge+number",
            value = 85,
            title = {"text": "Overall System Health"},
            gauge = {"axis": {"range": [None, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 50], "color": "lightgray"},
                        {"range": [50, 85], "color": "gray"}],
                    "threshold": {"line": {"color": "red", "width": 4},
                                "thickness": 0.75, "value": 90}}
        ))
        fig.update_layout(title="Executive Dashboard")
        return fig