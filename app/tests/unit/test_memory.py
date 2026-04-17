"""Unit tests for memory modules."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.memory.policies import (
    DefaultMemoryPolicy,
    AggressiveMemoryPolicy,
    MinimalMemoryPolicy,
    MemoryPolicyManager,
)


class TestDefaultMemoryPolicy:
    """Tests for DefaultMemoryPolicy."""

    @pytest.fixture
    def policy(self):
        """Create a default policy instance."""
        return DefaultMemoryPolicy()

    def test_get_ttl_for_preference(self, policy):
        """Test TTL for preference category."""
        ttl = policy.get_ttl("preference", importance=2)
        assert ttl == 365 * 24 * 3600

    def test_get_ttl_for_fact(self, policy):
        """Test TTL for fact category."""
        ttl = policy.get_ttl("fact", importance=3)
        assert ttl == 90 * 24 * 3600

    def test_get_ttl_for_high_importance(self, policy):
        """Test TTL for high importance generic memory."""
        ttl = policy.get_ttl("unknown", importance=3)
        assert ttl == 90 * 24 * 3600

    def test_get_ttl_for_low_importance(self, policy):
        """Test TTL for low importance generic memory."""
        ttl = policy.get_ttl("unknown", importance=1)
        assert ttl == 7 * 24 * 3600

    def test_should_retain_always(self, policy):
        """Test that default policy retains all memories."""
        assert policy.should_retain("preference", importance=1) is True
        assert policy.should_retain("fact", importance=5) is True
        assert policy.should_retain("unknown", importance=1) is True


class TestAggressiveMemoryPolicy:
    """Tests for AggressiveMemoryPolicy."""

    @pytest.fixture
    def policy(self):
        """Create an aggressive policy instance."""
        return AggressiveMemoryPolicy()

    def test_extended_ttl(self, policy):
        """Test that aggressive policy uses extended TTL."""
        ttl = policy.get_ttl("preference", importance=1)
        assert ttl == 365 * 24 * 3600

    def test_should_retain_always(self, policy):
        """Test that aggressive policy retains all memories."""
        assert policy.should_retain("preference", importance=1) is True
        assert policy.should_retain("unknown", importance=1) is True


class TestMinimalMemoryPolicy:
    """Tests for MinimalMemoryPolicy."""

    @pytest.fixture
    def policy(self):
        """Create a minimal policy instance."""
        return MinimalMemoryPolicy()

    def test_threshold_filtering(self, policy):
        """Test that minimal policy filters by importance."""
        assert policy.should_retain("unknown", importance=5) is True
        assert policy.should_retain("unknown", importance=2) is False

    def test_short_ttl_for_low_importance(self, policy):
        """Test short TTL for low importance memories."""
        ttl = policy.get_ttl("unknown", importance=1)
        assert ttl == 7 * 24 * 3600

    def test_medium_ttl_for_high_importance(self, policy):
        """Test medium TTL for high importance memories."""
        ttl = policy.get_ttl("unknown", importance=5)
        assert ttl == 30 * 24 * 3600


class TestMemoryPolicyManager:
    """Tests for MemoryPolicyManager."""

    def test_default_policy(self):
        """Test manager uses default policy initially."""
        manager = MemoryPolicyManager()
        assert isinstance(manager.policy, DefaultMemoryPolicy)

    def test_change_policy(self):
        """Test changing the active policy."""
        manager = MemoryPolicyManager()
        new_policy = MinimalMemoryPolicy()
        manager.set_policy(new_policy)
        assert manager.policy == new_policy

    def test_get_ttl_delegates_to_policy(self):
        """Test that get_ttl delegates to the policy."""
        manager = MemoryPolicyManager(AggressiveMemoryPolicy())
        ttl = manager.get_ttl("preference", importance=1)
        assert ttl == 365 * 24 * 3600

    def test_should_retain_delegates_to_policy(self):
        """Test that should_retain delegates to the policy."""
        manager = MemoryPolicyManager(MinimalMemoryPolicy())
        assert manager.should_retain("unknown", importance=1) is False
        assert manager.should_retain("unknown", importance=5) is True

    def test_get_policy_summary(self):
        """Test getting policy summary."""
        manager = MemoryPolicyManager()
        summary = manager.get_policy_summary()
        assert "policy_type" in summary
        assert summary["policy_type"] == "DefaultMemoryPolicy"


class TestMemoryCategories:
    """Tests for memory category constants."""

    def test_long_term_memory_categories(self):
        """Test that LongTermMemory uses correct categories."""
        from app.memory.long_term import LongTermMemory

        assert LongTermMemory.CATEGORY_PREFERENCE == "preference"
        assert LongTermMemory.CATEGORY_FACT == "fact"
        assert LongTermMemory.CATEGORY_HISTORY == "history"
        assert LongTermMemory.CATEGORY_SUMMARY == "summary"