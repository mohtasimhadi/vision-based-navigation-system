import numpy as np
import pytest
from vision_nav.vision_pipeline import _wall_gap_heading

W, H = 640, 480
ROI_TOP = int(H * 0.35)
ROI_BOT = int(H * 0.85)


def _blank():
    return np.zeros((H, W), dtype=np.uint8)


def _with_walls(left_x: int, right_x: int, thickness: int = 5):
    edges = _blank()
    edges[ROI_TOP:ROI_BOT, left_x : left_x + thickness] = 255
    edges[ROI_TOP:ROI_BOT, right_x : right_x + thickness] = 255
    return edges


class TestClearPath:
    def test_blank_image_is_clear(self):
        _, clear, *_ = _wall_gap_heading(_blank(), W, H)
        assert clear is True

    def test_blank_image_heading_near_zero(self):
        # clear path: left_wall=0, right_wall=W-1, gap_centre=(W-1)/2, cx=W//2
        # heading = (W-1)/2 - W//2 = -0.5 for even W — within half a pixel of centre
        heading, clear, *_ = _wall_gap_heading(_blank(), W, H)
        assert abs(heading) <= 0.5

    def test_edges_outside_roi_ignored(self):
        edges = _blank()
        edges[0 : ROI_TOP - 5, :] = 255     # above ROI
        edges[ROI_BOT + 5 : H, :] = 255     # below ROI
        _, clear, *_ = _wall_gap_heading(edges, W, H)
        assert clear is True

    def test_small_blobs_filtered_out(self):
        # A tiny blob (< MIN_CC_AREA=300) should be ignored → still clear
        edges = _blank()
        edges[ROI_TOP + 10 : ROI_TOP + 15, W // 4 : W // 4 + 5] = 255
        _, clear, *_ = _wall_gap_heading(edges, W, H)
        assert clear is True


class TestWallDetection:
    def test_walls_on_both_sides_not_clear(self):
        edges = _with_walls(40, 580)
        _, clear, lx, rx, *_ = _wall_gap_heading(edges, W, H)
        assert clear is False
        assert lx > 0
        assert rx < W - 1

    def test_left_wall_detected_left_of_center(self):
        edges = _with_walls(40, 580)
        _, _, lx, *_ = _wall_gap_heading(edges, W, H)
        assert lx < W // 2

    def test_right_wall_detected_right_of_center(self):
        edges = _with_walls(40, 580)
        _, _, _lx, rx, *_ = _wall_gap_heading(edges, W, H)
        assert rx > W // 2

    def test_gap_width_positive(self):
        edges = _with_walls(40, 580)
        _, _, lx, rx, *_ = _wall_gap_heading(edges, W, H)
        assert rx > lx


class TestHeadingDirection:
    def test_centered_walls_near_zero_heading(self):
        cx = W // 2
        offset = 120
        edges = _with_walls(cx - offset - 5, cx + offset)
        heading, _, *_ = _wall_gap_heading(edges, W, H)
        assert abs(heading) < 20

    def test_left_wall_only_gives_positive_heading(self):
        # Only left wall → gap center pulled to the right → positive heading
        edges = _blank()
        edges[ROI_TOP:ROI_BOT, 20:30] = 255
        heading, clear, *_ = _wall_gap_heading(edges, W, H)
        assert clear is False
        assert heading > 0

    def test_right_wall_only_gives_negative_heading(self):
        # Only right wall → gap center pulled to the left → negative heading
        edges = _blank()
        edges[ROI_TOP:ROI_BOT, 610:620] = 255
        heading, clear, *_ = _wall_gap_heading(edges, W, H)
        assert clear is False
        assert heading < 0

    def test_heading_magnitude_larger_when_more_offset(self):
        edges_close  = _with_walls(W // 2 - 80, W // 2 + 60)
        edges_offset = _with_walls(40, 200)
        h_close, *_  = _wall_gap_heading(edges_close,  W, H)
        h_off,   *_  = _wall_gap_heading(edges_offset, W, H)
        assert abs(h_off) > abs(h_close)


class TestReturnShape:
    def test_returns_correct_number_of_values(self):
        result = _wall_gap_heading(_blank(), W, H)
        heading, clear, lx, rx, cleaned, kept, roi_top, roi_bot, band, labels = result
        assert isinstance(heading, float)
        assert isinstance(clear, (bool, np.bool_))
        assert isinstance(lx, int)
        assert isinstance(rx, int)

    def test_roi_boundaries_match_constants(self):
        *_, roi_top, roi_bot, _, _ = _wall_gap_heading(_blank(), W, H)
        assert roi_top == ROI_TOP
        assert roi_bot == ROI_BOT

    def test_cleaned_full_same_shape_as_input(self):
        edges = _blank()
        _, _, _, _, cleaned, *_ = _wall_gap_heading(edges, W, H)
        assert cleaned.shape == edges.shape
