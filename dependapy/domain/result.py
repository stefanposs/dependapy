"""
Result Pattern — Explizite Fehlerbehandlung ohne Exceptions.

Ersetzt das SentinelType-Pattern mit typsicheren Ok/Err-Werten.

Usage:
    match registry.get_latest_version("requests"):
        case Ok(version):
            print(f"Latest: {version}")
        case Err(error):
            print(f"Fehler: {error}")
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Never, TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Erfolgreicher Wert."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        """Gibt den Wert zurück. Sicher, da Ok immer einen Wert hat."""
        return self.value

    def unwrap_or(self, default: T) -> T:  # noqa: ARG002
        """Gibt den Wert zurück, ignoriert den Default."""
        return self.value

    def map(self, fn: Callable[[T], U]) -> Ok[U]:
        """Wendet fn auf den Wert an."""
        return Ok(fn(self.value))

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Kettet eine Result-erzeugende Funktion an."""
        return fn(self.value)


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Fehlerwert mit konkretem Fehlertyp."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Never:
        """Wirft ValueError — Err hat keinen Wert."""
        msg = f"Called unwrap on Err: {self.error}"
        raise ValueError(msg)

    def unwrap_or(self, default: U) -> U:
        """Gibt den Default-Wert zurück."""
        return default

    def map(self, fn: Callable[[object], object]) -> Err[E]:  # noqa: ARG002
        """No-op — Err wird nicht transformiert."""
        return self

    def and_then(self, fn: Callable[[object], object]) -> Err[E]:  # noqa: ARG002
        """No-op — Err wird nicht weiterverarbeitet."""
        return self


type Result[T, E] = Ok[T] | Err[E]


def collect_results(results: list[Result[T, E]]) -> Result[list[T], E]:
    """Sammelt eine Liste von Results in ein einzelnes Result.

    Gibt Err beim ersten Fehler zurück, sonst Ok mit allen Werten.
    """
    values: list[T] = []
    for r in results:
        match r:
            case Ok(value):
                values.append(value)
            case Err() as err:
                return err
    return Ok(values)
