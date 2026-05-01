import math
import pytest
from utils.data_classes import World
from utils.scenarios import nominal, challenging, ROBOT_ROWS


class TestNominal:
    def test_returns_world(self):
        assert isinstance(nominal(), World)

    def test_has_plants(self):
        assert len(nominal().plants) > 0

    def test_no_fog(self):
        assert nominal().fog_density == 0.0

    def test_has_lights(self):
        assert len(nominal().lights) > 0

    def test_has_corridor_tiles(self):
        # Nominal uses flat terrain tiles (boxes)
        assert len(nominal().boxes) > 0

    def test_world_name(self):
        assert nominal().name == "crop_nominal"

    @pytest.mark.parametrize("row", [0, 1, 2])
    def test_robot_position_matches_row(self, row):
        w = nominal(row)
        r = ROBOT_ROWS[row]
        assert w.robot_x == r["x"]
        assert w.robot_y == r["y"]
        assert w.robot_yaw == pytest.approx(r["yaw"])

    def test_row1_faces_negative_x(self):
        w = nominal(1)
        assert w.robot_yaw == pytest.approx(math.pi)

    def test_row0_and_row2_face_positive_x(self):
        assert nominal(0).robot_yaw == pytest.approx(0.0)
        assert nominal(2).robot_yaw == pytest.approx(0.0)

    def test_different_rows_give_different_y(self):
        y0 = nominal(0).robot_y
        y1 = nominal(1).robot_y
        y2 = nominal(2).robot_y
        assert y0 != y1
        assert y1 != y2

    def test_plant_count_consistent(self):
        # Same seed → same plant count
        assert len(nominal(0).plants) == len(nominal(0).plants)


class TestChallenging:
    def test_returns_world(self):
        assert isinstance(challenging(), World)

    def test_has_fog(self):
        assert challenging().fog_density > 0.0

    def test_has_plants(self):
        assert len(challenging().plants) > 0

    def test_has_obstacles(self):
        obstacle_names = [b.name for b in challenging().boxes]
        assert any("crate" in n or "debris" in n for n in obstacle_names)

    def test_world_name(self):
        assert challenging().name == "crop_challenging"

    def test_has_lights(self):
        assert len(challenging().lights) > 0

    def test_has_decorations(self):
        assert len(challenging().decorations) > 0

    @pytest.mark.parametrize("row", [0, 1, 2])
    def test_robot_position_matches_row(self, row):
        w = challenging(row)
        r = ROBOT_ROWS[row]
        assert w.robot_x == r["x"]
        assert w.robot_y == r["y"]

    def test_fog_density_positive(self):
        assert challenging().fog_density == pytest.approx(0.055)

    def test_fog_start_and_end(self):
        w = challenging()
        assert w.fog_start > 0
        assert w.fog_end > w.fog_start


class TestRobotRows:
    def test_three_rows_defined(self):
        assert len(ROBOT_ROWS) == 3

    def test_all_rows_have_required_keys(self):
        for r in ROBOT_ROWS:
            assert "x" in r
            assert "y" in r
            assert "yaw" in r
