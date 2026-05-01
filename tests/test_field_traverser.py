import math
import pytest


# ── Pure logic extracted from FieldTraverser (no ROS2 needed) ─────────────────

def _steer(heading, Kp=0.006, max_angular_z=1.2):
    return max(-max_angular_z, min(max_angular_z, -Kp * heading))


def _speed_factor(heading_err, corridor_width, vp_confidence):
    err = abs(heading_err) / 320.0
    factor = 1.0 - min(err * 1.5, 0.5)
    if corridor_width < 80.0:
        factor *= 0.5
    elif corridor_width < 120.0:
        factor *= 0.75
    if vp_confidence == 1:
        factor *= 0.6
    return factor


def _end_of_row(trip_dist, corridor_idx, vp_confidence, corridor_width,
                ROWS=None):
    if ROWS is None:
        ROWS = [
            {"x_start": -0.5, "x_end": 9.4},
            {"x_start":  9.4, "x_end": -0.5},
            {"x_start": -0.5, "x_end":  9.4},
        ]
    row = ROWS[corridor_idx]
    row_len = abs(row["x_end"] - row["x_start"])
    if trip_dist > (row_len - 0.3):
        return True
    visual = (vp_confidence == 1 or corridor_width > 300)
    return visual and trip_dist > (row_len - 2.0)


class TestFieldTraverserRows:
    def test_row_count(self):
        from vision_nav.field_traverser import FieldTraverser
        assert len(FieldTraverser.ROWS) == 3

    def test_row_names(self):
        from vision_nav.field_traverser import FieldTraverser
        names = [r["name"] for r in FieldTraverser.ROWS]
        assert "C2_left"  in names
        assert "C1_inner" in names
        assert "C3_right" in names

    def test_c1_inner_faces_negative_x(self):
        from vision_nav.field_traverser import FieldTraverser
        inner = next(r for r in FieldTraverser.ROWS if r["name"] == "C1_inner")
        assert inner["dir"] == -1

    def test_c2_and_c3_face_positive_x(self):
        from vision_nav.field_traverser import FieldTraverser
        for name in ("C2_left", "C3_right"):
            row = next(r for r in FieldTraverser.ROWS if r["name"] == name)
            assert row["dir"] == 1

    def test_row_y_values_distinct(self):
        from vision_nav.field_traverser import FieldTraverser
        ys = [r["y"] for r in FieldTraverser.ROWS]
        assert len(set(ys)) == 3


class TestSteer:
    def test_zero_heading_gives_zero(self):
        assert _steer(0) == pytest.approx(0.0)

    def test_positive_heading_gives_negative_angular(self):
        assert _steer(50) < 0

    def test_negative_heading_gives_positive_angular(self):
        assert _steer(-50) > 0

    def test_proportional_to_heading(self):
        assert _steer(100) == pytest.approx(-0.6, abs=1e-6)

    def test_clamps_at_max_positive(self):
        assert _steer(-500) == pytest.approx(1.2)

    def test_clamps_at_max_negative(self):
        assert _steer(500) == pytest.approx(-1.2)

    def test_custom_kp(self):
        assert _steer(100, Kp=0.010) == pytest.approx(-1.0, abs=1e-6)

    def test_custom_max(self):
        result = _steer(1000, max_angular_z=0.5)
        assert result == pytest.approx(-0.5)


class TestSpeedFactor:
    def test_zero_error_full_speed(self):
        assert _speed_factor(0.0, 200.0, 0) == pytest.approx(1.0)

    def test_large_error_reduces_speed(self):
        factor_small = _speed_factor(10.0, 200.0, 0)
        factor_large = _speed_factor(200.0, 200.0, 0)
        assert factor_large < factor_small

    def test_narrow_corridor_halves_speed(self):
        full  = _speed_factor(0.0, 200.0, 0)
        narrow = _speed_factor(0.0, 60.0, 0)
        assert narrow == pytest.approx(full * 0.5)

    def test_medium_corridor_three_quarter_speed(self):
        full   = _speed_factor(0.0, 200.0, 0)
        medium = _speed_factor(0.0, 100.0, 0)
        assert medium == pytest.approx(full * 0.75)

    def test_low_vp_confidence_reduces_speed(self):
        full = _speed_factor(0.0, 200.0, 0)
        low  = _speed_factor(0.0, 200.0, 1)
        assert low == pytest.approx(full * 0.6)

    def test_factor_never_exceeds_one(self):
        assert _speed_factor(0.0, 500.0, 0) <= 1.0

    def test_factor_non_negative(self):
        assert _speed_factor(320.0, 50.0, 1) >= 0.0

    def test_combined_narrow_and_low_confidence(self):
        factor = _speed_factor(0.0, 60.0, 1)
        assert factor == pytest.approx(1.0 * 0.5 * 0.6)


class TestEndOfRow:
    ROW_LEN = 9.9  # abs(9.4 - (-0.5))

    def test_triggers_at_distance_threshold(self):
        assert _end_of_row(self.ROW_LEN - 0.2, 0, 0, 200) is True

    def test_does_not_trigger_early(self):
        assert _end_of_row(self.ROW_LEN - 2.0, 0, 0, 200) is False

    def test_visual_trigger_with_clear_path(self):
        # vp_confidence == 1 (clear) and close to end
        assert _end_of_row(self.ROW_LEN - 1.5, 0, 1, 200) is True

    def test_visual_trigger_with_wide_corridor(self):
        # corridor_width > 300 and close to end
        assert _end_of_row(self.ROW_LEN - 1.5, 0, 0, 350) is True

    def test_visual_does_not_trigger_far_from_end(self):
        assert _end_of_row(2.0, 0, 1, 350) is False

    def test_all_corridors_have_same_length(self):
        for idx in range(3):
            # should trigger near the expected row length
            assert _end_of_row(9.8, idx, 0, 200) is True


class TestDeadReckoningMath:
    def test_forward_motion_updates_x(self):
        x, y, yaw = 0.0, 0.0, 0.0
        v, dt = 0.35, 0.05
        x += v * math.cos(yaw) * dt
        y += v * math.sin(yaw) * dt
        assert x == pytest.approx(0.0175, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-6)

    def test_yaw_updates_with_angular(self):
        yaw = 0.0
        w_z, dt = 0.5, 0.05
        yaw += w_z * dt
        assert yaw == pytest.approx(0.025)

    def test_reversed_direction_moves_negative_x(self):
        x, y, yaw = 9.4, 0.0, math.pi
        v, dt = 0.35, 0.05
        x += v * math.cos(yaw) * dt
        assert x < 9.4
