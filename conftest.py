import os
import sys
from unittest.mock import MagicMock

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))

# Add project root (for utils) and vision_nav/ (for vision_nav package) to sys.path
for _p in (ROOT, os.path.join(ROOT, "vision_nav")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Mock all ROS2/RMW packages before any test module is imported.
# This allows importing node files to extract pure functions without a ROS2 install.
_ROS_MOCKS = [
    "rclpy",
    "rclpy.qos",
    "rclpy.time",
    "rclpy.clock",
    "sensor_msgs",
    "sensor_msgs.msg",
    "geometry_msgs",
    "geometry_msgs.msg",
    "std_msgs",
    "std_msgs.msg",
    "cv_bridge",
]
for _mod in _ROS_MOCKS:
    sys.modules.setdefault(_mod, MagicMock())

# rclpy.node.Node must be a real class so subclasses (e.g. FieldTraverser)
# retain their own class-level attributes and don't get swallowed by MagicMock.
class _FakeNode:
    def __init__(self, *args, **kwargs):
        pass
    def get_logger(self):           return MagicMock()
    def get_clock(self):            return MagicMock()
    def create_subscription(self, *a, **kw): return MagicMock()
    def create_publisher(self, *a, **kw):    return MagicMock()
    def create_timer(self, *a, **kw):        return MagicMock()
    def declare_parameter(self, name, default):
        m = MagicMock()
        m.value = default
        return m
    def destroy_node(self): pass

_rclpy_node_mod = MagicMock()
_rclpy_node_mod.Node = _FakeNode
sys.modules["rclpy.node"] = _rclpy_node_mod


@pytest.fixture(autouse=True)
def project_root_cwd(monkeypatch):
    """Run every test with cwd = project root so template paths resolve correctly."""
    monkeypatch.chdir(ROOT)
