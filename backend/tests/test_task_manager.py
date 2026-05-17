"""Tests for TaskManager, Task, and TaskStatus."""

import time
import threading
from datetime import datetime, timedelta

import pytest

from app.models.task import TaskManager, Task, TaskStatus


class TestTaskStatus:
    def test_enum_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_enum_membership(self):
        valid = {s.value for s in TaskStatus}
        for v in ("pending", "processing", "completed", "failed"):
            assert v in valid


class TestTask:
    def test_task_creation_defaults(self):
        now = datetime.now()
        task = Task(
            task_id="t1",
            task_type="test",
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        assert task.progress == 0
        assert task.message == ""
        assert task.result is None
        assert task.error is None
        assert task.metadata == {}
        assert task.progress_detail == {}

    def test_to_dict(self):
        now = datetime.now()
        task = Task(
            task_id="t1",
            task_type="build_graph",
            status=TaskStatus.PROCESSING,
            created_at=now,
            updated_at=now,
            progress=50,
            message="halfway there",
            result=None,
            metadata={"graph_id": "g-001"},
            progress_detail={"chunks": 5, "total_chunks": 10},
        )
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["task_type"] == "build_graph"
        assert d["status"] == "processing"
        assert d["progress"] == 50
        assert d["message"] == "halfway there"
        assert d["metadata"] == {"graph_id": "g-001"}
        assert d["progress_detail"] == {"chunks": 5, "total_chunks": 10}
        assert d["result"] is None
        assert d["error"] is None
        assert "created_at" in d
        assert "updated_at" in d

    def test_to_dict_completed(self):
        now = datetime.now()
        task = Task(
            task_id="t2",
            task_type="report",
            status=TaskStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            progress=100,
            message="done",
            result={"report_id": "r-001"},
        )
        d = task.to_dict()
        assert d["status"] == "completed"
        assert d["result"] == {"report_id": "r-001"}

    def test_to_dict_failed(self):
        now = datetime.now()
        task = Task(
            task_id="t3",
            task_type="simulation",
            status=TaskStatus.FAILED,
            created_at=now,
            updated_at=now,
            error="Something went wrong",
        )
        d = task.to_dict()
        assert d["status"] == "failed"
        assert d["error"] == "Something went wrong"


class TestTaskManager:
    def test_singleton(self):
        tm1 = TaskManager()
        tm2 = TaskManager()
        assert tm1 is tm2

    def test_create_task(self):
        tm = TaskManager()
        task_id = tm.create_task("build_graph", metadata={"project": "p1"})
        assert task_id.startswith("task_") or isinstance(task_id, str)
        task = tm.get_task(task_id)
        assert task is not None
        assert task.task_type == "build_graph"
        assert task.status == TaskStatus.PENDING
        assert task.metadata == {"project": "p1"}

    def test_get_task_not_found(self):
        tm = TaskManager()
        assert tm.get_task("nonexistent") is None

    def test_update_task(self):
        tm = TaskManager()
        task_id = tm.create_task("test")
        tm.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=30,
            message="processing",
            progress_detail={"step": "parsing"},
        )
        task = tm.get_task(task_id)
        assert task.status == TaskStatus.PROCESSING
        assert task.progress == 30
        assert task.message == "processing"
        assert task.progress_detail == {"step": "parsing"}

    def test_update_task_nonexistent_does_not_raise(self):
        tm = TaskManager()
        tm.update_task("no-such-id", status=TaskStatus.PROCESSING)

    def test_complete_task(self):
        tm = TaskManager()
        task_id = tm.create_task("test")
        tm.complete_task(task_id, result={"key": "value"})
        task = tm.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 100
        assert task.message == "任务完成"
        assert task.result == {"key": "value"}

    def test_fail_task(self):
        tm = TaskManager()
        task_id = tm.create_task("test")
        tm.fail_task(task_id, "error occurred")
        task = tm.get_task(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.message == "任务失败"
        assert task.error == "error occurred"

    def test_list_tasks_ordered_by_creation(self):
        tm = TaskManager()
        id1 = tm.create_task("type_a")
        time.sleep(0.01)
        id2 = tm.create_task("type_a")
        time.sleep(0.01)
        id3 = tm.create_task("type_b")

        all_tasks = tm.list_tasks()
        assert len(all_tasks) == 3
        assert all_tasks[0]["task_id"] == id3
        assert all_tasks[2]["task_id"] == id1

    def test_list_tasks_filter_by_type(self):
        tm = TaskManager()
        tm.create_task("type_a")
        tm.create_task("type_b")
        tm.create_task("type_a")
        a_tasks = tm.list_tasks(task_type="type_a")
        assert len(a_tasks) == 2
        assert all(t["task_type"] == "type_a" for t in a_tasks)

    def test_cleanup_old_tasks(self):
        tm = TaskManager()
        old_id = tm.create_task("old")
        new_id = tm.create_task("new")

        old = tm.get_task(old_id)
        old.created_at = datetime.now() - timedelta(hours=48)
        old.updated_at = datetime.now() - timedelta(hours=48)

        # Mark only the old one as completed so it's eligible for cleanup
        tm.complete_task(old_id, result={})

        tm.cleanup_old_tasks(max_age_hours=24)
        assert tm.get_task(old_id) is None
        assert tm.get_task(new_id) is not None

    def test_cleanup_old_tasks_skips_pending(self):
        tm = TaskManager()
        old_id = tm.create_task("old")
        old = tm.get_task(old_id)
        old.created_at = datetime.now() - timedelta(hours=48)
        old.updated_at = datetime.now() - timedelta(hours=48)

        tm.cleanup_old_tasks(max_age_hours=24)
        # The task is still pending, so it should NOT be cleaned up
        assert tm.get_task(old_id) is not None

    def test_thread_safety(self):
        """Multiple threads should be able to create tasks concurrently."""
        tm = TaskManager()
        ids = []
        errors = []

        def create():
            try:
                tid = tm.create_task("concurrent")
                ids.append(tid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(ids) == 20
        assert len(set(ids)) == 20  # all unique
