#!/usr/bin/env python3
"""
Actionable Insights System for Load Testing Results
===================================================

Provides intelligent, priority-based recommendations and step-by-step remediation guides.
Transforms raw test data into actionable insights that teams can immediately implement.

Features:
- Priority-based recommendation engine
- Step-by-step remediation guides
- Risk-impact matrices with decision trees
- Role-specific action plans
- Automated issue classification
- Progress tracking and validation
- Integration with ticketing systems
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
import hashlib

class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class ImpactLevel(Enum):
    SEVERE = 1      # System unusable
    MAJOR = 2       # Significant functionality affected
    MODERATE = 3    # Some functionality affected
    MINOR = 4       # Minimal impact

class Urgency(Enum):
    IMMEDIATE = 1   # Fix within hours
    URGENT = 2      # Fix within 1-2 days  
    NORMAL = 3      # Fix within 1 week
    LOW = 4         # Fix when convenient

class ActionType(Enum):
    INVESTIGATION = "investigation"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    CODE_CHANGE = "code_change"
    MONITORING = "monitoring"
    PROCESS = "process"
    TRAINING = "training"

@dataclass
class RemediationStep:
    """A single step in a remediation plan"""
    id: str
    title: str
    description: str
    action_type: ActionType
    estimated_time: str  # e.g., "30 minutes", "2 hours", "1 day"
    required_skills: List[str]
    required_tools: List[str]
    prerequisites: List[str] = field(default_factory=list)
    validation_criteria: str = ""
    automation_script: Optional[str] = None
    documentation_links: List[str] = field(default_factory=list)
    
@dataclass
class ActionableRecommendation:
    """A complete actionable recommendation"""
    id: str
    title: str
    description: str
    category: str
    priority: Priority
    impact: ImpactLevel
    urgency: Urgency
    confidence_score: float  # 0.0 to 1.0
    
    # Business context
    business_justification: str
    expected_outcome: str
    success_metrics: List[str]
    
    # Technical details
    root_cause: str
    affected_components: List[str]
    remediation_steps: List[RemediationStep]
    
    # Resource requirements
    estimated_effort: str
    required_roles: List[str]
    budget_estimate: Optional[str] = None
    
    # Timeline and dependencies
    target_resolution_time: str
    dependencies: List[str] = field(default_factory=list)
    
    # Risk assessment
    risk_of_inaction: str
    implementation_risks: List[str] = field(default_factory=list)
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    status: str = "open"  # open, in_progress, resolved, rejected
    
class DecisionNode:
    """Node in a decision tree for troubleshooting"""
    def __init__(self, condition: str, question: str, true_path=None, false_path=None, action=None):
        self.condition = condition
        self.question = question
        self.true_path = true_path
        self.false_path = false_path
        self.action = action

class ActionableInsightsSystem:
    """System for generating actionable insights and recommendations"""
    
    def __init__(self):
        self.recommendations_db = {}
        self.remediation_templates = {}
        self.decision_trees = {}
        self.issue_classifiers = {}
        
        # Initialize the system
        self._initialize_remediation_templates()
        self._initialize_decision_trees()
        self._initialize_issue_classifiers()
    
    def _initialize_remediation_templates(self):
        """Initialize templates for common remediation patterns"""
        
        # Network connectivity issues
        self.remediation_templates["network_connectivity"] = [
            RemediationStep(
                id="net_01",
                title="Verify Network Connectivity",
                description="Test basic network connectivity between client and camera servers",
                action_type=ActionType.INVESTIGATION,
                estimated_time="15 minutes",
                required_skills=["network_troubleshooting"],
                required_tools=["ping", "traceroute", "telnet"],
                validation_criteria="Ping response time < 50ms, no packet loss",
                automation_script="""
#!/bin/bash
# Network connectivity test
echo "Testing connectivity to camera servers..."
for server in $(cat camera_servers.txt); do
    echo "Testing $server..."
    ping -c 4 $server
    traceroute $server
done
                """,
                documentation_links=["https://wiki.company.com/network-troubleshooting"]
            ),
            RemediationStep(
                id="net_02", 
                title="Check Firewall Rules",
                description="Verify firewall rules allow traffic on required ports",
                action_type=ActionType.CONFIGURATION,
                estimated_time="20 minutes",
                required_skills=["firewall_management"],
                required_tools=["iptables", "firewall_console"],
                prerequisites=["net_01"],
                validation_criteria="Required ports (80, 443, 554) are open",
                automation_script="""
