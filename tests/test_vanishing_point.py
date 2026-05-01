import pytest
import numpy as np
from vision_nav.vanishing_point import _fit_line, _intersect


class TestFitLine:
    def test_perfect_diagonal(self):
        pts = [(0, 0), (1, 1), (2, 2), (3, 3)]
        m, b = _fit_line(pts)
        assert m == pytest.approx(1.0, abs=1e-4)
        assert b == pytest.approx(0.0, abs=1e-4)

    def test_slope_and_intercept(self):
        # y = 2x + 3
        pts = [(0, 3), (1, 5), (2, 7), (3, 9)]
        m, b = _fit_line(pts)
        assert m == pytest.approx(2.0, abs=1e-3)
        assert b == pytest.approx(3.0, abs=1e-3)

    def test_negative_slope(self):
        # y = -x + 4
        pts = [(0, 4), (1, 3), (2, 2), (3, 1)]
        m, b = _fit_line(pts)
        assert m == pytest.approx(-1.0, abs=1e-3)
        assert b == pytest.approx(4.0, abs=1e-3)

    def test_two_points(self):
        pts = [(0, 0), (2, 4)]
        m, b = _fit_line(pts)
        assert m == pytest.approx(2.0, abs=1e-3)
        assert b == pytest.approx(0.0, abs=1e-3)

    def test_returns_none_for_empty_list(self):
        assert _fit_line([]) is None

    def test_returns_none_for_single_point(self):
        assert _fit_line([(5, 5)]) is None

    def test_returns_tuple(self):
        result = _fit_line([(0, 0), (1, 2)])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_floats(self):
        m, b = _fit_line([(0, 0), (1, 1)])
        assert isinstance(m, float)
        assert isinstance(b, float)

    def test_noisy_points_approximate_fit(self):
        rng = np.random.default_rng(42)
        xs = np.arange(10, dtype=float)
        ys = 3.0 * xs + 5.0 + rng.normal(0, 0.05, size=10)
        pts = list(zip(xs.tolist(), ys.tolist()))
        m, b = _fit_line(pts)
        assert m == pytest.approx(3.0, abs=0.1)
        assert b == pytest.approx(5.0, abs=0.5)


class TestIntersect:
    def test_basic_intersection(self):
        # y = x  and  y = -x + 4  →  x=2, y=2
        x, y = _intersect((1.0, 0.0), (-1.0, 4.0))
        assert x == pytest.approx(2.0, abs=1e-4)
        assert y == pytest.approx(2.0, abs=1e-4)

    def test_vertical_meeting(self):
        # y = 2x - 1  and  y = -2x + 7  →  x=2, y=3
        x, y = _intersect((2.0, -1.0), (-2.0, 7.0))
        assert x == pytest.approx(2.0, abs=1e-4)
        assert y == pytest.approx(3.0, abs=1e-4)

    def test_parallel_lines_return_origin(self):
        # Identical slopes → no intersection → returns (0, 0)
        x, y = _intersect((1.0, 0.0), (1.0, 5.0))
        assert x == 0.0
        assert y == 0.0

    def test_nearly_parallel_threshold(self):
        # Slope difference < 1e-6 treated as parallel
        x, y = _intersect((1.0, 0.0), (1.0 + 1e-7, 0.0))
        assert x == 0.0 and y == 0.0

    def test_horizontal_and_diagonal(self):
        # y = 0  and  y = x - 3  →  x=3, y=0
        x, y = _intersect((0.0, 0.0), (1.0, -3.0))
        assert x == pytest.approx(3.0, abs=1e-4)
        assert y == pytest.approx(0.0, abs=1e-4)

    def test_returns_two_floats(self):
        result = _intersect((1.0, 0.0), (-1.0, 4.0))
        assert len(result) == 2
        assert all(isinstance(v, float) for v in result)

    def test_symmetry(self):
        # Order of arguments should not affect result
        left  = (0.5, 1.0)
        right = (-0.5, 3.0)
        x1, y1 = _intersect(left, right)
        x2, y2 = _intersect(right, left)
        assert x1 == pytest.approx(x2, abs=1e-6)
        assert y1 == pytest.approx(y2, abs=1e-6)
