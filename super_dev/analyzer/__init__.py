"""
Super Dev 项目分析器
用于自动检测和分析项目结构
"""

from .analyzer import ArchitectureReport, ProjectAnalyzer
from .baseline_audit import BaselineAuditBuilder, BaselineAuditReport
from .dependency_graph import (
    CriticalPath,
    DependencyEdge,
    DependencyGraphBuilder,
    DependencyGraphReport,
    DependencyNode,
)
from .detectors import detect_project_type, detect_tech_stack
from .feature_checklist import FeatureChecklistBuilder, FeatureChecklistItem, FeatureCoverageReport
from .impact import ImpactAnalysisReport, ImpactAnalyzer, ImpactItem
from .models import (
    ArchitecturePattern,
    Dependency,
    DesignPattern,
    FrameworkType,
    PatternType,
    ProjectCategory,
    ProjectType,
    TechStack,
)
from .product_audit import ProductAuditBuilder, ProductAuditFinding, ProductAuditReport
from .regression_guard import RegressionCheck, RegressionGuardBuilder, RegressionGuardReport
from .repo_map import RepoMapBuilder, RepoMapItem, RepoMapReport

__all__ = [
    "ProjectAnalyzer",
    "BaselineAuditBuilder",
    "BaselineAuditReport",
    "ProjectCategory",
    "ProjectType",
    "ArchitectureReport",
    "Dependency",
    "DesignPattern",
    "PatternType",
    "TechStack",
    "FrameworkType",
    "ArchitecturePattern",
    "RepoMapBuilder",
    "RepoMapItem",
    "RepoMapReport",
    "FeatureChecklistBuilder",
    "FeatureChecklistItem",
    "FeatureCoverageReport",
    "ImpactAnalyzer",
    "ImpactAnalysisReport",
    "ImpactItem",
    "ProductAuditBuilder",
    "ProductAuditFinding",
    "ProductAuditReport",
    "RegressionCheck",
    "RegressionGuardBuilder",
    "RegressionGuardReport",
    "DependencyEdge",
    "DependencyNode",
    "CriticalPath",
    "DependencyGraphBuilder",
    "DependencyGraphReport",
    "detect_project_type",
    "detect_tech_stack",
]
