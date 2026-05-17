"""Tests for Project and ProjectManager."""

import os
import json
from datetime import datetime

import pytest

from app.models.project import Project, ProjectManager, ProjectStatus


class TestProject:
    def test_minimal_creation(self):
        p = Project(
            project_id="proj_test123",
            name="Test Project",
            status=ProjectStatus.CREATED,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert p.project_id == "proj_test123"
        assert p.name == "Test Project"
        assert p.status == ProjectStatus.CREATED
        assert p.files == []
        assert p.total_text_length == 0
        assert p.ontology is None
        assert p.error is None

    def test_to_dict(self):
        p = Project(
            project_id="proj_abc",
            name="My Project",
            status=ProjectStatus.ONTOLOGY_GENERATED,
            created_at="2025-06-01T12:00:00",
            updated_at="2025-06-01T12:30:00",
            files=[{"filename": "doc.pdf", "path": "/tmp/doc.pdf", "size": 1024}],
            total_text_length=5000,
            ontology={"entity_types": ["Person"]},
            analysis_summary="Some analysis",
            chunk_size=300,
            chunk_overlap=30,
        )
        d = p.to_dict()
        assert d["project_id"] == "proj_abc"
        assert d["status"] == "ontology_generated"
        assert d["ontology"] == {"entity_types": ["Person"]}
        assert d["chunk_size"] == 300

    def test_from_dict(self):
        raw = {
            "project_id": "proj_xyz",
            "name": "Restored",
            "status": "graph_completed",
            "created_at": "2025-06-10T00:00:00",
            "updated_at": "2025-06-10T01:00:00",
            "graph_id": "graph-001",
            "error": None,
        }
        p = Project.from_dict(raw)
        assert p.project_id == "proj_xyz"
        assert p.status == ProjectStatus.GRAPH_COMPLETED
        assert p.graph_id == "graph-001"
        assert p.error is None

    def test_from_dict_with_status_object(self):
        """from_dict should handle a status that is already a ProjectStatus enum."""
        raw = {
            "project_id": "proj_enum",
            "name": "EnumTest",
            "status": ProjectStatus.FAILED,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        p = Project.from_dict(raw)
        assert p.status == ProjectStatus.FAILED


class TestProjectManager:
    def test_create_project(self, temp_project_dir):
        p = ProjectManager.create_project("Integration Test")
        assert p.project_id.startswith("proj_")
        assert p.name == "Integration Test"
        assert p.status == ProjectStatus.CREATED

        # Verify project directory was created
        project_dir = os.path.join(temp_project_dir, p.project_id)
        assert os.path.isdir(project_dir)
        assert os.path.isdir(os.path.join(project_dir, "files"))

        # Verify metadata was written
        meta_path = os.path.join(project_dir, "project.json")
        assert os.path.isfile(meta_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["project_id"] == p.project_id

    def test_get_project(self, temp_project_dir):
        created = ProjectManager.create_project("GetTest")
        fetched = ProjectManager.get_project(created.project_id)
        assert fetched is not None
        assert fetched.project_id == created.project_id
        assert fetched.name == "GetTest"

    def test_get_project_not_found(self, temp_project_dir):
        assert ProjectManager.get_project("proj_nonexistent") is None

    def test_save_and_get_project_updates_updated_at(self, temp_project_dir):
        p = ProjectManager.create_project("SaveTest")
        original_updated = p.updated_at
        p.name = "Renamed"
        ProjectManager.save_project(p)
        fetched = ProjectManager.get_project(p.project_id)
        assert fetched.name == "Renamed"
        assert fetched.updated_at >= original_updated

    def test_list_projects(self, temp_project_dir):
        ProjectManager.create_project("First")
        ProjectManager.create_project("Second")
        projects = ProjectManager.list_projects()
        assert len(projects) == 2
        names = {p.name for p in projects}
        assert "First" in names
        assert "Second" in names

    def test_list_projects_limit(self, temp_project_dir):
        for i in range(5):
            ProjectManager.create_project(f"Proj-{i}")
        projects = ProjectManager.list_projects(limit=3)
        assert len(projects) == 3

    def test_delete_project(self, temp_project_dir):
        p = ProjectManager.create_project("DeleteMe")
        assert ProjectManager.delete_project(p.project_id) is True
        assert ProjectManager.get_project(p.project_id) is None

    def test_delete_project_nonexistent(self, temp_project_dir):
        assert ProjectManager.delete_project("proj_nope") is False

    def test_save_and_get_extracted_text(self, temp_project_dir):
        p = ProjectManager.create_project("TextTest")
        ProjectManager.save_extracted_text(p.project_id, "Hello world")
        text = ProjectManager.get_extracted_text(p.project_id)
        assert text == "Hello world"

    def test_get_extracted_text_not_found(self, temp_project_dir):
        assert ProjectManager.get_extracted_text("proj_nonexistent") is None

    def test_save_file_to_project(self, temp_project_dir):
        p = ProjectManager.create_project("FileTest")

        # Create a minimal file-like object
        class FakeFileStorage:
            def save(self, path):
                with open(path, "w") as f:
                    f.write("dummy content")

        info = ProjectManager.save_file_to_project(
            p.project_id, FakeFileStorage(), "report.pdf"
        )
        assert info["original_filename"] == "report.pdf"
        assert info["saved_filename"].endswith(".pdf")
        assert info["size"] > 0
        assert os.path.isfile(info["path"])

    def test_get_project_files(self, temp_project_dir):
        p = ProjectManager.create_project("FilesTest")

        class FakeFileStorage:
            def save(self, path):
                with open(path, "w") as f:
                    f.write("dummy")

        ProjectManager.save_file_to_project(p.project_id, FakeFileStorage(), "a.txt")
        ProjectManager.save_file_to_project(p.project_id, FakeFileStorage(), "b.txt")

        files = ProjectManager.get_project_files(p.project_id)
        assert len(files) == 2
