"""Shared fixtures and configuration for all tests."""

import os
import sys
import tempfile
import pytest

# Ensure the backend root is on sys.path so `app` is importable
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)


@pytest.fixture(autouse=True)
def _reset_task_manager():
    """Reset TaskManager singleton between tests so test isolation is preserved."""
    from app.models.task import TaskManager
    inst = TaskManager()
    with inst._task_lock:
        inst._tasks.clear()
    yield


@pytest.fixture
def temp_project_dir():
    """Provide a temporary directory that replaces ProjectManager.PROJECTS_DIR.

    After the test the directory is cleaned up automatically.
    """
    from app.models.project import ProjectManager
    original = ProjectManager.PROJECTS_DIR
    with tempfile.TemporaryDirectory(prefix="mf_test_") as tmp:
        ProjectManager.PROJECTS_DIR = tmp
        yield tmp
    ProjectManager.PROJECTS_DIR = original


@pytest.fixture
def sample_text():
    return (
        "人工智能正在深刻改变教育领域。个性化学习系统能够根据每个学生的特点调整教学内容。\n\n"
        "智能辅导系统可以实时回答学生的问题。数据分析技术帮助教师了解学生的学习情况。\n\n"
        "虚拟现实技术为学生提供沉浸式的学习体验。未来教育将更加注重培养学生的创新能力。"
    )
