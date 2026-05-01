import xml.etree.ElementTree as ET
import pytest
from utils.data_classes import World, Plant, Box
from utils.assembler import assemble


def _simple_world(**kwargs):
    return World(name="testworld", **kwargs)


class TestAssembleOutput:
    def test_returns_string(self):
        assert isinstance(assemble(_simple_world()), str)

    def test_contains_world_name(self):
        w = World(name="unique_world_name_xyz")
        assert "unique_world_name_xyz" in assemble(w)

    def test_valid_xml(self):
        ET.fromstring(assemble(_simple_world()))  # raises ParseError if invalid

    def test_starts_with_xml_declaration(self):
        result = assemble(_simple_world())
        assert result.strip().startswith("<?xml")

    def test_contains_sdf_root(self):
        result = assemble(_simple_world())
        root = ET.fromstring(result)
        assert root.tag == "sdf"


class TestAssembleFog:
    def test_fog_included_when_density_positive(self):
        w = _simple_world(fog_density=0.05, fog_start=1.5, fog_end=14.0)
        result = assemble(w)
        assert "<fog>" in result
        assert "0.0500" in result

    def test_fog_omitted_when_zero(self):
        result = assemble(_simple_world(fog_density=0.0))
        assert "<fog>" not in result

    def test_fog_start_end_in_output(self):
        w = _simple_world(fog_density=0.05, fog_start=2.0, fog_end=12.0)
        result = assemble(w)
        assert "2.0" in result
        assert "12.0" in result


class TestAssembleRobot:
    def test_contains_husky_model(self):
        result = assemble(_simple_world())
        assert "husky" in result

    def test_robot_position_present(self):
        w = _simple_world(robot_x=3.5, robot_y=-1.0)
        result = assemble(w)
        assert "3.500" in result
        assert "-1.000" in result

    def test_robot_yaw_present(self):
        import math
        w = _simple_world(robot_yaw=math.pi)
        result = assemble(w)
        assert "3.14" in result


class TestAssemblePlants:
    def test_empty_world_has_no_plants(self):
        result = assemble(_simple_world())
        assert "plant_" not in result

    def test_added_plant_appears_in_output(self):
        w = _simple_world()
        w.plants.append(Plant(x=1.0, y=0.5))
        result = assemble(w)
        assert "plant_0" in result

    def test_multiple_plants_indexed_correctly(self):
        w = _simple_world()
        w.plants.append(Plant(x=1.0, y=0.5))
        w.plants.append(Plant(x=2.0, y=-0.5))
        result = assemble(w)
        assert "plant_0" in result
        assert "plant_1" in result

    def test_valid_xml_with_plants(self):
        w = _simple_world()
        w.plants.append(Plant(x=1.0, y=0.5))
        ET.fromstring(assemble(w))


class TestAssembleBoxes:
    def test_empty_world_has_no_named_boxes_from_content(self):
        w = _simple_world()
        result = assemble(w)
        assert "testcrate" not in result

    def test_added_box_name_in_output(self):
        w = _simple_world()
        w.boxes.append(Box("testcrate", 2.0, 0.0, 0.5, 0.3, 0.3, 0.3))
        result = assemble(w)
        assert "testcrate" in result

    def test_valid_xml_with_boxes(self):
        w = _simple_world()
        w.boxes.append(Box("b", 1.0, 0.0, 0.5, 0.3, 0.3, 0.3))
        ET.fromstring(assemble(w))


class TestAssembleLights:
    def test_lights_from_world_included(self):
        w = _simple_world()
        w.lights.append('<light name="custom_light" type="point"><pose>1 0 2 0 0 0</pose></light>')
        result = assemble(w)
        assert "custom_light" in result

    def test_decorations_from_world_included(self):
        w = _simple_world()
        w.decorations.append('<model name="deco_model"><static>true</static><link name="l"/></model>')
        result = assemble(w)
        assert "deco_model" in result


class TestAssembleFullScenario:
    def test_nominal_scenario_assembles(self):
        from utils.scenarios import nominal
        ET.fromstring(assemble(nominal()))

    def test_challenging_scenario_assembles(self):
        from utils.scenarios import challenging
        ET.fromstring(assemble(challenging()))
