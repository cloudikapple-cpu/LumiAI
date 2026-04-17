"""Memory retention policies and TTL management."""

from datetime import datetime, timedelta
from typing import Protocol

from app.config import settings


class MemoryPolicy(Protocol):
    """Protocol for memory retention policies."""

    def get_ttl(self, category: str, importance: int) -> int | None:
        """Get TTL in seconds for a memory, or None for no expiration."""
        ...

    def should_retain(self, category: str, importance: int) -> bool:
        """Check if a memory should be retained."""
        ...


class DefaultMemoryPolicy:
    """
    Default memory retention policy.
    - High importance memories: 90 days
    - Medium importance: 30 days
    - Low importance: 7 days
    - Preferences: 1 year
    """

    CATEGORY_TTL = {
        "preference": 365 * 24 * 3600,
        "fact": 90 * 24 * 3600,
        "history": 30 * 24 * 3600,
        "summary": 7 * 24 * 3600,
    }

    def get_ttl(self, category: str, importance: int) -> int | None:
        """Get TTL based on category and importance."""
        if category in self.CATEGORY_TTL:
            return self.CATEGORY_TTL[category]

        if importance >= 3:
            return 90 * 24 * 3600
        elif importance >= 2:
            return 30 * 24 * 3600
        else:
            return 7 * 24 * 3600

    def should_retain(self, category: str, importance: int) -> bool:
        """Keep all explicitly stored memories."""
        return True


class AggressiveMemoryPolicy:
    """Aggressive memory policy - keeps everything for longer."""

    def get_ttl(self, category: str, importance: int) -> int | None:
        """Get extended TTL."""
        return 365 * 24 * 3600

    def should_retain(self, category: str, importance: int) -> bool:
        return True


class MinimalMemoryPolicy:
    """Minimal memory policy - keeps very little."""

    IMPORTANCE_THRESHOLD = 3

    def get_ttl(self, category: str, importance: int) -> int | None:
        """Get short TTL for low importance memories."""
        if importance >= self.IMPORTANCE_THRESHOLD:
            return 30 * 24 * 3600
        return 7 * 24 * 3600

    def should_retain(self, category: str, importance: int) -> bool:
        """Only retain high importance memories."""
        return importance >= self.IMPORTANCE_THRESHOLD


class MemoryPolicyManager:
    """Manages memory policies and applies them."""

    def __init__(self, policy: MemoryPolicy | None = None):
        self.policy = policy or DefaultMemoryPolicy()

    def set_policy(self, policy: MemoryPolicy) -> None:
        """Change the active memory policy."""
        self.policy = policy

    def get_ttl(self, category: str, importance: int) -> int | None:
        """Get TTL for a memory."""
        return self.policy.get_ttl(category, importance)

    def should_retain(self, category: str, importance: int) -> bool:
        """Check if memory should be retained."""
        return self.policy.should_retain(category, importance)

    def get_policy_summary(self) -> dict:
        """Get summary of current policy settings."""
        return {
            "policy_type": self.policy.__class__.__name__,
            "config": {
                "default_ttl_90_days": self.policy.get_ttl("any", 3) == 90 * 24 * 3600,
            },
        }


_policy_manager: MemoryPolicyManager | None = None


def get_memory_policy() -> MemoryPolicyManager:
    """Get the global memory policy manager."""
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = MemoryPolicyManager()
    return _policy_manager