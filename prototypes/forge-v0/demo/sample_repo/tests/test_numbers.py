import pytest

from sample_app.numbers import (
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    running_mean,
)


def test_c_to_f_freezing():
    assert celsius_to_fahrenheit(0) == 32


def test_c_to_f_boiling():
    assert celsius_to_fahrenheit(100) == 212


def test_f_to_c_freezing():
    assert fahrenheit_to_celsius(32) == pytest.approx(0)


def test_f_to_c_boiling():
    assert fahrenheit_to_celsius(212) == pytest.approx(100)


def test_running_mean_simple():
    assert running_mean([1, 2, 3]) == [1.0, 1.5, 2.0]


def test_running_mean_singleton():
    assert running_mean([5]) == [5.0]
