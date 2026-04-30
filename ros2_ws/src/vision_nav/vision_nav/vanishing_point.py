import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class VanishingPointDetector(Node):
    def __init__(self):
        super().__init__('vanishing_point_detector')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self._callback, 10
        )
        self.get_logger().info('Vanishing point detector ready.')

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]
        roi_top = h // 3

        # ── 1. Edge detection inside the ROI ─────────────────────────────
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi     = gray[roi_top:, :]
        edges   = cv2.Canny(roi, 50, 150)

        # ── 2. Hough line detection ───────────────────────────────────────
        lines = cv2.HoughLinesP(
            edges,
            rho=1, theta=np.pi / 180, threshold=40,
            minLineLength=30, maxLineGap=15
        )

        left_pts, right_pts = [], []
        annotated = frame.copy()

        if lines is not None:
            for seg in lines:
                x1, y1, x2, y2 = seg[0]

                if x2 == x1:
                    continue
                slope = (y2 - y1) / (x2 - x1)

                # Skip near-horizontal (grass texture) and near-vertical (posts)
                if abs(slope) < 0.3 or abs(slope) > 10.0:
                    continue

                # Offset y into full-frame coordinates for drawing
                fy1, fy2 = y1 + roi_top, y2 + roi_top

                if slope < 0:
                    left_pts += [(x1, y1), (x2, y2)]
                    cv2.line(annotated, (x1, fy1), (x2, fy2), (255, 100, 0), 1)   # blue-ish
                else:
                    right_pts += [(x1, y1), (x2, y2)]
                    cv2.line(annotated, (x1, fy1), (x2, fy2), (0, 100, 255), 1)   # orange-ish

        # ── 3. Fit a line to each group, find their intersection ──────────
        vp_x = w // 2   # default: assume centred
        vp_confidence = 0

        left_fit  = _fit_line(left_pts)
        right_fit = _fit_line(right_pts)

        if left_fit and right_fit:
            ix, iy = _intersect(left_fit, right_fit)
            iy_full = iy + roi_top   # convert ROI y → full-frame y

            # Accept the VP only if it falls in the upper 2/3 of the frame
            # (rows converging below the horizon means the geometry is broken)
            if 0 < ix < w and iy_full < h * 2 // 3:
                vp_x = int(ix)
                vp_confidence = min(len(left_pts), len(right_pts))
                cv2.circle(annotated, (vp_x, int(iy_full)), 8,  (0, 255, 255), -1)
                cv2.circle(annotated, (vp_x, int(iy_full)), 14, (0, 255, 255), 2)

        heading_error = vp_x - w // 2

        # ── 4. Visualisation ──────────────────────────────────────────────
        cv2.line(annotated, (0, roi_top), (w, roi_top), (0, 220, 220), 1)   # ROI boundary
        cv2.line(annotated, (w // 2, roi_top), (w // 2, h), (255, 255, 255), 1)  # centre ref

        cv2.putText(annotated,
                    f'VP heading error: {heading_error:+d} px',
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(annotated,
                    f'confidence: {vp_confidence} pts',
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        cv2.imshow('Canny Edges', edges)
        cv2.imshow('Vanishing Point', annotated)
        cv2.waitKey(1)


# ── Helpers (module-level, no state needed) ───────────────────────────────────

def _fit_line(pts: list):
    """Fit y = mx + b to a list of (x, y) points. Returns (m, b) or None."""
    if len(pts) < 2:
        return None
    xs = np.array([p[0] for p in pts], dtype=np.float32)
    ys = np.array([p[1] for p in pts], dtype=np.float32)
    m, b = np.polyfit(xs, ys, 1)
    return (float(m), float(b))


def _intersect(left, right):
    """Intersect y = m1*x + b1 with y = m2*x + b2. Returns (x, y)."""
    m1, b1 = left
    m2, b2 = right
    if abs(m1 - m2) < 1e-6:   # parallel — no intersection
        return (0.0, 0.0)
    x = (b2 - b1) / (m1 - m2)
    y = m1 * x + b1
    return (x, y)


def main(args=None):
    rclpy.init(args=args)
    node = VanishingPointDetector()
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
