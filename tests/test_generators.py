import pytest
from utils.data_classes import World, Plant
from utils.generators import (
    add_natural_row,
    add_terrain_tile,
    add_end_posts,
    add_grass_field,
    add_loose_gravel,
    add_corridor_light_strip,
    add_row_light,
)


def _world():
    return World(name="test")


class TestAddNaturalRow:
    def test_adds_plants(self):
        w = _world()
        add_natural_row(w, y_center=0.0, seed=42)
        assert len(w.plants) > 0

    def test_plants_near_y_center(self):
        w = _world()
        add_natural_row(w, y_center=1.0, curve_amp=0.10, y_jitter=0.06, seed=42)
        # All plants should be within ±0.5 m of y_center
        for p in w.plants:
            assert abs(p.y - 1.0) < 0.5

    def test_plants_within_x_range(self):
        w = _world()
        add_natural_row(w, y_center=0.0, length=9.0, seed=42)
        for p in w.plants:
            assert -0.3 <= p.x <= 9.3  # small jitter allowed beyond [0, length]

    def test_skip_reduces_plant_count(self):
        w_full = _world()
        w_skip = _world()
        add_natural_row(w_full, y_center=0.0, seed=7)
        add_natural_row(w_skip, y_center=0.0, skip=[0, 1, 2, 3], seed=7)
        assert len(w_skip.plants) < len(w_full.plants)

    def test_clear_end_reduces_plant_count(self):
        w_full = _world()
        w_clear = _world()
        add_natural_row(w_full, y_center=0.0, length=9.0, seed=5)
        add_natural_row(w_clear, y_center=0.0, length=9.0, clear_end_m=2.0, seed=5)
        assert len(w_clear.plants) < len(w_full.plants)

    def test_clear_end_no_plants_near_end(self):
        w = _world()
        add_natural_row(w, y_center=0.0, length=9.0, clear_end_m=2.0, seed=3)
        # No plant should have x > 9.0 - 2.0 = 7.0 (minus some small jitter)
        assert all(p.x <= 7.5 for p in w.plants)

    def test_same_seed_reproducible(self):
        w1, w2 = _world(), _world()
        add_natural_row(w1, y_center=0.0, seed=99)
        add_natural_row(w2, y_center=0.0, seed=99)
        assert len(w1.plants) == len(w2.plants)
        for p1, p2 in zip(w1.plants, w2.plants):
            assert p1.x == pytest.approx(p2.x)
            assert p1.y == pytest.approx(p2.y)

    def test_different_seeds_give_different_layouts(self):
        w1, w2 = _world(), _world()
        add_natural_row(w1, y_center=0.0, seed=1)
        add_natural_row(w2, y_center=0.0, seed=2)
        assert [p.x for p in w1.plants] != [p.x for p in w2.plants]

    def test_does_not_touch_boxes_or_lights(self):
        w = _world()
        add_natural_row(w, y_center=0.0, seed=42)
        assert len(w.boxes) == 0
        assert len(w.lights) == 0


class TestAddTerrainTile:
    def test_adds_one_box(self):
        w = _world()
        add_terrain_tile(w, 4.5, 0.0, 9.0, 1.0, r=0.5, g=0.3, b=0.1)
        assert len(w.boxes) == 1

    def test_position_correct(self):
        w = _world()
        add_terrain_tile(w, 4.5, -1.0, 9.0, 1.0, r=0.5, g=0.3, b=0.1)
        b = w.boxes[0]
        assert b.x == 4.5
        assert b.y == -1.0
        assert b.sx == 9.0
        assert b.sy == 1.0

    def test_auto_name_assigned(self):
        w = _world()
        add_terrain_tile(w, 4.5, 0.0, 9.0, 1.0, r=0.5, g=0.3, b=0.1)
        assert w.boxes[0].name != ""

    def test_custom_name_used(self):
        w = _world()
        add_terrain_tile(w, 4.5, 0.0, 9.0, 1.0, r=0.5, g=0.3, b=0.1, name="my_tile")
        assert w.boxes[0].name == "my_tile"

    def test_color_stored(self):
        w = _world()
        add_terrain_tile(w, 0, 0, 1, 1, r=0.8, g=0.2, b=0.4)
        b = w.boxes[0]
        assert b.r == pytest.approx(0.8)
        assert b.g == pytest.approx(0.2)
        assert b.b == pytest.approx(0.4)

    def test_thin_z_height(self):
        w = _world()
        add_terrain_tile(w, 0, 0, 1, 1, r=0, g=0, b=0)
        assert w.boxes[0].z == pytest.approx(0.005)


