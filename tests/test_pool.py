"""Tests for src.systems.pool — generic Pool[T] (BLOQUE 1)."""
from __future__ import annotations

import pytest

from src.systems.pool import Pool


class _Item:
    """Minimal PoolItem test double."""
    def __init__(self) -> None:
        self.active: bool = False
        self.spawn_calls: int = 0
        self.release_calls: int = 0

    def on_spawn(self) -> None:
        self.spawn_calls += 1

    def on_release(self) -> None:
        self.release_calls += 1


def test_pool_factory_runs_size_times() -> None:
    pool: Pool[_Item] = Pool(_Item, 50)
    assert pool.size == 50
    assert len(pool._items) == 50
    assert all(isinstance(it, _Item) for it in pool._items)


def test_acquire_returns_inactive_item_and_marks_active() -> None:
    pool: Pool[_Item] = Pool(_Item, 5)
    it = pool.acquire()
    assert it is not None
    assert it.active
    assert pool.active_count == 1


def test_acquire_calls_on_spawn() -> None:
    pool: Pool[_Item] = Pool(_Item, 5)
    it = pool.acquire()
    assert it is not None
    assert it.spawn_calls == 1
    assert it.release_calls == 0


def test_release_flips_flag_and_calls_on_release() -> None:
    pool: Pool[_Item] = Pool(_Item, 5)
    it = pool.acquire()
    assert it is not None
    pool.release(it)
    assert not it.active
    assert it.release_calls == 1
    assert pool.active_count == 0


def test_release_idempotent_on_inactive() -> None:
    """release() on already-released item is a no-op (no double-count)."""
    pool: Pool[_Item] = Pool(_Item, 5)
    it = pool.acquire()
    assert it is not None
    pool.release(it)
    pool.release(it)  # second call should be a no-op
    assert pool.active_count == 0
    assert it.release_calls == 1


def test_acquire_exhaustion_returns_none() -> None:
    """When all items are active, acquire() returns None silently."""
    pool: Pool[_Item] = Pool(_Item, 3)
    items = [pool.acquire() for _ in range(3)]
    assert all(it is not None for it in items)
    assert pool.is_full
    assert pool.acquire() is None


def test_release_then_acquire_returns_released_item() -> None:
    """Pool reuse: release one, acquire again, get the same one back."""
    pool: Pool[_Item] = Pool(_Item, 2)
    a = pool.acquire()
    b = pool.acquire()
    assert a is not None and b is not None
    assert pool.acquire() is None
    pool.release(a)
    again = pool.acquire()
    assert again is a  # the same instance


def test_release_all_clears_active() -> None:
    pool: Pool[_Item] = Pool(_Item, 5)
    [pool.acquire() for _ in range(5)]
    assert pool.is_full
    pool.release_all()
    assert pool.active_count == 0
    assert not pool.is_full


def test_high_watermark_tracks_peak() -> None:
    pool: Pool[_Item] = Pool(_Item, 10)
    [pool.acquire() for _ in range(7)]
    assert pool.high_watermark == 7
    pool.release(pool._items[0])
    assert pool.high_watermark == 7  # peak doesn't decrease


def test_for_each_active_skips_inactive() -> None:
    pool: Pool[_Item] = Pool(_Item, 5)
    a = pool.acquire()
    b = pool.acquire()
    assert a is not None and b is not None
    seen: list[_Item] = []
    pool.for_each_active(lambda it: seen.append(it))
    assert seen == [a, b]


def test_pool_rejects_zero_size() -> None:
    with pytest.raises(ValueError):
        Pool(_Item, 0)
    with pytest.raises(ValueError):
        Pool(_Item, -5)


def test_iter_yields_all_items() -> None:
    pool: Pool[_Item] = Pool(_Item, 3)
    all_items = list(pool)
    assert len(all_items) == 3
