#!/usr/bin/env python3
"""
Hierarchical Navigation and Filtering System
============================================

Provides intelligent result organization with navigation, filtering, and search capabilities.
Designed for easy consumption across different organizational roles and use cases.

Features:
- Multi-level information architecture
- Advanced filtering and search
- Contextual help and explanations
- Quick navigation and drill-down
- Mobile-responsive design
- Accessibility compliance
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

@dataclass
class NavigationNode:
    """Represents a node in the hierarchical navigation structure"""
    id: str
    title: str
    description: str
    level: int
    parent_id: Optional[str] = None
    children: List[str] = None
    data_path: Optional[str] = None
    audience_relevance: List[str] = None
    priority: int = 1  # 1=high, 2=medium, 3=low
    tags: List[str] = None
    help_text: Optional[str] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.audience_relevance is None:
            self.audience_relevance = ["all"]
        if self.tags is None:
            self.tags = []

@dataclass
class FilterCriteria:
    """Criteria for filtering results"""
    audience: Optional[str] = None
    priority_levels: List[int] = None
    tags: List[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    performance_threshold: Optional[Dict[str, float]] = None
    text_search: Optional[str] = None
    
    def __post_init__(self):
        if self.priority_levels is None:
            self.priority_levels = [1, 2, 3]
        if self.tags is None:
            self.tags = []

class HierarchicalNavigationSystem:
    """Manages hierarchical organization and navigation of test results"""
    
    def __init__(self, output_dir: str = "organized_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Navigation structure
        self.navigation_tree = {}
        self.node_registry = {}
        
        # Search indices
        self.text_index = {}
        self.tag_index = {}
        self.audience_index = {}
        
        # Initialize the standard navigation structure
        self._initialize_navigation_structure()
    
    def _initialize_navigation_structure(self):
        """Initialize the standard hierarchical navigation structure"""
        
        # Root level - Main categories
        root_nodes = [
            NavigationNode(
                id="executive_summary",
                title="Executive Summary",
                description="High-level business insights and strategic recommendations",
                level=0,
                audience_relevance=["executive", "all"],
                priority=1,
                tags=["summary", "business", "strategic"],
                help_text="Quick overview for decision makers focusing on business impact and strategic implications"
            ),
            NavigationNode(
                id="technical_analysis",
                title="Technical Analysis",
                description="Detailed technical performance metrics and engineering insights",
                level=0,
                audience_relevance=["engineer", "data_scientist", "all"],
                priority=1,
                tags=["technical", "performance", "engineering"],
                help_text="In-depth technical analysis for engineers and technical teams"
            ),
            NavigationNode(
                id="operational_metrics",
                title="Operational Metrics",
                description="Real-time operational data and monitoring insights",
                level=0,
                audience_relevance=["operations", "engineer", "all"],
                priority=1,
                tags=["operations", "monitoring", "real-time"],
                help_text="Operational metrics and alerts for day-to-day system management"
            ),
            NavigationNode(
                id="data_science",
                title="Data Science & Analytics", 
                description="Statistical analysis, patterns, and predictive insights",
                level=0,
                audience_relevance=["data_scientist", "analyst", "all"],
                priority=1,
                tags=["analytics", "statistics", "data"],
                help_text="Comprehensive statistical analysis and data science insights"
            ),
            NavigationNode(
                id="alerts_actions",
                title="Alerts & Actions",
                description="Critical alerts, warnings, and recommended actions",
                level=0,
                audience_relevance=["all"],
                priority=1,
                tags=["alerts", "actions", "critical"],
                help_text="Important alerts and actionable recommendations requiring immediate attention"
            )
        ]
        
        # Add root nodes to registry
        for node in root_nodes:
            self.node_registry[node.id] = node
            self.navigation_tree[node.id] = node
        
        # Executive Summary sub-categories
        executive_children = [
            NavigationNode(
                id="business_impact",
                title="Business Impact Assessment",
                description="Impact on business operations and strategic objectives",
                level=1,
                parent_id="executive_summary",
                audience_relevance=["executive"],
                priority=1,
                tags=["business", "impact", "roi"],
                help_text="Analysis of how system performance affects business objectives and ROI"
            ),
            NavigationNode(
                id="capacity_planning",
                title="Capacity Planning",
                description="Current capacity assessment and future scaling recommendations",
                level=1,
                parent_id="executive_summary",
                audience_relevance=["executive", "operations"],
                priority=1,
                tags=["capacity", "scaling", "planning"],
                help_text="Strategic capacity planning and resource allocation recommendations"
            ),
            NavigationNode(
                id="risk_assessment",
                title="Risk Assessment",
                description="Identified risks and mitigation strategies",
                level=1,
                parent_id="executive_summary",
                audience_relevance=["executive", "operations"],
                priority=1,
                tags=["risk", "mitigation", "strategy"],
                help_text="Risk analysis and recommended mitigation strategies"
            ),
            NavigationNode(
                id="investment_recommendations",
                title="Investment Recommendations",
                description="Recommended investments and expected returns",
                level=1,
                parent_id="executive_summary",
                audience_relevance=["executive"],
                priority=2,
                tags=["investment", "budget", "roi"],
                help_text="Strategic investment recommendations for system improvements"
            )
        ]
        
        # Technical Analysis sub-categories
        technical_children = [
            NavigationNode(
                id="performance_metrics",
                title="Performance Metrics",
                description="Detailed performance statistics and benchmarks",
                level=1,
                parent_id="technical_analysis",
                audience_relevance=["engineer", "data_scientist"],
                priority=1,
                tags=["performance", "metrics", "benchmarks"],
                help_text="Comprehensive performance metrics including FPS, latency, and throughput"
            ),
            NavigationNode(
                id="system_resources",
                title="System Resource Analysis",
                description="CPU, memory, network, and storage utilization",
                level=1,
                parent_id="technical_analysis",
                audience_relevance=["engineer", "operations"],
                priority=1,
                tags=["resources", "cpu", "memory", "network"],
                help_text="Detailed analysis of system resource utilization and bottlenecks"
            ),
            NavigationNode(
                id="stream_analysis",
                title="Individual Stream Analysis",
                description="Per-stream performance and behavior analysis",
                level=1,
                parent_id="technical_analysis",
                audience_relevance=["engineer", "data_scientist"],
                priority=1,
                tags=["streams", "individual", "behavior"],
                help_text="Detailed analysis of individual stream performance and patterns"
            ),
            NavigationNode(
                id="error_analysis",
                title="Error Analysis",
                description="Error patterns, root causes, and troubleshooting",
                level=1,
                parent_id="technical_analysis",
                audience_relevance=["engineer"],
                priority=1,
                tags=["errors", "troubleshooting", "debugging"],
                help_text="Comprehensive error analysis and troubleshooting guidance"
            ),
            NavigationNode(
                id="optimization_opportunities",
                title="Optimization Opportunities",
                description="Identified optimization opportunities and recommendations",
                level=1,
                parent_id="technical_analysis",
                audience_relevance=["engineer"],
                priority=2,
                tags=["optimization", "tuning", "improvement"],
                help_text="Technical optimization opportunities and implementation guidance"
            )
        ]
        
        # Operational Metrics sub-categories
        operational_children = [
            NavigationNode(
                id="real_time_status",
                title="Real-time Status",
                description="Current system status and health indicators",
                level=1,
                parent_id="operational_metrics",
                audience_relevance=["operations"],
                priority=1,
                tags=["real-time", "status", "health"],
                help_text="Live system status and health monitoring dashboard"
            ),
            NavigationNode(
                id="sla_compliance",
                title="SLA Compliance",
                description="Service level agreement compliance and tracking",
                level=1,
                parent_id="operational_metrics",
                audience_relevance=["operations", "executive"],
                priority=1,
                tags=["sla", "compliance", "tracking"],
                help_text="SLA compliance metrics and performance against agreed service levels"
            ),
            NavigationNode(
                id="monitoring_alerts",
                title="Monitoring & Alerts",
                description="Alert configurations and monitoring recommendations",
                level=1,
                parent_id="operational_metrics",
                audience_relevance=["operations"],
                priority=1,
                tags=["monitoring", "alerts", "notifications"],
                help_text="Monitoring setup and alert configuration recommendations"
            ),
            NavigationNode(
                id="maintenance_schedule",
                title="Maintenance Schedule",
                description="Recommended maintenance activities and schedules",
                level=1,
                parent_id="operational_metrics",
                audience_relevance=["operations"],
                priority=2,
                tags=["maintenance", "schedule", "preventive"],
                help_text="Preventive maintenance schedule and routine operational tasks"
            )
        ]
        
        # Data Science sub-categories
        data_science_children = [
            NavigationNode(
                id="statistical_analysis",
                title="Statistical Analysis",
                description="Comprehensive statistical analysis and significance testing",
                level=1,
                parent_id="data_science",
                audience_relevance=["data_scientist"],
                priority=1,
                tags=["statistics", "analysis", "significance"],
                help_text="Statistical analysis including hypothesis testing and confidence intervals"
            ),
            NavigationNode(
                id="correlation_analysis",
                title="Correlation Analysis",
                description="Correlation patterns between metrics and variables",
                level=1,
                parent_id="data_science",
                audience_relevance=["data_scientist"],
                priority=1,
                tags=["correlation", "patterns", "relationships"],
                help_text="Analysis of correlations between different performance metrics"
            ),
            NavigationNode(
                id="anomaly_detection",
                title="Anomaly Detection",
                description="Detected anomalies and outlier analysis",
                level=1,
                parent_id="data_science",
                audience_relevance=["data_scientist", "engineer"],
                priority=1,
                tags=["anomalies", "outliers", "detection"],
                help_text="Automated anomaly detection and outlier analysis"
            ),
            NavigationNode(
                id="predictive_insights",
                title="Predictive Insights",
                description="Predictive models and forecasting analysis",
                level=1,
                parent_id="data_science",
                audience_relevance=["data_scientist"],
                priority=2,
                tags=["prediction", "forecasting", "modeling"],
                help_text="Predictive analysis and forecasting models for capacity planning"
            ),
            NavigationNode(
                id="data_export",
                title="Data Export & APIs",
                description="Raw data exports and API endpoints for further analysis",
                level=1,
                parent_id="data_science",
                audience_relevance=["data_scientist", "engineer"],
                priority=2,
                tags=["export", "api", "raw-data"],
                help_text="Access to raw data and API endpoints for custom analysis"
            )
        ]
        
        # Add all child nodes
        all_children = executive_children + technical_children + operational_children + data_science_children
        
        for child in all_children:
            self.node_registry[child.id] = child
            # Add to parent's children list
            if child.parent_id in self.node_registry:
                self.node_registry[child.parent_id].children.append(child.id)
        
        # Build search indices
        self._build_search_indices()
    
    def _build_search_indices(self):
        """Build search indices for fast filtering and searching"""
        self.text_index = {}
        self.tag_index = {}
        self.audience_index = {}
        
        for node_id, node in self.node_registry.items():
            # Text index
            text_content = f"{node.title} {node.description} {node.help_text or ''}".lower()
            words = re.findall(r'\w+', text_content)
            for word in words:
                if word not in self.text_index:
                    self.text_index[word] = []
                self.text_index[word].append(node_id)
            
            # Tag index
            for tag in node.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(node_id)
            
            # Audience index
            for audience in node.audience_relevance:
                if audience not in self.audience_index:
                    self.audience_index[audience] = []
                self.audience_index[audience].append(node_id)
    
    def organize_report_data(self, enhanced_report: Dict) -> Dict:
        """Organize report data according to hierarchical structure"""
        organized_data = {
            "navigation": self._generate_navigation_structure(),
            "content": {},
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "structure_version": "2.0",
                "total_nodes": len(self.node_registry)
            }
        }
        
        # Map report data to navigation nodes
        organized_data["content"] = self._map_data_to_nodes(enhanced_report)
        
        return organized_data
    
    def _generate_navigation_structure(self) -> Dict:
        """Generate the navigation structure for frontend consumption"""
        navigation = {
            "tree": {},
            "nodes": {},
            "breadcrumbs": {},
            "quick_access": []
        }
        
        # Build tree structure
        for node_id, node in self.node_registry.items():
            navigation["nodes"][node_id] = {
                "id": node.id,
                "title": node.title,
                "description": node.description,
                "level": node.level,
                "parent_id": node.parent_id,
                "children": node.children,
                "audience_relevance": node.audience_relevance,
                "priority": node.priority,
                "tags": node.tags,
                "help_text": node.help_text,
                "has_data": node.data_path is not None
            }
            
            if node.level == 0:
                navigation["tree"][node_id] = self._build_tree_branch(node_id)
        
        # Build breadcrumbs for each node
        for node_id in self.node_registry:
            navigation["breadcrumbs"][node_id] = self._build_breadcrumbs(node_id)
        
        # Quick access items (high priority items)
        navigation["quick_access"] = [
            node_id for node_id, node in self.node_registry.items()
            if node.priority == 1 and node.level <= 1
        ]
        
        return navigation
    
    def _build_tree_branch(self, node_id: str) -> Dict:
        """Recursively build tree branch structure"""
        node = self.node_registry[node_id]
        branch = {
            "id": node.id,
            "title": node.title,
            "level": node.level,
            "children": []
        }
        
        for child_id in node.children:
            branch["children"].append(self._build_tree_branch(child_id))
        
        return branch
    
    def _build_breadcrumbs(self, node_id: str) -> List[Dict]:
        """Build breadcrumb trail for a node"""
        breadcrumbs = []
        current_node = self.node_registry[node_id]
        
        # Walk up the tree
        while current_node:
            breadcrumbs.insert(0, {
                "id": current_node.id,
                "title": current_node.title,
                "level": current_node.level
            })
            
            if current_node.parent_id:
                current_node = self.node_registry.get(current_node.parent_id)
            else:
                break
        
        return breadcrumbs
    
    def _map_data_to_nodes(self, enhanced_report: Dict) -> Dict:
        """Map report data to appropriate navigation nodes"""
        content = {}
        
        # Executive Summary content
        content["executive_summary"] = {
            "summary": enhanced_report.get("insights", {}).get("executive", {}).get("business_impact", {}),
            "key_metrics": self._extract_executive_metrics(enhanced_report),
            "status": self._determine_overall_status(enhanced_report)
        }
        
        content["business_impact"] = enhanced_report.get("insights", {}).get("executive", {}).get("business_impact", {})
        content["capacity_planning"] = enhanced_report.get("insights", {}).get("executive", {}).get("capacity_planning", {})
        content["risk_assessment"] = enhanced_report.get("insights", {}).get("executive", {}).get("risk_assessment", {})
        content["investment_recommendations"] = enhanced_report.get("recommendations", {}).get("long_term_strategies", [])
        
        # Technical Analysis content
        content["technical_analysis"] = {
            "overview": enhanced_report.get("analytics", {}).get("performance_metrics", {}),
            "bottlenecks": enhanced_report.get("insights", {}).get("engineer", {}).get("technical_bottlenecks", [])
        }
        
        content["performance_metrics"] = {
            "fps_statistics": enhanced_report.get("analytics", {}).get("performance_metrics", {}).get("fps_statistics", {}),
            "throughput": enhanced_report.get("analytics", {}).get("performance_metrics", {}).get("throughput_analysis", {}),
            "benchmarks": self._generate_performance_benchmarks(enhanced_report)
        }
        
        content["system_resources"] = {
            "current_usage": enhanced_report.get("raw_data", {}).get("system_resources", {}),
            "efficiency_analysis": enhanced_report.get("analytics", {}).get("efficiency_metrics", {}),
            "recommendations": enhanced_report.get("recommendations", {}).get("short_term_improvements", [])
        }
        
        content["stream_analysis"] = {
            "individual_streams": enhanced_report.get("raw_data", {}).get("individual_streams", []),
            "patterns": self._analyze_stream_patterns(enhanced_report),
            "top_performers": self._identify_top_performers(enhanced_report),
            "problem_streams": self._identify_problem_streams(enhanced_report)
        }
        
        content["error_analysis"] = {
            "error_summary": self._summarize_errors(enhanced_report),
            "error_patterns": enhanced_report.get("analytics", {}).get("stability_metrics", {}).get("connection_stability", {}).get("failure_pattern_analysis", {}),
            "troubleshooting_guide": self._generate_troubleshooting_guide(enhanced_report)
        }
        
        # Operational Metrics content
        content["operational_metrics"] = {
            "current_status": "operational",
            "health_score": self._calculate_health_score(enhanced_report)
        }
        
        content["real_time_status"] = {
            "active_streams": enhanced_report.get("raw_data", {}).get("test_info", {}).get("max_concurrent_achieved", 0),
            "system_health": self._assess_system_health(enhanced_report),
            "alerts_count": len(enhanced_report.get("alerts", {}).get("critical", []) + enhanced_report.get("alerts", {}).get("warning", []))
        }
        
        content["sla_compliance"] = enhanced_report.get("insights", {}).get("operations", {}).get("sla_compliance", {})
        content["monitoring_alerts"] = enhanced_report.get("insights", {}).get("operations", {}).get("monitoring_alerts", [])
        content["maintenance_schedule"] = enhanced_report.get("insights", {}).get("operations", {}).get("maintenance_schedule", {})
        
        # Data Science content
        content["data_science"] = {
            "overview": enhanced_report.get("analytics", {}),
            "datasets_available": self._list_available_datasets(enhanced_report)
        }
        
        content["statistical_analysis"] = enhanced_report.get("insights", {}).get("data_scientist", {}).get("statistical_significance", {})
        content["correlation_analysis"] = enhanced_report.get("insights", {}).get("data_scientist", {}).get("correlation_analysis", {})
        content["anomaly_detection"] = enhanced_report.get("insights", {}).get("data_scientist", {}).get("anomaly_detection", [])
        content["predictive_insights"] = enhanced_report.get("insights", {}).get("data_scientist", {}).get("predictive_modeling_suggestions", [])
        
        # Alerts & Actions
        content["alerts_actions"] = {
            "critical_alerts": enhanced_report.get("alerts", {}).get("critical", []),
            "warnings": enhanced_report.get("alerts", {}).get("warning", []),
            "immediate_actions": enhanced_report.get("recommendations", {}).get("immediate_actions", []),
            "priority_matrix": self._create_priority_matrix(enhanced_report)
        }
        
        return content
    
    def filter_content(self, organized_data: Dict, filter_criteria: FilterCriteria) -> Dict:
        """Filter content based on criteria"""
        filtered_data = {
            "navigation": organized_data["navigation"].copy(),
            "content": {},
            "metadata": organized_data["metadata"].copy(),
            "filter_applied": asdict(filter_criteria)
        }
        
        # Filter navigation nodes
        relevant_node_ids = self._find_relevant_nodes(filter_criteria)
        
        # Filter navigation structure
        filtered_navigation = self._filter_navigation(organized_data["navigation"], relevant_node_ids)
        filtered_data["navigation"] = filtered_navigation
        
        # Filter content
        for node_id in relevant_node_ids:
            if node_id in organized_data["content"]:
                filtered_data["content"][node_id] = organized_data["content"][node_id]
        
        return filtered_data
    
    def _find_relevant_nodes(self, filter_criteria: FilterCriteria) -> List[str]:
        """Find nodes that match the filter criteria"""
        relevant_nodes = set()
        
        # Filter by audience
        if filter_criteria.audience:
            if filter_criteria.audience in self.audience_index:
                relevant_nodes.update(self.audience_index[filter_criteria.audience])
        else:
            # Include all nodes if no audience specified
            relevant_nodes.update(self.node_registry.keys())
        
        # Filter by priority
        priority_filtered = set()
        for node_id in relevant_nodes:
            node = self.node_registry[node_id]
            if node.priority in filter_criteria.priority_levels:
                priority_filtered.add(node_id)
        relevant_nodes = priority_filtered
        
        # Filter by tags
        if filter_criteria.tags:
            tag_filtered = set()
            for tag in filter_criteria.tags:
                if tag in self.tag_index:
                    tag_filtered.update(self.tag_index[tag])
            relevant_nodes = relevant_nodes.intersection(tag_filtered)
        
        # Filter by text search
        if filter_criteria.text_search:
            search_terms = filter_criteria.text_search.lower().split()
            search_filtered = set()
            
            for term in search_terms:
                if term in self.text_index:
                    search_filtered.update(self.text_index[term])
            
            if search_filtered:
                relevant_nodes = relevant_nodes.intersection(search_filtered)
        
        return list(relevant_nodes)
    
    def _filter_navigation(self, navigation: Dict, relevant_node_ids: List[str]) -> Dict:
        """Filter navigation structure to include only relevant nodes"""
        filtered_nav = {
            "tree": {},
            "nodes": {},
            "breadcrumbs": {},
            "quick_access": []
        }
        
        # Filter nodes
        for node_id in relevant_node_ids:
            if node_id in navigation["nodes"]:
                filtered_nav["nodes"][node_id] = navigation["nodes"][node_id]
        
        # Rebuild tree with filtered nodes
        for node_id, node_data in filtered_nav["nodes"].items():
            if node_data["level"] == 0:
                filtered_nav["tree"][node_id] = self._build_filtered_tree_branch(node_id, relevant_node_ids)
        
        # Filter breadcrumbs
        for node_id in relevant_node_ids:
            if node_id in navigation["breadcrumbs"]:
                filtered_nav["breadcrumbs"][node_id] = navigation["breadcrumbs"][node_id]
        
        # Filter quick access
        filtered_nav["quick_access"] = [
            node_id for node_id in navigation["quick_access"]
            if node_id in relevant_node_ids
        ]
        
        return filtered_nav
    
    def _build_filtered_tree_branch(self, node_id: str, relevant_node_ids: List[str]) -> Dict:
        """Build tree branch with only relevant nodes"""
        if node_id not in relevant_node_ids:
            return None
        
        node = self.node_registry[node_id]
        branch = {
            "id": node.id,
            "title": node.title,
            "level": node.level,
            "children": []
        }
        
        for child_id in node.children:
            if child_id in relevant_node_ids:
                child_branch = self._build_filtered_tree_branch(child_id, relevant_node_ids)
                if child_branch:
                    branch["children"].append(child_branch)
        
        return branch
    
    def search_content(self, organized_data: Dict, search_query: str) -> Dict:
        """Search content across all nodes"""
        search_results = {
            "query": search_query,
            "total_results": 0,
            "results_by_category": {},
            "relevant_nodes": [],
            "content_matches": []
        }
        
        search_terms = search_query.lower().split()
        
        # Search in navigation nodes
        for node_id, node in self.node_registry.items():
            node_text = f"{node.title} {node.description} {node.help_text or ''}".lower()
            
            match_score = 0
            for term in search_terms:
                if term in node_text:
                    match_score += node_text.count(term)
            
            if match_score > 0:
                search_results["relevant_nodes"].append({
                    "node_id": node_id,
                    "title": node.title,
                    "description": node.description,
                    "match_score": match_score,
                    "audience_relevance": node.audience_relevance
                })
        
        # Search in content
        for node_id, content in organized_data.get("content", {}).items():
            content_matches = self._search_in_content(content, search_terms, node_id)
            if content_matches:
                search_results["content_matches"].extend(content_matches)
        
        # Sort results by relevance
        search_results["relevant_nodes"].sort(key=lambda x: x["match_score"], reverse=True)
        search_results["total_results"] = len(search_results["relevant_nodes"]) + len(search_results["content_matches"])
        
        return search_results
    
    def _search_in_content(self, content: Any, search_terms: List[str], node_id: str) -> List[Dict]:
        """Search within content data"""
        matches = []
        
        def search_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    search_recursive(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_recursive(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                obj_lower = obj.lower()
                for term in search_terms:
                    if term in obj_lower:
                        matches.append({
                            "node_id": node_id,
                            "path": path,
                            "content": obj,
                            "term": term,
                            "context": obj[:100] + "..." if len(obj) > 100 else obj
                        })
        
        search_recursive(content)
        return matches
    
    def generate_navigation_ui(self, organized_data: Dict, audience: str = "all") -> str:
        """Generate HTML navigation UI"""
        filter_criteria = FilterCriteria(audience=audience if audience != "all" else None)
        filtered_data = self.filter_content(organized_data, filter_criteria)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Load Test Results Navigation</title>
            <style>
                {self._get_navigation_css()}
            </style>
        </head>
        <body>
            <div class="navigation-container">
                <header class="nav-header">
                    <h1>Load Test Results</h1>
                    <div class="audience-selector">
                        <label for="audience">View for:</label>
                        <select id="audience" onchange="filterByAudience(this.value)">
                            <option value="all">All Audiences</option>
                            <option value="executive">Executive</option>
                            <option value="engineer">Engineer</option>
                            <option value="data_scientist">Data Scientist</option>
                            <option value="operations">Operations</option>
                        </select>
                    </div>
                    <div class="search-container">
                        <input type="text" id="search-input" placeholder="Search..." onkeyup="performSearch()">
                        <button onclick="performSearch()">Search</button>
                    </div>
                </header>
                
                <div class="main-content">
                    <nav class="sidebar">
                        <div class="quick-access">
                            <h3>Quick Access</h3>
                            <ul>
                                {self._generate_quick_access_html(filtered_data)}
                            </ul>
                        </div>
                        
                        <div class="navigation-tree">
                            <h3>Full Navigation</h3>
                            {self._generate_tree_html(filtered_data)}
                        </div>
                    </nav>
                    
                    <main class="content-area">
                        <div id="content-display">
                            <div class="welcome-message">
                                <h2>Welcome to Load Test Results</h2>
                                <p>Select a section from the navigation to view detailed results.</p>
                                <p>Current view: <strong>{audience.title() if audience != "all" else "All Audiences"}</strong></p>
                            </div>
                        </div>
                    </main>
                </div>
                
                <div class="breadcrumbs" id="breadcrumbs" style="display: none;">
                    <!-- Breadcrumbs will be populated by JavaScript -->
                </div>
            </div>
            
            <script>
                {self._get_navigation_javascript(filtered_data)}
            </script>
        </body>
        </html>
        """
        
        return html
    
    def _get_navigation_css(self) -> str:
        """Get CSS styles for navigation UI"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .navigation-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        .nav-header {
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .nav-header h1 {
            margin: 0;
        }
        
        .audience-selector, .search-container {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.5rem 0;
        }
        
        .audience-selector select, .search-container input {
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .search-container button {
            padding: 0.5rem 1rem;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .main-content {
            display: flex;
            min-height: calc(100vh - 80px);
        }
        
        .sidebar {
            width: 300px;
            background: #f8f9fa;
            border-right: 1px solid #ddd;
            padding: 1rem;
            overflow-y: auto;
        }
        
        .content-area {
            flex: 1;
            padding: 2rem;
            overflow-y: auto;
        }
        
        .quick-access h3, .navigation-tree h3 {
            margin-bottom: 1rem;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }
        
        .navigation-tree ul, .quick-access ul {
            list-style: none;
        }
        
        .navigation-tree li, .quick-access li {
            margin: 0.5rem 0;
        }
        
        .navigation-tree a, .quick-access a {
            color: #2c3e50;
            text-decoration: none;
            padding: 0.5rem;
            display: block;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        
        .navigation-tree a:hover, .quick-access a:hover {
            background-color: #e9ecef;
        }
        
        .nav-level-0 > a {
            font-weight: bold;
            background: #e3f2fd;
        }
        
        .nav-level-1 {
            margin-left: 1rem;
        }
        
        .nav-level-1 > a {
            font-size: 0.9rem;
        }
        
        .breadcrumbs {
            background: #f8f9fa;
            padding: 0.5rem 2rem;
            border-top: 1px solid #ddd;
            font-size: 0.9rem;
        }
        
        .breadcrumb-item {
            display: inline;
        }
        
        .breadcrumb-item:not(:last-child)::after {
            content: " > ";
            margin: 0 0.5rem;
            color: #6c757d;
        }
        
        .breadcrumb-item a {
            color: #3498db;
            text-decoration: none;
        }
        
        .welcome-message {
            text-align: center;
            padding: 3rem;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 2rem 0;
        }
        
        .content-section {
            margin-bottom: 2rem;
        }
        
        .content-section h2 {
            color: #2c3e50;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }
        
        .help-text {
            background: #e3f2fd;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
            border-left: 4px solid #2196f3;
        }
        
        @media (max-width: 768px) {
            .main-content {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                border-right: none;
                border-bottom: 1px solid #ddd;
            }
            
            .nav-header {
                flex-direction: column;
                align-items: stretch;
            }
            
            .audience-selector, .search-container {
                justify-content: center;
            }
        }
        """
    
    def _generate_quick_access_html(self, filtered_data: Dict) -> str:
        """Generate HTML for quick access links"""
        quick_access_items = filtered_data["navigation"]["quick_access"]
        html = ""
        
        for node_id in quick_access_items:
            if node_id in filtered_data["navigation"]["nodes"]:
                node = filtered_data["navigation"]["nodes"][node_id]
                html += f'<li><a href="#" onclick="loadContent(\'{node_id}\')">{node["title"]}</a></li>'
        
        return html
    
    def _generate_tree_html(self, filtered_data: Dict) -> str:
        """Generate HTML for navigation tree"""
        tree = filtered_data["navigation"]["tree"]
        html = "<ul>"
        
        for root_id, root_data in tree.items():
            html += self._generate_tree_node_html(root_data, filtered_data["navigation"]["nodes"])
        
        html += "</ul>"
        return html
    
    def _generate_tree_node_html(self, node_data: Dict, all_nodes: Dict) -> str:
        """Generate HTML for a single tree node"""
        node_id = node_data["id"]
        level_class = f"nav-level-{node_data['level']}"
        
        html = f'<li class="{level_class}">'
        html += f'<a href="#" onclick="loadContent(\'{node_id}\')">{node_data["title"]}</a>'
        
        if node_data["children"]:
            html += "<ul>"
            for child in node_data["children"]:
                html += self._generate_tree_node_html(child, all_nodes)
            html += "</ul>"
        
        html += "</li>"
        return html
    
    def _get_navigation_javascript(self, filtered_data: Dict) -> str:
        """Get JavaScript for navigation functionality"""
        return f"""
        const navigationData = {json.dumps(filtered_data, default=str)};
        
        function loadContent(nodeId) {{
            const node = navigationData.navigation.nodes[nodeId];
            const content = navigationData.content[nodeId];
            const contentArea = document.getElementById('content-display');
            
            if (!node) {{
                contentArea.innerHTML = '<div class="error">Content not found</div>';
                return;
            }}
            
            let html = `
                <div class="content-section">
                    <h2>${{node.title}}</h2>
                    <p>${{node.description}}</p>
                    
                    ${{node.help_text ? `<div class="help-text">${{node.help_text}}</div>` : ''}}
                    
                    <div class="content-data">
                        ${{content ? formatContent(content) : '<p>No detailed data available for this section.</p>'}}
                    </div>
                </div>
            `;
            
            contentArea.innerHTML = html;
            updateBreadcrumbs(nodeId);
        }}
        
        function formatContent(content) {{
            if (typeof content === 'object') {{
                return '<pre>' + JSON.stringify(content, null, 2) + '</pre>';
            }}
            return '<p>' + content + '</p>';
        }}
        
        function updateBreadcrumbs(nodeId) {{
            const breadcrumbs = navigationData.navigation.breadcrumbs[nodeId];
            const breadcrumbsElement = document.getElementById('breadcrumbs');
            
            if (breadcrumbs && breadcrumbs.length > 0) {{
                let html = 'Navigation: ';
                breadcrumbs.forEach((crumb, index) => {{
                    if (index < breadcrumbs.length - 1) {{
                        html += `<span class="breadcrumb-item"><a href="#" onclick="loadContent('${{crumb.id}}')">${{crumb.title}}</a></span>`;
                    }} else {{
                        html += `<span class="breadcrumb-item">${{crumb.title}}</span>`;
                    }}
                }});
                
                breadcrumbsElement.innerHTML = html;
                breadcrumbsElement.style.display = 'block';
            }}
        }}
        
        function filterByAudience(audience) {{
            // This would trigger a server request to reload with filtered data
            // For demo purposes, we'll just show an alert
            alert('Filtering by audience: ' + audience);
        }}
        
        function performSearch() {{
            const query = document.getElementById('search-input').value;
            if (query.trim() === '') return;
            
            // This would trigger a search request
            alert('Searching for: ' + query);
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', function(e) {{
            if (e.ctrlKey && e.key === 'f') {{
                e.preventDefault();
                document.getElementById('search-input').focus();
            }}
        }});
        """
    
    # Helper methods for content analysis and organization
    def _extract_executive_metrics(self, enhanced_report: Dict) -> Dict:
        """Extract key metrics for executive summary"""
        raw_data = enhanced_report.get("raw_data", {})
        return {
            "max_concurrent_streams": raw_data.get("test_info", {}).get("max_concurrent_achieved", 0),
            "average_fps": raw_data.get("stream_performance", {}).get("average_fps", 0),
            "total_data_processed_gb": raw_data.get("stream_performance", {}).get("total_bytes_received", 0) / (1024**3),
            "system_efficiency": "high" if raw_data.get("system_resources", {}).get("average_cpu_percent", 0) < 70 else "medium"
        }
    
    def _determine_overall_status(self, enhanced_report: Dict) -> str:
        """Determine overall system status"""
        alerts = enhanced_report.get("alerts", {})
        critical_count = len(alerts.get("critical", []))
        warning_count = len(alerts.get("warning", []))
        
        if critical_count > 0:
            return "critical"
        elif warning_count > 3:
            return "warning"
        else:
            return "healthy"
    
    def _generate_performance_benchmarks(self, enhanced_report: Dict) -> Dict:
        """Generate performance benchmarks"""
        raw_data = enhanced_report.get("raw_data", {})
        avg_fps = raw_data.get("stream_performance", {}).get("average_fps", 0)
        
        return {
            "fps_rating": "excellent" if avg_fps > 25 else "good" if avg_fps > 15 else "poor",
            "vs_industry_standard": f"{(avg_fps / 30) * 100:.1f}% of ideal",
            "performance_tier": "production_ready" if avg_fps > 20 else "optimization_needed"
        }
    
    def _analyze_stream_patterns(self, enhanced_report: Dict) -> Dict:
        """Analyze patterns in stream behavior"""
        individual_streams = enhanced_report.get("raw_data", {}).get("individual_streams", [])
        
        if not individual_streams:
            return {}
        
        fps_values = [s.get("avg_fps", 0) for s in individual_streams]
        reconnections = [s.get("reconnections", 0) for s in individual_streams]
        
        return {
            "consistency_score": 100 - (statistics.stdev(fps_values) * 10) if len(fps_values) > 1 else 100,
            "stability_pattern": "stable" if max(reconnections) <= 1 else "unstable",
            "performance_distribution": {
                "high_performers": len([f for f in fps_values if f > 20]),
                "average_performers": len([f for f in fps_values if 10 <= f <= 20]),
                "low_performers": len([f for f in fps_values if f < 10])
            }
        }
    
    def _identify_top_performers(self, enhanced_report: Dict) -> List[Dict]:
        """Identify top performing streams"""
        individual_streams = enhanced_report.get("raw_data", {}).get("individual_streams", [])
        
        # Sort by FPS and take top 5
        sorted_streams = sorted(individual_streams, key=lambda s: s.get("avg_fps", 0), reverse=True)
        
        return [{
            "camera_id": s.get("camera_id"),
            "avg_fps": s.get("avg_fps", 0),
            "stability_score": 100 - (s.get("reconnections", 0) * 10),
            "total_frames": s.get("total_frames", 0)
        } for s in sorted_streams[:5]]
    
    def _identify_problem_streams(self, enhanced_report: Dict) -> List[Dict]:
        """Identify problematic streams"""
        individual_streams = enhanced_report.get("raw_data", {}).get("individual_streams", [])
        
        problem_streams = []
        for stream in individual_streams:
            issues = []
            
            if stream.get("avg_fps", 0) < 5:
                issues.append("Low FPS")
            if stream.get("reconnections", 0) > 3:
                issues.append("Frequent reconnections")
            if len(stream.get("errors", [])) > 5:
                issues.append("High error rate")
            
            if issues:
                problem_streams.append({
                    "camera_id": stream.get("camera_id"),
                    "issues": issues,
                    "avg_fps": stream.get("avg_fps", 0),
                    "reconnections": stream.get("reconnections", 0),
                    "error_count": len(stream.get("errors", []))
                })
        
        return sorted(problem_streams, key=lambda s: len(s["issues"]), reverse=True)[:10]
    
    def _summarize_errors(self, enhanced_report: Dict) -> Dict:
        """Summarize error information"""
        individual_streams = enhanced_report.get("raw_data", {}).get("individual_streams", [])
        
        all_errors = []
        error_types = {}
        
        for stream in individual_streams:
            for error in stream.get("errors", []):
                all_errors.append(error)
                error_type = self._categorize_error_type(error)
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": len(all_errors),
            "error_types": error_types,
            "most_common_error": max(error_types.items(), key=lambda x: x[1]) if error_types else None,
            "error_rate": len(all_errors) / len(individual_streams) if individual_streams else 0
        }
    
    def _categorize_error_type(self, error: str) -> str:
        """Categorize error into type"""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return "timeout"
        elif "ssl" in error_lower:
            return "ssl"
        elif "500" in error:
            return "server_error"
        elif "network" in error_lower:
            return "network"
        else:
            return "other"
    
    def _generate_troubleshooting_guide(self, enhanced_report: Dict) -> List[Dict]:
        """Generate troubleshooting guide based on errors"""
        error_summary = self._summarize_errors(enhanced_report)
        guide = []
        
        for error_type, count in error_summary.get("error_types", {}).items():
            if error_type == "timeout":
                guide.append({
                    "error_type": error_type,
                    "frequency": count,
                    "steps": [
                        "Check network latency between client and camera servers",
                        "Verify camera server response times",
                        "Consider increasing timeout values",
                        "Monitor network bandwidth utilization"
                    ]
                })
            elif error_type == "ssl":
                guide.append({
                    "error_type": error_type,
                    "frequency": count,
                    "steps": [
                        "Verify SSL certificate validity",
                        "Check certificate chain",
                        "Update certificate store",
                        "Consider certificate pinning"
                    ]
                })
        
        return guide
    
    def _calculate_health_score(self, enhanced_report: Dict) -> int:
        """Calculate overall system health score (0-100)"""
        raw_data = enhanced_report.get("raw_data", {})
        
        # Factors contributing to health score
        fps_score = min(100, (raw_data.get("stream_performance", {}).get("average_fps", 0) / 30) * 100)
        cpu_score = max(0, 100 - raw_data.get("system_resources", {}).get("average_cpu_percent", 0))
        memory_score = max(0, 100 - raw_data.get("system_resources", {}).get("average_memory_percent", 0))
        
        # Connection stability
        total_reconnections = raw_data.get("stream_performance", {}).get("total_reconnections", 0)
        max_concurrent = raw_data.get("test_info", {}).get("max_concurrent_achieved", 1)
        stability_score = max(0, 100 - (total_reconnections / max_concurrent) * 50)
        
        # Weighted average
        health_score = (fps_score * 0.3 + cpu_score * 0.2 + memory_score * 0.2 + stability_score * 0.3)
        
        return int(health_score)
    
    def _assess_system_health(self, enhanced_report: Dict) -> str:
        """Assess overall system health status"""
        health_score = self._calculate_health_score(enhanced_report)
        
        if health_score >= 85:
            return "excellent"
        elif health_score >= 70:
            return "good"
        elif health_score >= 50:
            return "fair"
        else:
            return "poor"
    
    def _list_available_datasets(self, enhanced_report: Dict) -> List[str]:
        """List available datasets for data science analysis"""
        return [
            "individual_stream_performance.csv",
            "system_metrics_timeseries.csv", 
            "error_logs.json",
            "performance_summary.json",
            "correlation_matrix.csv"
        ]
    
    def _create_priority_matrix(self, enhanced_report: Dict) -> Dict:
        """Create priority matrix for actions"""
        alerts = enhanced_report.get("alerts", {})
        recommendations = enhanced_report.get("recommendations", {})
        
        matrix = {
            "high_impact_urgent": [],
            "high_impact_not_urgent": [],
            "low_impact_urgent": [],
            "low_impact_not_urgent": []
        }
        
        # Classify alerts
        for alert in alerts.get("critical", []):
            matrix["high_impact_urgent"].append({
                "type": "alert",
                "message": alert.get("message", ""),
                "action": alert.get("recommendation", "")
            })
        
        for alert in alerts.get("warning", []):
            matrix["high_impact_not_urgent"].append({
                "type": "alert",
                "message": alert.get("message", ""),
                "action": alert.get("recommendation", "")
            })
        
        # Classify recommendations
        for rec in recommendations.get("immediate_actions", []):
            matrix["high_impact_urgent"].append({
                "type": "recommendation",
                "message": rec.get("action", ""),
                "action": rec.get("steps", [])
            })
        
        return matrix
    
    def export_organized_data(self, organized_data: Dict, output_path: str):
        """Export organized data to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(organized_data, f, indent=2, default=str)
    
    def save_navigation_ui(self, organized_data: Dict, audience: str = "all") -> str:
        """Save navigation UI to HTML file"""
        html_content = self.generate_navigation_ui(organized_data, audience)
        
        output_file = self.output_dir / f"navigation_ui_{audience}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)