class TestAddEndPosts:
    def test_one_pair_gives_two_posts(self):
        w = _world()
        add_end_posts(w, x=9.4, y_pairs=[(-0.5, 0.5)])
        assert len(w.boxes) == 2

    def test_two_pairs_give_four_posts(self):
        w = _world()
        add_end_posts(w, x=9.4, y_pairs=[(-0.5, 0.5), (-1.5, 1.5)])
        assert len(w.boxes) == 4

    def test_posts_at_correct_x(self):
        w = _world()
        add_end_posts(w, x=5.0, y_pairs=[(0.0, 1.0)])
        for b in w.boxes:
            assert b.x == 5.0

    def test_posts_at_correct_y(self):
        w = _world()
        add_end_posts(w, x=9.4, y_pairs=[(-0.5, 0.5)])
        ys = sorted(b.y for b in w.boxes)
        assert ys[0] == pytest.approx(-0.5)
        assert ys[1] == pytest.approx(0.5)

    def test_posts_are_tall(self):
        w = _world()
        add_end_posts(w, x=9.4, y_pairs=[(0.0, 1.0)])
        for b in w.boxes:
            assert b.sz >= 0.5


class TestAddGrassField:
    def test_adds_one_decoration(self):
        w = _world()
        add_grass_field(w, 4.5, 0.0, 9.0, 1.0, seed=42)
        assert len(w.decorations) == 1

    def test_decoration_contains_grass_tag(self):
        w = _world()
        add_grass_field(w, 4.5, 0.0, 9.0, 1.0, seed=42)
        assert "grassfield" in w.decorations[0]

    def test_multiple_calls_add_multiple_decorations(self):
        w = _world()
        add_grass_field(w, 4.5, -1.0, 9.0, 1.0, seed=1)
        add_grass_field(w, 4.5,  1.0, 9.0, 1.0, seed=2)
        assert len(w.decorations) == 2

    def test_does_not_add_plants_or_boxes(self):
        w = _world()
        add_grass_field(w, 4.5, 0.0, 9.0, 1.0, seed=42)
        assert len(w.plants) == 0
        assert len(w.boxes) == 0

    def test_reproducible_with_seed(self):
        w1, w2 = _world(), _world()
        add_grass_field(w1, 4.5, 0.0, 9.0, 1.0, seed=7)
        add_grass_field(w2, 4.5, 0.0, 9.0, 1.0, seed=7)
        assert w1.decorations[0] == w2.decorations[0]


class TestAddLooseGravel:
    def test_adds_one_decoration(self):
        w = _world()
        add_loose_gravel(w, 4.5, 0.0, 9.0, 1.0, n_stones=50, seed=42)
        assert len(w.decorations) == 1

    def test_decoration_contains_gravel_tag(self):
        w = _world()
        add_loose_gravel(w, 4.5, 0.0, 9.0, 1.0, n_stones=10, seed=42)
        assert "gravel" in w.decorations[0]

    def test_reproducible_with_seed(self):
        w1, w2 = _world(), _world()
        add_loose_gravel(w1, 4.5, 0.0, 9.0, 1.0, n_stones=30, seed=99)
        add_loose_gravel(w2, 4.5, 0.0, 9.0, 1.0, n_stones=30, seed=99)
        assert w1.decorations[0] == w2.decorations[0]

    def test_does_not_add_plants_or_boxes(self):
        w = _world()
        add_loose_gravel(w, 4.5, 0.0, 9.0, 1.0, seed=42)
        assert len(w.plants) == 0
        assert len(w.boxes) == 0


class TestAddCorridorLightStrip:
    def test_adds_n_lights(self):
        w = _world()
        add_corridor_light_strip(w, y=0.0, r=1.0, g=0.5, b=0.0, n_lights=5)
        assert len(w.lights) == 5

    def test_custom_n_lights(self):
        w = _world()
        add_corridor_light_strip(w, y=0.0, r=1.0, g=0.5, b=0.0, n_lights=3)
        assert len(w.lights) == 3

    def test_lights_are_strings(self):
        w = _world()
        add_corridor_light_strip(w, y=1.0, r=0.9, g=0.6, b=0.2, n_lights=2)
        for light in w.lights:
            assert isinstance(light, str)

    def test_multiple_strips_accumulate(self):
        w = _world()
        add_corridor_light_strip(w, y=-1.0, r=1.0, g=0.4, b=0.05, n_lights=5)
        add_corridor_light_strip(w, y=0.0,  r=1.0, g=0.98, b=0.85, n_lights=5)
        assert len(w.lights) == 10

    def test_does_not_touch_plants_or_boxes(self):
        w = _world()
        add_corridor_light_strip(w, y=0.0, r=1.0, g=1.0, b=1.0)
        assert len(w.plants) == 0
        assert len(w.boxes) == 0


class TestAddRowLight:
    def test_adds_one_light(self):
        w = _world()
        add_row_light(w, "row_light_0", x=1.0, y=0.5, z=1.5, r=1.0, g=0.8, b=0.2)
        assert len(w.lights) == 1

    def test_light_is_string(self):
        w = _world()
        add_row_light(w, "rl", x=0.0, y=0.0, z=1.0, r=1.0, g=1.0, b=1.0)
        assert isinstance(w.lights[0], str)
