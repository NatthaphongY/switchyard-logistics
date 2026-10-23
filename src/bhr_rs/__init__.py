"""BHR-RS reference implementation (stage P1).

Public entry points:
    bhr_rs.gate.evaluate            compliance gate, fourteen codes
    bhr_rs.planners.plan_greedy     baseline planner reproducing current practice
    bhr_rs.planners.plan_priced     congestion-priced planner
    bhr_rs.evaluate.run_ladder      paired measurement with a pre-registered ladder
"""

from .gate import Finding, Release, evaluate  # noqa: F401
from .model import Consignment, Lane, LegPlan, Network, Node, Plan, Thresholds  # noqa: F401
from .planners import plan_greedy, plan_priced, plan_with_composition  # noqa: F401

__all__ = [
    "Consignment",
    "Finding",
    "Lane",
    "LegPlan",
    "Network",
    "Node",
    "Plan",
    "Release",
    "Thresholds",
    "evaluate",
    "plan_greedy",
    "plan_priced",
    "plan_with_composition",
]

VERSION = "0.1.0"