#!/bin/bash
# Check firewall rules
echo "Checking firewall rules for camera streaming ports..."
for port in 80 443 554; do
    iptables -L | grep $port || echo "Port $port may be blocked"
done
                """
            ),
            RemediationStep(
                id="net_03",
                title="Monitor Network Performance",
                description="Set up continuous monitoring of network performance",
                action_type=ActionType.MONITORING,
                estimated_time="1 hour",
                required_skills=["monitoring_setup"],
                required_tools=["monitoring_system"],
                prerequisites=["net_01", "net_02"],
                validation_criteria="Monitoring dashboard shows network metrics"
            )
        ]
        
        # Performance optimization
        self.remediation_templates["performance_optimization"] = [
            RemediationStep(
                id="perf_01",
                title="Analyze Resource Utilization",
                description="Review CPU, memory, and network utilization patterns",
                action_type=ActionType.INVESTIGATION,
                estimated_time="30 minutes",
                required_skills=["performance_analysis"],
                required_tools=["htop", "iotop", "nethogs"],
                validation_criteria="Resource utilization patterns identified"
            ),
            RemediationStep(
                id="perf_02",
                title="Optimize Connection Pool Settings",
                description="Tune connection pool parameters for better performance",
                action_type=ActionType.CONFIGURATION,
                estimated_time="45 minutes",
                required_skills=["application_tuning"],
                required_tools=["configuration_editor"],
                prerequisites=["perf_01"],
                validation_criteria="Connection pool metrics improved by 20%",
                automation_script="""
