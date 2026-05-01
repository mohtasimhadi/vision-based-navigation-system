import pytest
from utils.data_classes import Plant, Box, World


class TestPlant:
    def test_required_fields(self):
        p = Plant(x=1.0, y=2.0)
        assert p.x == 1.0
        assert p.y == 2.0

    def test_defaults(self):
        p = Plant(x=0.0, y=0.0)
        assert p.canopy_r == 0.26
        assert p.stem_r == 0.04
        assert p.stem_h == 0.32
        assert p.cr == 0.11
        assert p.cg == 0.50
        assert p.cb == 0.08

    def test_custom_values(self):
        p = Plant(x=0.5, y=-1.0, canopy_r=0.30, cr=0.15, cg=0.40, cb=0.10)
        assert p.canopy_r == 0.30
        assert p.cr == 0.15
        assert p.cg == 0.40

    def test_negative_coordinates(self):
        p = Plant(x=-3.0, y=-1.5)
        assert p.x == -3.0
        assert p.y == -1.5

    def test_float_precision(self):
        p = Plant(x=1.234, y=5.678)
        assert p.x == pytest.approx(1.234)
        assert p.y == pytest.approx(5.678)


class TestBox:
    def test_required_fields(self):
        b = Box("crate", 1.0, 2.0, 0.5, 0.3, 0.3, 0.3)
        assert b.name == "crate"
        assert b.x == 1.0
        assert b.y == 2.0
        assert b.z == 0.5
        assert b.sx == 0.3
        assert b.sy == 0.3
        assert b.sz == 0.3

    def test_default_color(self):
        b = Box("box", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        assert b.r == 0.55
        assert b.g == 0.33
        assert b.b == 0.10

    def test_custom_color(self):
        b = Box("colored", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, r=0.8, g=0.2, b=0.5)
        assert b.r == 0.8
        assert b.g == 0.2
        assert b.b == 0.5

    def test_name_preserved(self):
        b = Box("my_special_box", 0, 0, 0, 1, 1, 1)
        assert b.name == "my_special_box"


class TestWorld:
    def test_name_required(self):
        w = World(name="test_world")
        assert w.name == "test_world"

    def test_default_robot_position(self):
        w = World(name="w")
        assert w.robot_x == -0.5
        assert w.robot_y == 0.0
        assert w.robot_yaw == 0.0

    def test_default_lists_empty(self):
        w = World(name="w")
        assert w.plants == []
        assert w.boxes == []
        assert w.lights == []
        assert w.decorations == []

    def test_default_fog_off(self):
        w = World(name="w")
        assert w.fog_density == 0.0

    def test_custom_robot_position(self):
        w = World(name="w", robot_x=9.4, robot_y=0.0, robot_yaw=3.14159)
        assert w.robot_x == 9.4
        assert w.robot_yaw == pytest.approx(3.14159)

    def test_lists_are_independent_across_instances(self):
        w1 = World(name="a")
        w2 = World(name="b")
        w1.plants.append(Plant(0.0, 0.0))
        assert len(w2.plants) == 0

    def test_fog_settings(self):
        w = World(name="foggy", fog_density=0.05, fog_start=2.0, fog_end=15.0)
        assert w.fog_density == pytest.approx(0.05)
        assert w.fog_start == pytest.approx(2.0)
        assert w.fog_end == pytest.approx(15.0)

    def test_ambient_tuple(self):
        w = World(name="w", ambient=(0.3, 0.3, 0.3, 1.0))
        assert w.ambient == (0.3, 0.3, 0.3, 1.0)

    def test_sun_direction_tuple(self):
        w = World(name="w", sun_dir=(-0.5, 0.1, -0.9))
        assert w.sun_dir == (-0.5, 0.1, -0.9)
