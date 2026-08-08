"""Generic object pool with `active` flag + on_spawn/on_release hooks.

Migrated from nebula-hunter seed. Used by ParticleEngine, ProjectilePool,
EnemyPool, BossPool, DamagePopupPool, PowerUpPool. The `active` flag pattern
keeps the inner loop allocation-free — the engine never news objects at
runtime, it just flips flags.

Description: typed generic pool. acquire() returns inactive item or None
             if the pool is exhausted. release() flips the flag back and
             calls on_release() so per-kind cleanup (e.g. resetting particle
             state) happens in one place.
Dependencies: none.
"""
from __future__ import annotations

from typing import Callable, Generic, Iterator, Protocol, TypeVar


class PoolItem(Protocol):
    """Anything that has an `active: bool` field and optional hooks."""

    active: bool

    def on_spawn(self) -> None: ...
    def on_release(self) -> None: ...


T = TypeVar("T", bound=PoolItem)


class Pool(Generic[T]):
    """Fixed-capacity pool of T.

    Items are pre-allocated in __init__ via the factory. The pool keeps a
    flat list; acquire() is O(n) linear scan (n=pool size, 1500 in worst
    case) — fine for our scale because the hot path hits the first inactive
    item almost always (LIFO-like usage).
    """

    __slots__ = ("_factory", "_items", "_size", "_active_count", "_high_watermark")

    def __init__(self, factory: Callable[[], T], size: int) -> None:
        if size < 1:
            raise ValueError(f"Pool size must be >= 1, got {size}")
        self._factory: Callable[[], T] = factory
        self._items: list[T] = [factory() for _ in range(size)]
        self._size: int = size
        self._active_count: int = 0
        self._high_watermark: int = 0

    @property
    def size(self) -> int:
        return self._size

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def high_watermark(self) -> int:
        """Max active_count ever observed. Useful for tuning pool size."""
        return self._high_watermark

    @property
    def is_full(self) -> bool:
        return self._active_count >= self._size

    def acquire(self) -> T | None:
        """Return an inactive item, or None if pool is exhausted.

        Calls on_spawn() before returning so per-kind setup happens in
        one place.
        """
        for item in self._items:
            if not item.active:
                item.active = True
                self._active_count += 1
                if self._active_count > self._high_watermark:
                    self._high_watermark = self._active_count
                item.on_spawn()
                return item
        return None

    def release(self, item: T) -> None:
        """Flip the flag, call on_release().

        Safe to call on already-inactive items (idempotent no-op).
        """
        if item.active:
            item.active = False
            self._active_count -= 1
            item.on_release()

    def release_all(self) -> None:
        """Bulk release. Used on scene transition (TITLE → GAMEPLAY etc)."""
        for item in self._items:
            if item.active:
                item.active = False
                self._active_count -= 1
                item.on_release()

    def __iter__(self) -> Iterator[T]:
        """Iterate over ALL items (active and inactive). Caller filters."""
        return iter(self._items)

    def for_each_active(self, fn: Callable[[T], None]) -> None:
        """Apply `fn` to every active item. Skips inactive in O(1) per slot."""
        for item in self._items:
            if item.active:
                fn(item)

    def __repr__(self) -> str:
        return f"Pool(size={self._size}, active={self._active_count}, peak={self._high_watermark})"
