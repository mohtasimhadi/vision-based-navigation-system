import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


PANEL_W, PANEL_H = 320, 240   # each tile in the display grid

GREEN_LOW  = np.array([25,  40,  40])
GREEN_HIGH = np.array([85, 255, 255])


class VisionPipeline(Node):
    def __init__(self):
        super().__init__('vision_pipeline')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self._callback, 10
        )
        self._morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.get_logger().info('Vision pipeline ready.')

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]
        roi_top = h // 3

        # ── Step 2: HSV segmentation ──────────────────────────────────────
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, GREEN_LOW, GREEN_HIGH)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, self._morph_kernel)

        col_green = np.sum(green_mask[roi_top:, :], axis=0).astype(np.float32)
        thresh = col_green.max() * 0.3
        corridor_cols = np.where(col_green < thresh)[0]
        corridor_x = int(np.median(corridor_cols)) if len(corridor_cols) > 0 else w // 2
        heading_hist = corridor_x - w // 2

        row_ann = _draw_row_detection(frame, green_mask, corridor_x, heading_hist, roi_top)

        # ── Step 3: Vanishing point ───────────────────────────────────────
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray[roi_top:, :], 50, 150)

        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=40,
            minLineLength=30, maxLineGap=15
        )

        left_pts, right_pts = [], []
        vp_ann = frame.copy()

        if lines is not None:
            for seg in lines:
                x1, y1, x2, y2 = seg[0]
                if x2 == x1:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                if abs(slope) < 0.3 or abs(slope) > 10.0:
                    continue
                fy1, fy2 = y1 + roi_top, y2 + roi_top
                if slope < 0:
                    left_pts += [(x1, y1), (x2, y2)]
                    cv2.line(vp_ann, (x1, fy1), (x2, fy2), (255, 100, 0), 1)
                else:
                    right_pts += [(x1, y1), (x2, y2)]
                    cv2.line(vp_ann, (x1, fy1), (x2, fy2), (0, 100, 255), 1)

        vp_x, vp_confidence = w // 2, 0
        left_fit, right_fit = _fit_line(left_pts), _fit_line(right_pts)

        if left_fit and right_fit:
            ix, iy = _intersect(left_fit, right_fit)
            iy_full = iy + roi_top
            if 0 < ix < w and iy_full < h * 2 // 3:
                vp_x, vp_confidence = int(ix), min(len(left_pts), len(right_pts))
                cv2.circle(vp_ann, (vp_x, int(iy_full)),  8, (0, 255, 255), -1)
                cv2.circle(vp_ann, (vp_x, int(iy_full)), 14, (0, 255, 255),  2)

        heading_vp = vp_x - w // 2

        cv2.line(vp_ann, (0, roi_top), (w, roi_top), (0, 220, 220), 1)
        cv2.line(vp_ann, (w // 2, roi_top), (w // 2, h), (255, 255, 255), 1)
        cv2.putText(vp_ann, f'err: {heading_vp:+d}px  conf:{vp_confidence}',
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # ── Tile into one window ──────────────────────────────────────────
        panels = [
            ('Camera Feed',     frame),
            ('Green Mask',      cv2.cvtColor(green_mask, cv2.COLOR_GRAY2BGR)),
            ('Row Detection',   row_ann),
            ('Canny Edges',     cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)),
            ('Vanishing Point', vp_ann),
            ('',                _summary_panel(heading_hist, heading_vp, vp_confidence)),
        ]

        tiles = []
        for title, img in panels:
            tile = cv2.resize(img, (PANEL_W, PANEL_H))
            if title:
                cv2.putText(tile, title, (6, 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            tiles.append(tile)

        display = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
        cv2.imshow('Vision Pipeline', display)
        cv2.waitKey(1)


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _draw_row_detection(frame, green_mask, corridor_x, heading_error, roi_top):
    h, w = frame.shape[:2]
    ann = frame.copy()
    overlay = np.zeros_like(frame)
    overlay[green_mask > 0] = (0, 200, 0)
    ann = cv2.addWeighted(ann, 1.0, overlay, 0.4, 0)
    cv2.line(ann, (0, roi_top), (w, roi_top), (0, 220, 220), 1)
    cv2.line(ann, (w // 2, roi_top), (w // 2, h), (255, 255, 255), 1)
    cv2.line(ann, (corridor_x, roi_top), (corridor_x, h), (0, 0, 255), 2)
    cv2.putText(ann, f'err: {heading_error:+d}px', (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return ann


def _summary_panel(heading_hist: int, heading_vp: int, confidence: int):
    panel = np.zeros((480, 640, 3), dtype=np.uint8)
    rows = [
        ('Heading summary', (0, 255, 255)),
        ('',                (0, 0, 0)),
        (f'  Histogram : {heading_hist:+d} px', (200, 200, 200)),
        (f'  Vanish pt : {heading_vp:+d} px',  (200, 200, 200)),
        (f'  VP conf   : {confidence} pts',     (200, 200, 200)),
    ]
    for i, (txt, colour) in enumerate(rows):
        cv2.putText(panel, txt, (20, 40 + i * 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, colour, 1)
    return panel


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _fit_line(pts):
    if len(pts) < 2:
        return None
    xs = np.array([p[0] for p in pts], dtype=np.float32)
    ys = np.array([p[1] for p in pts], dtype=np.float32)
    m, b = np.polyfit(xs, ys, 1)
    return (float(m), float(b))


def _intersect(left, right):
    m1, b1 = left
    m2, b2 = right
    if abs(m1 - m2) < 1e-6:
        return (0.0, 0.0)
    x = (b2 - b1) / (m1 - m2)
    return (x, m1 * x + b1)


def main(args=None):
    rclpy.init(args=args)
    node = VisionPipeline()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
