"""Tests für dependapy.domain.result — Result[T, E] Pattern."""

from __future__ import annotations

import pytest

from dependapy.domain.errors import PackageNotFoundError, RegistryError
from dependapy.domain.result import Err, Ok, Result, collect_results


class TestOk:
    def test_is_ok(self) -> None:
        assert Ok(42).is_ok() is True

    def test_is_err(self) -> None:
        assert Ok(42).is_err() is False

    def test_unwrap(self) -> None:
        assert Ok("hello").unwrap() == "hello"

    def test_unwrap_or(self) -> None:
        assert Ok("hello").unwrap_or("default") == "hello"

    def test_map(self) -> None:
        result = Ok(2).map(lambda x: x * 3)
        assert result == Ok(6)

    def test_and_then(self) -> None:
        result = Ok(5).and_then(lambda x: Ok(x + 1))
        assert result == Ok(6)

    def test_and_then_returns_err(self) -> None:
        err = RegistryError("fail")
        result = Ok(5).and_then(lambda x: Err(err))
        assert result == Err(err)

    def test_equality(self) -> None:
        assert Ok(1) == Ok(1)
        assert Ok(1) != Ok(2)
        assert Ok(1) != Err(RegistryError("x"))

    def test_frozen_immutable(self) -> None:
        r = Ok(42)
        with pytest.raises((AttributeError, TypeError)):
            r.value = 99  # type: ignore[misc]

    def test_ok_with_none(self) -> None:
        r: Result[None, str] = Ok(None)
        assert r.is_ok()
        assert r.unwrap() is None


class TestErr:
    def test_is_ok(self) -> None:
        assert Err(RegistryError("x")).is_ok() is False

    def test_is_err(self) -> None:
        assert Err(RegistryError("x")).is_err() is True

    def test_unwrap_raises(self) -> None:
        with pytest.raises(ValueError, match="Called unwrap on Err"):
            Err(RegistryError("oops")).unwrap()

    def test_unwrap_or(self) -> None:
        assert Err(RegistryError("x")).unwrap_or("fallback") == "fallback"

    def test_map_no_op(self) -> None:
        err = Err(RegistryError("original"))
        result = err.map(lambda x: x * 2)
        assert result == err

    def test_and_then_no_op(self) -> None:
        err = Err(RegistryError("original"))
        result = err.and_then(lambda x: Ok(x))
        assert result == err

    def test_equality(self) -> None:
        e = RegistryError("same")
        assert Err(e) == Err(e)

    def test_frozen_immutable(self) -> None:
        r = Err(RegistryError("x"))
        with pytest.raises((AttributeError, TypeError)):
            r.error = None  # type: ignore[misc]


class TestCollectResults:
    def test_all_ok(self) -> None:
        results = [Ok(1), Ok(2), Ok(3)]
        assert collect_results(results) == Ok([1, 2, 3])

    def test_empty_list(self) -> None:
        assert collect_results([]) == Ok([])

    def test_first_err_short_circuits(self) -> None:
        err = RegistryError("fail")
        results = [Ok(1), Err(err), Ok(3)]
        match collect_results(results):
            case Err(e):
                assert e is err
            case Ok(_):
                pytest.fail("Expected Err, got Ok")

    def test_all_err_returns_first(self) -> None:
        err1 = RegistryError("first")
        err2 = RegistryError("second")
        results = [Err(err1), Err(err2)]
        match collect_results(results):
            case Err(e):
                assert e is err1
            case Ok(_):
                pytest.fail("Expected Err")


class TestResultPatternMatching:
    """Testet den idiomatischen match-Statement Einsatz."""

    def test_match_ok(self) -> None:
        value = None
        match Ok(42):
            case Ok(v):
                value = v
            case Err(_):
                pytest.fail("Should match Ok")
        assert value == 42

    def test_match_err(self) -> None:
        error = None
        err = PackageNotFoundError("requests")
        match Err(err):
            case Ok(_):
                pytest.fail("Should match Err")
            case Err(e):
                error = e
        assert error is err

    def test_chaining(self) -> None:
        """Test: Ok(2).map(x3).and_then(halve) = Ok(3.0)"""
        result: Result[float, str] = Ok(2).map(lambda x: x * 3).and_then(lambda x: Ok(float(x / 2)))
        assert result == Ok(3.0)
