"""Retrieval: cosine + tag boosts."""

from __future__ import annotations

import math

import pytest

from whorl.kb.rag import cosine


def test_cosine_identical():
    v = [0.1, 0.2, 0.3]
    assert cosine(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal():
    assert cosine([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)


def test_cosine_empty():
    assert cosine([], [1, 2, 3]) == 0.0
    assert cosine([1, 2, 3], []) == 0.0
    assert cosine([0, 0, 0], [1, 2, 3]) == 0.0


def test_cosine_mismatched_length():
    assert cosine([1, 0], [1, 0, 0]) == 0.0


def test_cosine_known_value():
    a = [1.0, 1.0]
    b = [1.0, 0.0]
    # cos(45°) = √2/2
    assert cosine(a, b) == pytest.approx(math.sqrt(2) / 2)
