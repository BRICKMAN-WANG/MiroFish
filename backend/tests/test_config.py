"""Tests for Config class."""

import os

import pytest

from app.config import Config


class TestConfig:
    def test_default_values(self):
        assert Config.MAX_CONTENT_LENGTH == 50 * 1024 * 1024
        assert Config.DEFAULT_CHUNK_SIZE == 500
        assert Config.DEFAULT_CHUNK_OVERLAP == 50
        assert Config.OASIS_DEFAULT_MAX_ROUNDS == 10
        assert Config.REPORT_AGENT_MAX_TOOL_CALLS == 5
        assert Config.JSON_AS_ASCII is False

    def test_allowed_extensions(self):
        assert "pdf" in Config.ALLOWED_EXTENSIONS
        assert "md" in Config.ALLOWED_EXTENSIONS
        assert "txt" in Config.ALLOWED_EXTENSIONS
        assert "markdown" in Config.ALLOWED_EXTENSIONS

    def test_oasis_twitter_actions(self):
        assert "CREATE_POST" in Config.OASIS_TWITTER_ACTIONS
        assert "DO_NOTHING" in Config.OASIS_TWITTER_ACTIONS

    def test_oasis_reddit_actions(self):
        assert "CREATE_COMMENT" in Config.OASIS_REDDIT_ACTIONS
        assert "TREND" in Config.OASIS_REDDIT_ACTIONS

    def test_validate_missing_keys(self):
        """validate should return errors when required keys are missing."""
        original_api_key = Config.LLM_API_KEY
        original_zep_key = Config.ZEP_API_KEY
        Config.LLM_API_KEY = None
        Config.ZEP_API_KEY = None
        try:
            errors = Config.validate()
            assert len(errors) == 2
            assert any("LLM_API_KEY" in e for e in errors)
            assert any("ZEP_API_KEY" in e for e in errors)
        finally:
            Config.LLM_API_KEY = original_api_key
            Config.ZEP_API_KEY = original_zep_key

    def test_validate_success(self):
        original_api_key = Config.LLM_API_KEY
        original_zep_key = Config.ZEP_API_KEY
        Config.LLM_API_KEY = "test-key"
        Config.ZEP_API_KEY = "test-zep-key"
        try:
            errors = Config.validate()
            assert errors == []
        finally:
            Config.LLM_API_KEY = original_api_key
            Config.ZEP_API_KEY = original_zep_key
