import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float64, Int32
from cv_bridge import CvBridge
import cv2
import numpy as np


# ── Tuning constants ──────────────────────────────────────────────────────────
ROI_TOP_FRAC   = 1 / 3   # ignore this top fraction of the image (sky/canopy)
HEADING_ALPHA  = 0.35    # EMA smoothing weight (lower = smoother, more lag)


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
        self._heading_smooth = 0.0
        self.get_logger().info('Vision pipeline (wall-gap) ready.')

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w  = frame.shape[:2]

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        heading, clear, left_wall_x, right_wall_x = _wall_gap_heading(edges, w, h)

        # EMA smoothing; reset immediately when path is clear
        if clear:
            self._heading_smooth = 0.0
        else:
            self._heading_smooth = (HEADING_ALPHA * heading
                                    + (1.0 - HEADING_ALPHA) * self._heading_smooth)

        gap_width = float(right_wall_x - left_wall_x)

        self.pub_heading.publish(Float64(data=self._heading_smooth))
        self.pub_vp_heading.publish(Float64(data=self._heading_smooth))
        self.pub_confidence.publish(Int32(data=int(clear)))
        self.pub_corridor_w.publish(Float64(data=gap_width))
        self.pub_left_peak.publish(Float64(data=float(left_wall_x)))
        self.pub_right_peak.publish(Float64(data=float(right_wall_x)))

        _draw_debug(frame, edges, heading, clear, left_wall_x, right_wall_x, w, h)


# ── Core algorithm ────────────────────────────────────────────────────────────

def _wall_gap_heading(edges, img_w, img_h):
    """
    Collapse the lower portion of the edge image into a 1-D occupancy row.

    Left wall:  rightmost occupied column in the left  image half  → inner boundary of left  plants
    Right wall: leftmost  occupied column in the right image half  → inner boundary of right plants

    The safe corridor is the gap between those two boundaries.
    Heading = gap_centre - image_centre  (positive → gap is right of centre → steer right).
    Clear = no wall edges found on either side (row has ended).
    """
    roi_top  = int(img_h * ROI_TOP_FRAC)
    band     = edges[roi_top:, :]
    occupied = np.any(band > 0, axis=0)   # True where any row in the band has an edge

    cx = img_w // 2

    left_cols  = np.where(occupied[:cx])[0]       # occupied columns in left  half
    right_cols = np.where(occupied[cx:])[0] + cx  # occupied columns in right half

    no_left  = len(left_cols)  == 0
    no_right = len(right_cols) == 0

    left_wall_x  = int(left_cols[-1])  if not no_left  else 0
    right_wall_x = int(right_cols[0])  if not no_right else img_w - 1

    clear      = no_left and no_right
    gap_centre = (left_wall_x + right_wall_x) / 2.0
    heading    = gap_centre - cx   # positive → steer right, negative → steer left

    return heading, clear, left_wall_x, right_wall_x


# ── Debug visualisation ───────────────────────────────────────────────────────

def _draw_debug(frame, edges, heading, clear, left_wall_x, right_wall_x, w, h):
    ann = frame.copy()
    cx  = w // 2
    roi_top = int(h * ROI_TOP_FRAC)

    # ROI boundary
    cv2.line(ann, (0, roi_top), (w, roi_top), (0, 220, 220), 1)

    # Don't-go-zone shading: left plant wall (red) and right plant wall (red)
    overlay = ann.copy()
    cv2.rectangle(overlay, (0, roi_top), (left_wall_x, h - 1),  (0, 0, 120), -1)
    cv2.rectangle(overlay, (right_wall_x, roi_top), (w - 1, h - 1), (0, 0, 120), -1)
    cv2.addWeighted(overlay, 0.35, ann, 0.65, 0, ann)

    # Wall boundary lines
    cv2.line(ann, (left_wall_x,  roi_top), (left_wall_x,  h - 1), (0, 0, 255), 2)
    cv2.line(ann, (right_wall_x, roi_top), (right_wall_x, h - 1), (0, 0, 255), 2)

    # Gap centre target and image centre reference
    gap_centre = int((left_wall_x + right_wall_x) / 2)
    cv2.line(ann, (cx,         roi_top), (cx,         h - 1), (255, 255, 255), 1)
    cv2.line(ann, (gap_centre, roi_top), (gap_centre, h - 1),
             (0, 255, 0) if clear else (0, 255, 255), 2)

    # Edge panel
    edge_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cv2.line(edge_bgr, (0, roi_top), (w, roi_top), (0, 220, 220), 1)
    cv2.line(edge_bgr, (left_wall_x,  roi_top), (left_wall_x,  h - 1), (0, 0, 255), 2)
    cv2.line(edge_bgr, (right_wall_x, roi_top), (right_wall_x, h - 1), (0, 0, 255), 2)

    status = 'CLEAR' if clear else f'L:{left_wall_x}  R:{right_wall_x}  gap:{right_wall_x - left_wall_x}px'
    cv2.putText(ann, f'err:{heading:+.1f}px  {status}',
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

    cv2.imshow('Vision Pipeline',
               np.hstack([cv2.resize(ann,      (640, 480)),
                          cv2.resize(edge_bgr, (640, 480))]))
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