# Connection pool optimization
# Update application.conf
sed -i 's/max_connections=50/max_connections=100/' config/application.conf
sed -i 's/connection_timeout=30/connection_timeout=60/' config/application.conf
systemctl restart streaming_service
                """
            ),
            RemediationStep(
                id="perf_03",
                title="Implement Caching Strategy",
                description="Add caching layer to reduce server load",
                action_type=ActionType.CODE_CHANGE,
                estimated_time="4 hours",
                required_skills=["software_development", "caching"],
                required_tools=["redis", "development_environment"],
                prerequisites=["perf_01", "perf_02"],
                validation_criteria="Cache hit rate > 80%, response time improved by 30%"
            )
        ]
        
        # Capacity scaling
        self.remediation_templates["capacity_scaling"] = [
            RemediationStep(
                id="scale_01",
                title="Assess Current Capacity Limits",
                description="Determine exact bottlenecks preventing additional concurrent streams",
                action_type=ActionType.INVESTIGATION,
                estimated_time="1 hour",
                required_skills=["capacity_planning"],
                required_tools=["monitoring_tools", "profiling_tools"],
                validation_criteria="Bottlenecks identified and documented"
            ),
            RemediationStep(
                id="scale_02",
                title="Implement Horizontal Scaling",
                description="Add additional server instances to handle increased load",
                action_type=ActionType.INFRASTRUCTURE,
                estimated_time="4 hours",
                required_skills=["infrastructure_management", "load_balancing"],
                required_tools=["cloud_console", "load_balancer"],
                prerequisites=["scale_01"],
                validation_criteria="Additional instances deployed and load balanced"
            ),
            RemediationStep(
                id="scale_03",
                title="Configure Auto-scaling",
                description="Set up automatic scaling based on load metrics",
                action_type=ActionType.INFRASTRUCTURE,
                estimated_time="2 hours",
                required_skills=["auto_scaling", "monitoring"],
                required_tools=["cloud_console", "monitoring_system"],
                prerequisites=["scale_02"],
                validation_criteria="Auto-scaling triggers configured and tested"
            )
        ]
    
    def _initialize_decision_trees(self):
        """Initialize decision trees for different problem categories"""
        
        # Performance issues decision tree
        self.decision_trees["performance"] = DecisionNode(
            condition="avg_fps < 10",
            question="Is the average FPS below 10?",
            true_path=DecisionNode(
                condition="cpu_usage > 80",
                question="Is CPU usage above 80%?",
                true_path=DecisionNode(
                    condition="memory_usage > 80",
                    question="Is memory usage also above 80%?",
                    true_path="resource_scaling",
                    false_path="cpu_optimization"
                ),
                false_path=DecisionNode(
                    condition="reconnection_rate > 0.3",
                    question="Is the reconnection rate above 30%?",
                    true_path="network_connectivity",
                    false_path="application_optimization"
                )
            ),
            false_path=DecisionNode(
                condition="reconnection_rate > 0.2",
                question="Is the reconnection rate above 20%?",
                true_path="stability_improvement",
                false_path="minor_optimization"
            )
        )
        
        # Connectivity issues decision tree
        self.decision_trees["connectivity"] = DecisionNode(
            condition="total_errors > 50",
            question="Are there more than 50 total errors?",
            true_path=DecisionNode(
                condition="timeout_errors > 70%",
                question="Are more than 70% of errors timeout-related?",
                true_path="network_optimization",
                false_path="server_investigation"
            ),
            false_path="minor_connectivity_tuning"
        )
    
    def _initialize_issue_classifiers(self):
        """Initialize automated issue classifiers"""
        
        self.issue_classifiers = {
            "performance_degradation": {
                "conditions": [
                    lambda data: data.get("stream_performance", {}).get("average_fps", 0) < 15,
                    lambda data: data.get("test_info", {}).get("max_concurrent_achieved", 0) < data.get("test_info", {}).get("max_concurrent_target", 0) * 0.8
                ],
                "severity": ImpactLevel.MAJOR,
                "category": "performance"
            },
            "high_resource_usage": {
                "conditions": [
                    lambda data: data.get("system_resources", {}).get("average_cpu_percent", 0) > 80,
                    lambda data: data.get("system_resources", {}).get("average_memory_percent", 0) > 80
                ],
                "severity": ImpactLevel.MODERATE,
                "category": "resources"
            },
            "connectivity_instability": {
                "conditions": [
                    lambda data: data.get("stream_performance", {}).get("total_reconnections", 0) / max(1, data.get("test_info", {}).get("max_concurrent_achieved", 1)) > 0.2
                ],
                "severity": ImpactLevel.MAJOR,
                "category": "connectivity"
            },
            "error_surge": {
                "conditions": [
                    lambda data: sum(len(s.get("errors", [])) for s in data.get("individual_streams", [])) > 20
                ],
                "severity": ImpactLevel.MODERATE,
                "category": "errors"
            }
        }
    
    def generate_actionable_insights(self, enhanced_report: Dict) -> Dict:
        """Generate comprehensive actionable insights from test results"""
        
        insights = {
            "summary": self._generate_executive_summary(enhanced_report),
            "recommendations": self._generate_recommendations(enhanced_report),
            "decision_trees": self._generate_decision_guidance(enhanced_report),
            "priority_matrix": self._create_priority_matrix(enhanced_report),
            "implementation_roadmap": self._create_implementation_roadmap(enhanced_report),
            "risk_assessment": self._assess_risks(enhanced_report),
            "success_criteria": self._define_success_criteria(enhanced_report),
            "tracking_dashboard": self._create_tracking_dashboard_config(enhanced_report)
        }
        
        return insights
    
    def _generate_executive_summary(self, enhanced_report: Dict) -> Dict:
        """Generate executive summary of actionable insights"""
        
        recommendations = self._generate_recommendations(enhanced_report)
        
        critical_count = len([r for r in recommendations if r.priority == Priority.CRITICAL])
        high_count = len([r for r in recommendations if r.priority == Priority.HIGH])
        
        total_effort = self._estimate_total_effort(recommendations)
        
        return {
            "overall_health": self._assess_overall_health(enhanced_report),
            "immediate_attention_required": critical_count > 0,
            "total_recommendations": len(recommendations),
            "critical_issues": critical_count,
            "high_priority_issues": high_count,
            "estimated_total_effort": total_effort,
            "expected_improvement": self._estimate_improvement_potential(enhanced_report),
            "business_impact": self._assess_business_impact(enhanced_report),
            "top_3_actions": self._get_top_actions(recommendations)
        }
    
    def _generate_recommendations(self, enhanced_report: Dict) -> List[ActionableRecommendation]:
        """Generate specific actionable recommendations"""
        
        recommendations = []
        raw_data = enhanced_report.get("raw_data", {})
        
        # Classify issues automatically
        detected_issues = self._classify_issues(raw_data)
        
        # Generate recommendations for each issue
        for issue_type, issue_data in detected_issues.items():
            recommendations.extend(self._create_recommendations_for_issue(issue_type, issue_data, raw_data))
        
        # Add general optimization recommendations
        recommendations.extend(self._generate_optimization_recommendations(raw_data))
        
        # Sort by priority and impact
        recommendations.sort(key=lambda r: (r.priority.value, r.urgency.value))
        
        return recommendations
    
    def _classify_issues(self, raw_data: Dict) -> Dict:
        """Automatically classify issues based on test data"""
        
        detected_issues = {}
        
        for issue_type, classifier in self.issue_classifiers.items():
            conditions_met = 0
            total_conditions = len(classifier["conditions"])
            
            for condition in classifier["conditions"]:
                try:
                    if condition(raw_data):
                        conditions_met += 1
                except Exception:
                    pass  # Skip failed condition checks
            
            # If majority of conditions are met, classify as this issue
            if conditions_met >= total_conditions * 0.6:
                detected_issues[issue_type] = {
                    "severity": classifier["severity"],
                    "category": classifier["category"],
                    "confidence": conditions_met / total_conditions
                }
        
        return detected_issues
    
    def _create_recommendations_for_issue(self, issue_type: str, issue_data: Dict, raw_data: Dict) -> List[ActionableRecommendation]:
        """Create specific recommendations for a detected issue"""
        
        recommendations = []
        
        if issue_type == "performance_degradation":
            recommendations.append(ActionableRecommendation(
                id=f"rec_{issue_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                title="Optimize System Performance",
                description="System is experiencing performance degradation with low FPS and reduced capacity",
                category="performance",
                priority=Priority.HIGH,
                impact=issue_data["severity"],
                urgency=Urgency.URGENT,
                confidence_score=issue_data["confidence"],
                business_justification="Poor performance directly impacts monitoring quality and user experience",
                expected_outcome="Increase average FPS by 50% and improve system responsiveness",
                success_metrics=["Average FPS > 20", "CPU usage < 70%", "Response time < 2s"],
                root_cause="Resource bottlenecks and suboptimal configuration",
                affected_components=["streaming_service", "camera_connections", "resource_management"],
                remediation_steps=self.remediation_templates["performance_optimization"],
                estimated_effort="8 hours",
                required_roles=["DevOps Engineer", "Performance Engineer"],
                target_resolution_time="3 days",
                risk_of_inaction="Continued degradation may lead to service unavailability"
            ))
        
        elif issue_type == "high_resource_usage":
            recommendations.append(ActionableRecommendation(
                id=f"rec_{issue_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                title="Address High Resource Utilization",
                description="System resources are near capacity limits",
                category="infrastructure",
                priority=Priority.HIGH,
                impact=issue_data["severity"],
                urgency=Urgency.NORMAL,
                confidence_score=issue_data["confidence"],
                business_justification="High resource usage indicates imminent scaling needs",
                expected_outcome="Reduce resource utilization to safe levels (< 70%)",
                success_metrics=["CPU usage < 70%", "Memory usage < 70%", "Sustained performance"],
                root_cause="Insufficient capacity for current workload",
                affected_components=["compute_resources", "memory_management"],
                remediation_steps=self.remediation_templates["capacity_scaling"],
                estimated_effort="6 hours",
                required_roles=["Infrastructure Engineer", "DevOps Engineer"],
                budget_estimate="$500-2000/month for additional resources",
                target_resolution_time="1 week",
                risk_of_inaction="System failure under peak load"
            ))
        
        elif issue_type == "connectivity_instability":
            recommendations.append(ActionableRecommendation(
                id=f"rec_{issue_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                title="Improve Connection Stability",
                description="High rate of reconnections indicates network or server instability",
                category="networking",
                priority=Priority.CRITICAL,
                impact=issue_data["severity"],
                urgency=Urgency.IMMEDIATE,
                confidence_score=issue_data["confidence"],
                business_justification="Connection instability affects monitoring reliability and data quality",
                expected_outcome="Reduce reconnection rate to < 5%",
                success_metrics=["Reconnection rate < 5%", "Connection uptime > 99%", "Stable data flow"],
                root_cause="Network instability or server capacity issues",
                affected_components=["network_infrastructure", "connection_management", "camera_servers"],
                remediation_steps=self.remediation_templates["network_connectivity"],
                estimated_effort="4 hours",
                required_roles=["Network Engineer", "DevOps Engineer"],
                target_resolution_time="24 hours",
                risk_of_inaction="Critical data loss and monitoring gaps",
                implementation_risks=["Temporary service interruption during fixes"]
            ))
        
        return recommendations
    
    def _generate_optimization_recommendations(self, raw_data: Dict) -> List[ActionableRecommendation]:
        """Generate general optimization recommendations"""
        
        recommendations = []
        
        # Monitoring enhancement
        recommendations.append(ActionableRecommendation(
            id=f"rec_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="Enhance Monitoring and Alerting",
            description="Implement comprehensive monitoring to prevent future issues",
            category="monitoring",
            priority=Priority.MEDIUM,
            impact=ImpactLevel.MODERATE,
            urgency=Urgency.NORMAL,
            confidence_score=0.9,
            business_justification="Proactive monitoring reduces downtime and improves reliability",
            expected_outcome="Early detection of issues and faster resolution times",
            success_metrics=["Alert response time < 5 minutes", "99% uptime monitoring", "Automated health checks"],
            root_cause="Insufficient visibility into system performance",
            affected_components=["monitoring_system", "alerting_system"],
            remediation_steps=[
                RemediationStep(
                    id="mon_01",
                    title="Deploy Comprehensive Monitoring",
                    description="Set up Grafana dashboards and Prometheus metrics",
                    action_type=ActionType.MONITORING,
                    estimated_time="4 hours",
                    required_skills=["monitoring_setup", "grafana", "prometheus"],
                    required_tools=["grafana", "prometheus", "alertmanager"],
                    validation_criteria="All key metrics visible in dashboard"
                ),
                RemediationStep(
                    id="mon_02",
                    title="Configure Intelligent Alerting",
                    description="Set up smart alerts with appropriate thresholds",
                    action_type=ActionType.CONFIGURATION,
                    estimated_time="2 hours",
                    required_skills=["alerting_configuration"],
                    required_tools=["alertmanager", "notification_system"],
                    prerequisites=["mon_01"],
                    validation_criteria="Test alerts triggered and delivered successfully"
                )
            ],
            estimated_effort="6 hours",
            required_roles=["DevOps Engineer", "Monitoring Specialist"],
            target_resolution_time="1 week",
            risk_of_inaction="Continued blind spots in system visibility"
        ))
        
        # Documentation and runbooks
        recommendations.append(ActionableRecommendation(
            id=f"rec_documentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="Create Operational Runbooks",
            description="Develop comprehensive runbooks for common issues and procedures",
            category="process",
            priority=Priority.LOW,
            impact=ImpactLevel.MINOR,
            urgency=Urgency.LOW,
            confidence_score=0.8,
            business_justification="Runbooks improve response times and reduce human error",
            expected_outcome="Faster issue resolution and consistent procedures",
            success_metrics=["All common issues documented", "Response time reduced by 30%", "Procedure compliance > 95%"],
            root_cause="Lack of standardized procedures",
            affected_components=["operations_team", "documentation_system"],
            remediation_steps=[
                RemediationStep(
                    id="doc_01",
                    title="Document Common Troubleshooting Procedures",
                    description="Create step-by-step guides for frequent issues",
                    action_type=ActionType.PROCESS,
                    estimated_time="8 hours",
                    required_skills=["technical_writing", "troubleshooting"],
                    required_tools=["documentation_platform"],
                    validation_criteria="Runbooks tested and validated by team"
                )
            ],
            estimated_effort="8 hours",
            required_roles=["Senior Engineer", "Technical Writer"],
            target_resolution_time="2 weeks",
            risk_of_inaction="Inconsistent response to incidents"
        ))
        
        return recommendations
    
    def _generate_decision_guidance(self, enhanced_report: Dict) -> Dict:
        """Generate decision tree guidance for troubleshooting"""
        
        guidance = {}
        raw_data = enhanced_report.get("raw_data", {})
        
        # Evaluate each decision tree
        for tree_name, tree_root in self.decision_trees.items():
            guidance[tree_name] = self._traverse_decision_tree(tree_root, raw_data)
        
        return guidance
    
    def _traverse_decision_tree(self, node: DecisionNode, data: Dict) -> Dict:
        """Traverse a decision tree and return guidance"""
        
        if isinstance(node, str):
            # Leaf node - return action
            return {
                "action": node,
                "path": [],
                "confidence": 0.9
            }
        
        if node.action:
            # Action node
            return {
                "action": node.action,
                "path": [node.question],
                "confidence": 0.8
            }
        
        # Evaluate condition
        condition_result = self._evaluate_condition(node.condition, data)
        
        if condition_result:
            sub_result = self._traverse_decision_tree(node.true_path, data)
            sub_result["path"] = [f"{node.question} → YES"] + sub_result.get("path", [])
            return sub_result
        else:
            sub_result = self._traverse_decision_tree(node.false_path, data)
            sub_result["path"] = [f"{node.question} → NO"] + sub_result.get("path", [])
            return sub_result
    
    def _evaluate_condition(self, condition: str, data: Dict) -> bool:
        """Evaluate a condition string against data"""
        
        try:
            # Simple condition evaluation
            if "avg_fps < 10" in condition:
                return data.get("stream_performance", {}).get("average_fps", 0) < 10
            elif "cpu_usage > 80" in condition:
                return data.get("system_resources", {}).get("average_cpu_percent", 0) > 80
            elif "memory_usage > 80" in condition:
                return data.get("system_resources", {}).get("average_memory_percent", 0) > 80
            elif "reconnection_rate > 0.3" in condition:
                total_reconnections = data.get("stream_performance", {}).get("total_reconnections", 0)
                max_concurrent = data.get("test_info", {}).get("max_concurrent_achieved", 1)
                return (total_reconnections / max_concurrent) > 0.3
            elif "reconnection_rate > 0.2" in condition:
                total_reconnections = data.get("stream_performance", {}).get("total_reconnections", 0)
                max_concurrent = data.get("test_info", {}).get("max_concurrent_achieved", 1)
                return (total_reconnections / max_concurrent) > 0.2
            elif "total_errors > 50" in condition:
                total_errors = sum(len(s.get("errors", [])) for s in data.get("individual_streams", []))
                return total_errors > 50
            elif "timeout_errors > 70%" in condition:
                all_errors = []
                for stream in data.get("individual_streams", []):
                    all_errors.extend(stream.get("errors", []))
                timeout_errors = [e for e in all_errors if "timeout" in e.lower()]
                return len(timeout_errors) / max(1, len(all_errors)) > 0.7
            
            return False
        except Exception:
            return False
    
    def _create_priority_matrix(self, enhanced_report: Dict) -> Dict:
        """Create a priority matrix for decision making"""
        
        recommendations = self._generate_recommendations(enhanced_report)
        
        matrix = {
            "high_impact_urgent": [],
            "high_impact_not_urgent": [],
            "low_impact_urgent": [],
            "low_impact_not_urgent": []
        }
        
        for rec in recommendations:
            impact_high = rec.impact in [ImpactLevel.SEVERE, ImpactLevel.MAJOR]
            urgency_high = rec.urgency in [Urgency.IMMEDIATE, Urgency.URGENT]
            
            if impact_high and urgency_high:
                matrix["high_impact_urgent"].append(rec)
            elif impact_high and not urgency_high:
                matrix["high_impact_not_urgent"].append(rec)
            elif not impact_high and urgency_high:
                matrix["low_impact_urgent"].append(rec)
            else:
                matrix["low_impact_not_urgent"].append(rec)
        
        return matrix
    
    def _create_implementation_roadmap(self, enhanced_report: Dict) -> Dict:
        """Create a phased implementation roadmap"""
        
        recommendations = self._generate_recommendations(enhanced_report)
        
        roadmap = {
            "phase_1_immediate": {
                "timeframe": "0-3 days",
                "focus": "Critical issues and quick wins",
                "actions": []
            },
            "phase_2_short_term": {
                "timeframe": "1-2 weeks", 
                "focus": "High-impact improvements",
                "actions": []
            },
            "phase_3_medium_term": {
                "timeframe": "1-3 months",
                "focus": "Strategic enhancements",
                "actions": []
            },
            "phase_4_long_term": {
                "timeframe": "3-12 months",
                "focus": "Optimization and innovation",
                "actions": []
            }
        }
        
        for rec in recommendations:
            if rec.urgency == Urgency.IMMEDIATE:
                roadmap["phase_1_immediate"]["actions"].append(rec)
            elif rec.urgency == Urgency.URGENT:
                roadmap["phase_2_short_term"]["actions"].append(rec)
            elif rec.urgency == Urgency.NORMAL:
                roadmap["phase_3_medium_term"]["actions"].append(rec)
            else:
                roadmap["phase_4_long_term"]["actions"].append(rec)
        
        return roadmap
    
    def _assess_risks(self, enhanced_report: Dict) -> Dict:
        """Assess risks of current state and proposed changes"""
        
        raw_data = enhanced_report.get("raw_data", {})
        
        risks = {
            "current_state_risks": [],
            "implementation_risks": [],
            "mitigation_strategies": []
        }
        
        # Current state risks
        avg_fps = raw_data.get("stream_performance", {}).get("average_fps", 0)
        if avg_fps < 10:
            risks["current_state_risks"].append({
                "risk": "Service degradation",
                "probability": "high",
                "impact": "severe",
                "description": "Low FPS may render monitoring system ineffective"
            })
        
        cpu_usage = raw_data.get("system_resources", {}).get("average_cpu_percent", 0)
        if cpu_usage > 85:
            risks["current_state_risks"].append({
                "risk": "System failure",
                "probability": "medium",
                "impact": "severe",
                "description": "High CPU usage may lead to system crash under peak load"
            })
        
        # Implementation risks
        risks["implementation_risks"].append({
            "risk": "Service interruption during deployment",
            "probability": "low",
            "impact": "moderate",
            "description": "Configuration changes may temporarily affect service availability"
        })
        
        # Mitigation strategies
        risks["mitigation_strategies"].extend([
            "Implement changes during maintenance windows",
            "Use blue-green deployment strategies",
            "Maintain rollback plans for all changes",
            "Test changes in staging environment first"
        ])
        
        return risks
    
    def _define_success_criteria(self, enhanced_report: Dict) -> Dict:
        """Define clear success criteria for improvements"""
        
        current_metrics = self._extract_current_metrics(enhanced_report)
        
        return {
            "performance_targets": {
                "average_fps": {
                    "current": current_metrics["avg_fps"],
                    "target": max(20, current_metrics["avg_fps"] * 1.5),
                    "measurement": "Average FPS across all streams"
                },
                "cpu_utilization": {
                    "current": current_metrics["cpu_usage"],
                    "target": min(70, current_metrics["cpu_usage"] * 0.8),
                    "measurement": "Average CPU utilization percentage"
                },
                "connection_stability": {
                    "current": current_metrics["reconnection_rate"],
                    "target": 0.05,
                    "measurement": "Reconnections per stream ratio"
                }
            },
            "business_kpis": {
                "system_availability": {
                    "target": "99.9%",
                    "measurement": "Uptime percentage"
                },
                "monitoring_coverage": {
                    "target": "100%",
                    "measurement": "Percentage of cameras with active monitoring"
                }
            },
            "operational_metrics": {
                "incident_response_time": {
                    "target": "< 15 minutes",
                    "measurement": "Time from alert to response"
                },
                "resolution_time": {
                    "target": "< 2 hours",
                    "measurement": "Time from incident to resolution"
                }
            }
        }
    
    def _create_tracking_dashboard_config(self, enhanced_report: Dict) -> Dict:
        """Create configuration for tracking dashboard"""
        
        return {
            "dashboard_sections": [
                {
                    "title": "Performance Metrics",
                    "metrics": ["avg_fps", "cpu_usage", "memory_usage", "network_throughput"],
                    "chart_type": "time_series",
                    "refresh_interval": "30s"
                },
                {
                    "title": "Stability Indicators", 
                    "metrics": ["reconnection_rate", "error_count", "uptime_percentage"],
                    "chart_type": "gauge",
                    "refresh_interval": "1m"
                },
                {
                    "title": "Recommendation Status",
                    "metrics": ["open_recommendations", "in_progress", "completed"],
                    "chart_type": "status_board",
                    "refresh_interval": "5m"
                }
            ],
            "alerting_rules": [
                {
                    "metric": "avg_fps",
                    "condition": "< 15",
                    "severity": "warning",
                    "notification_channels": ["email", "slack"]
                },
                {
                    "metric": "cpu_usage",
                    "condition": "> 80",
                    "severity": "critical",
                    "notification_channels": ["email", "slack", "pagerduty"]
                }
            ]
        }
    
    # Helper methods
    def _assess_overall_health(self, enhanced_report: Dict) -> str:
        """Assess overall system health"""
        issues = self._classify_issues(enhanced_report.get("raw_data", {}))
        critical_issues = [i for i in issues.values() if i["severity"] == ImpactLevel.SEVERE]
        major_issues = [i for i in issues.values() if i["severity"] == ImpactLevel.MAJOR]
        
        if critical_issues:
            return "critical"
        elif len(major_issues) > 2:
            return "poor"
        elif major_issues:
            return "fair"
        else:
            return "good"
    
    def _estimate_total_effort(self, recommendations: List[ActionableRecommendation]) -> str:
        """Estimate total effort for all recommendations"""
        # Simple effort estimation (in reality, this would be more sophisticated)
        total_hours = 0
        
        for rec in recommendations:
            if "hour" in rec.estimated_effort:
                hours = int(rec.estimated_effort.split()[0])
                total_hours += hours
            elif "day" in rec.estimated_effort:
                days = int(rec.estimated_effort.split()[0])
                total_hours += days * 8
        
        if total_hours < 8:
            return f"{total_hours} hours"
        else:
            return f"{total_hours // 8} days"
    
    def _estimate_improvement_potential(self, enhanced_report: Dict) -> Dict:
        """Estimate potential improvement from implementing recommendations"""
        current_metrics = self._extract_current_metrics(enhanced_report)
        
        return {
            "performance_improvement": "30-50% FPS increase",
            "stability_improvement": "80% reduction in reconnections",
            "efficiency_improvement": "20-30% resource optimization",
            "reliability_improvement": "99.9% uptime achievement"
        }
    
    def _assess_business_impact(self, enhanced_report: Dict) -> Dict:
        """Assess business impact of current issues"""
        return {
            "monitoring_effectiveness": "Currently reduced by poor performance",
            "operational_cost": "Higher due to manual interventions",
            "reliability_impact": "Medium risk to service availability",
            "user_satisfaction": "May be affected by service issues"
        }
    
    def _get_top_actions(self, recommendations: List[ActionableRecommendation]) -> List[Dict]:
        """Get top 3 priority actions"""
        top_recs = sorted(recommendations, key=lambda r: (r.priority.value, r.urgency.value))[:3]
        
        return [{
            "title": rec.title,
            "priority": rec.priority.name,
            "effort": rec.estimated_effort,
            "timeline": rec.target_resolution_time
        } for rec in top_recs]
    
    def _extract_current_metrics(self, enhanced_report: Dict) -> Dict:
        """Extract current metrics for comparison"""
        raw_data = enhanced_report.get("raw_data", {})
        
        total_reconnections = raw_data.get("stream_performance", {}).get("total_reconnections", 0)
        max_concurrent = raw_data.get("test_info", {}).get("max_concurrent_achieved", 1)
        
        return {
            "avg_fps": raw_data.get("stream_performance", {}).get("average_fps", 0),
            "cpu_usage": raw_data.get("system_resources", {}).get("average_cpu_percent", 0),
            "memory_usage": raw_data.get("system_resources", {}).get("average_memory_percent", 0),
            "reconnection_rate": total_reconnections / max_concurrent
        }
    
    def export_recommendations(self, recommendations: List[ActionableRecommendation], output_format: str = "json") -> str:
        """Export recommendations in specified format"""
        
        if output_format == "json":
            return json.dumps([asdict(rec) for rec in recommendations], indent=2, default=str)
        
        elif output_format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            fieldnames = ["id", "title", "priority", "impact", "urgency", "effort", "timeline", "confidence"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for rec in recommendations:
                writer.writerow({
                    "id": rec.id,
                    "title": rec.title,
                    "priority": rec.priority.name,
                    "impact": rec.impact.name,
                    "urgency": rec.urgency.name,
                    "effort": rec.estimated_effort,
                    "timeline": rec.target_resolution_time,
                    "confidence": rec.confidence_score
                })
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def generate_ticket_integration_data(self, recommendations: List[ActionableRecommendation]) -> List[Dict]:
        """Generate data for integration with ticketing systems"""
        
        tickets = []
        
        for rec in recommendations:
            ticket = {
                "title": rec.title,
                "description": rec.description,
                "priority": rec.priority.name.lower(),
                "labels": [rec.category, f"impact-{rec.impact.name.lower()}", f"urgency-{rec.urgency.name.lower()}"],
                "assignee": rec.assigned_to,
                "estimated_effort": rec.estimated_effort,
                "due_date": rec.target_resolution_time,
                "acceptance_criteria": rec.success_metrics,
                "technical_details": {
                    "root_cause": rec.root_cause,
                    "affected_components": rec.affected_components,
                    "remediation_steps": [asdict(step) for step in rec.remediation_steps]
                },
                "business_justification": rec.business_justification,
                "risk_assessment": {
                    "risk_of_inaction": rec.risk_of_inaction,
                    "implementation_risks": rec.implementation_risks
                }
            }
            
            tickets.append(ticket)
        
        return tickets