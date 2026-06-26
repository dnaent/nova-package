"""Smoke tests for nova-llm-router.

These exercise the public API surface and the pure token-budgeting logic
without requiring network access, API keys, or cloud credentials.
"""
import pytest

from nova_llm_router import llm_router
from nova_llm_router.llm_router import set_budget, TokenBudgetExceeded


def test_public_api_is_importable():
    """The documented entry points exist and are callable."""
    assert callable(llm_router.complete_async)
    assert callable(set_budget)


def test_set_budget_returns_fresh_budget():
    budget = set_budget(cap=5000)
    assert budget.cap == 5000
    assert budget.used == 0


def test_budget_tracks_usage():
    """A budget within the cap charges usage; over the cap it raises."""
    budget = set_budget(cap=100)
    budget.charge(40)
    assert budget.used == 40
    with pytest.raises(TokenBudgetExceeded):
        budget.charge(1000)
