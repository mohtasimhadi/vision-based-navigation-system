import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float64, Int32
from cv_bridge import CvBridge
import cv2
import numpy as np


# ── Tuning constants ─────────────────────────────────────────────────────────
SCANLINE_FRAC   = 0.25   # scan line at this fraction of image height (0=top, 1=bottom)
ROVER_HALF_PX   = 65     # half rover width projected onto the scan line (pixels)
EDGE_BAND_HALF  = 10      # use a ±band of rows around the scan line for robustness
MIN_GAP_PX      = 40     # a gap narrower than this is not a usable path


class VisionPipeline(Node):
    def __init__(self):
        super().__init__('vision_pipeline')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self._callback, 10
        )
        self.pub_heading    = self.create_publisher(Float64, '/vision/heading_error',    10)
        self.pub_vp_heading = self.create_publisher(Float64, '/vision/vp_heading_error', 10)
        self.pub_confidence = self.create_publisher(Int32,   '/vision/vp_confidence',    10)
        self.pub_corridor_w = self.create_publisher(Float64, '/vision/corridor_width',   10)
        self.pub_left_peak  = self.create_publisher(Float64, '/vision/left_peak',        10)
        self.pub_right_peak = self.create_publisher(Float64, '/vision/right_peak',       10)
        self.get_logger().info('Vision pipeline (scan-line) ready.')

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w  = frame.shape[:2]

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        scanline_y = int(h * SCANLINE_FRAC)

        heading, clear, left_edge, right_edge, left_gap, right_gap = \
            _scan_line_heading(edges, w, scanline_y, ROVER_HALF_PX, EDGE_BAND_HALF)

        # corridor_width: how much clear space the rover has on the chosen side
        # (used by field_traverser for speed modulation — keep the same semantic)
        corridor_width = float(max(left_gap, right_gap) if not clear else w // 2)

        self.pub_heading.publish(Float64(data=float(heading)))
        self.pub_vp_heading.publish(Float64(data=float(heading)))   # same source
        self.pub_confidence.publish(Int32(data=int(clear)))         # 1 = path clear
        self.pub_corridor_w.publish(Float64(data=corridor_width))
        self.pub_left_peak.publish(Float64(data=float(left_edge)))
        self.pub_right_peak.publish(Float64(data=float(right_edge)))

        _draw_debug(frame, edges, scanline_y, w, heading,
                    left_edge, right_edge, clear, left_gap, right_gap)


# ── Core algorithm ───────────────────────────────────────────────────────────

def _scan_line_heading(edges, img_w, scanline_y, rover_half_px, band_half):
    """
    1. Collapse a horizontal band of edge rows into a single 1-D occupancy row.
    2. Check the rover footprint [cx-rover_half_px, cx+rover_half_px] for edges.
    3. If clear  → heading = 0 (go straight).
    4. If blocked → scan left from the left rover edge and right from the right
                    rover edge; steer toward whichever side has the larger gap.

    Returns
    -------
    heading      : signed pixel error from image centre (positive = steer right)
    clear        : True if the straight-ahead path was unobstructed
    left_edge_x  : x of the first edge to the left of the rover (or 0)
    right_edge_x : x of the first edge to the right of the rover (or img_w-1)
    left_gap     : clear pixels available to the left
    right_gap    : clear pixels available to the right
    """
    top    = max(0, scanline_y - band_half)
    bottom = min(edges.shape[0], scanline_y + band_half + 1)
    band   = edges[top:bottom, :]

    # Any non-zero edge pixel in the band → occupied column
    occupied = (np.sum(band, axis=0) > 0)

    cx      = img_w // 2
    left_b  = max(0,        cx - rover_half_px)
    right_b = min(img_w-1,  cx + rover_half_px)

    # ── Step 1: is the path ahead clear? ─────────────────────────────────────
    if not np.any(occupied[left_b:right_b + 1]):
        return 0.0, True, left_b, right_b, left_b, img_w - 1 - right_b

    # ── Step 2: scan left from left_b ────────────────────────────────────────
    left_edge_x = 0
    left_gap    = left_b           # worst case: edge at image boundary
    for i in range(left_b, -1, -1):
        if occupied[i]:
            left_edge_x = i
            left_gap    = left_b - i
            break

    # ── Step 3: scan right from right_b ──────────────────────────────────────
    right_edge_x = img_w - 1
    right_gap    = img_w - 1 - right_b
    for i in range(right_b, img_w):
        if occupied[i]:
            right_edge_x = i
            right_gap    = i - right_b
            break

    # ── Step 4: pick side with more room ─────────────────────────────────────
    if left_gap >= right_gap:
        # Steer left: target is the centre of the left gap
        target_x = left_b - left_gap // 2
    else:
        # Steer right: target is the centre of the right gap
        target_x = right_b + right_gap // 2

    heading = float(target_x - cx)
    return heading, False, left_edge_x, right_edge_x, left_gap, right_gap


# ── Debug visualisation ──────────────────────────────────────────────────────

def _draw_debug(frame, edges, scanline_y, img_w, heading,
                left_edge_x, right_edge_x, clear, left_gap, right_gap):
    h  = frame.shape[0]
    cx = img_w // 2

    ann = frame.copy()

    # Scan line
    color = (0, 255, 0) if clear else (0, 0, 255)
    cv2.line(ann, (0, scanline_y), (img_w, scanline_y), color, 1)

    # Rover footprint on scan line
    left_b  = max(0,       cx - ROVER_HALF_PX)
    right_b = min(img_w-1, cx + ROVER_HALF_PX)
    cv2.line(ann, (left_b,  scanline_y - 8), (left_b,  scanline_y + 8), (255, 255, 0), 2)
    cv2.line(ann, (right_b, scanline_y - 8), (right_b, scanline_y + 8), (255, 255, 0), 2)

    # Nearest edges found (left=blue, right=red)
    if not clear:
        cv2.circle(ann, (left_edge_x,  scanline_y), 5, (255, 80, 0),   -1)
        cv2.circle(ann, (right_edge_x, scanline_y), 5, (0,   80, 255), -1)

    # Heading arrow from centre
    target_x = int(cx + heading)
    cv2.arrowedLine(ann, (cx, scanline_y), (target_x, scanline_y),
                    (0, 255, 255), 2, tipLength=0.3)

    # Text overlay
    status = 'CLEAR' if clear else f'L:{left_gap}px R:{right_gap}px'
    cv2.putText(ann, f'err:{heading:+.0f}px  {status}',
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

    # Edge mask panel
    edge_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cv2.line(edge_bgr, (0, scanline_y), (img_w, scanline_y), (0, 255, 0), 1)

    display = np.hstack([
        cv2.resize(ann,      (640, 480)),
        cv2.resize(edge_bgr, (640, 480)),
    ])
    cv2.imshow('Vision Pipeline', display)
    cv2.waitKey(1)


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
