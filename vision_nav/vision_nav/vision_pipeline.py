import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float64, Int32
from cv_bridge import CvBridge
import cv2
import numpy as np


# ── Tuning constants ──────────────────────────────────────────────────────────
ROI_TOP_FRAC    = 0.35
ROI_BOTTOM_FRAC = 0.85
MIN_CC_AREA     = 300
MORPH_KERNEL    = np.ones((3, 3), np.uint8)
HEADING_ALPHA   = 0.35


class VisionPipeline(Node):
    def __init__(self):
        super().__init__('vision_pipeline')
        self.bridge = CvBridge()

        # Front camera — drives the processing pipeline
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self._callback, 10
        )
        # Observer cameras — display only, updated asynchronously
        self.sub_chase = self.create_subscription(
            Image, '/camera_chase/image_raw', self._chase_cb, 10
        )
        self.sub_global = self.create_subscription(
            Image, '/camera_global/image_raw', self._global_cb, 10
        )
        self._chase_frame  = None
        self._global_frame = None

        self.pub_heading    = self.create_publisher(Float64, '/vision/heading_error',    10)
        self.pub_vp_heading = self.create_publisher(Float64, '/vision/vp_heading_error', 10)
        self.pub_confidence = self.create_publisher(Int32,   '/vision/vp_confidence',    10)
        self.pub_corridor_w = self.create_publisher(Float64, '/vision/corridor_width',   10)
        self.pub_left_peak  = self.create_publisher(Float64, '/vision/left_peak',        10)
        self.pub_right_peak = self.create_publisher(Float64, '/vision/right_peak',       10)
        self._heading_smooth = 0.0
        self.get_logger().info('Vision pipeline (CC-filter) ready.')

    def _chase_cb(self, msg: Image):
        self._chase_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def _global_cb(self, msg: Image):
        self._global_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w  = frame.shape[:2]

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        heading, clear, left_wall_x, right_wall_x, cleaned_full, kept_info, \
            roi_top, roi_bottom, band_closed, labels = _wall_gap_heading(edges, w, h)

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

        _draw_debug(frame, edges, cleaned_full, kept_info, heading, clear,
                    left_wall_x, right_wall_x, roi_top, roi_bottom,
                    band_closed, labels, w, h,
                    self._chase_frame, self._global_frame)


# ── Core algorithm ────────────────────────────────────────────────────────────

def _wall_gap_heading(edges, img_w, img_h):
    roi_top    = int(img_h * ROI_TOP_FRAC)
    roi_bottom = int(img_h * ROI_BOTTOM_FRAC)
    band       = edges[roi_top:roi_bottom, :]

    band_closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, MORPH_KERNEL)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        band_closed, connectivity=8
    )

    cleaned = np.zeros_like(band_closed)
    kept_info = []
    for i in range(1, num_labels):
        area = int(stats[i, cv2.CC_STAT_AREA])
        x, y, bw, bh = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], \
                       stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        kept = area >= MIN_CC_AREA
        kept_info.append({'id': i, 'area': area, 'x': x, 'y': y,
                          'w': bw, 'h': bh, 'kept': kept})
        if kept:
            cleaned[labels == i] = 255

    occupied = np.any(cleaned > 0, axis=0)
    cx = img_w // 2
    left_cols  = np.where(occupied[:cx])[0]
    right_cols = np.where(occupied[cx:])[0] + cx
    no_left  = len(left_cols)  == 0
    no_right = len(right_cols) == 0
    left_wall_x  = int(left_cols[-1])  if not no_left  else 0
    right_wall_x = int(right_cols[0])  if not no_right else img_w - 1
    clear      = no_left and no_right
    gap_centre = (left_wall_x + right_wall_x) / 2.0
    heading    = gap_centre - cx

    cleaned_full = np.zeros_like(edges)
    cleaned_full[roi_top:roi_bottom, :] = cleaned

    return heading, clear, left_wall_x, right_wall_x, cleaned_full, kept_info, \
           roi_top, roi_bottom, band_closed, labels


# ── Debug visualisation ───────────────────────────────────────────────────────

def _draw_debug(frame, edges, cleaned_full, kept_info, heading, clear,
                left_wall_x, right_wall_x, roi_top, roi_bottom,
                band_closed, labels, w, h,
                chase_frame=None, global_frame=None):
    PW, PH  = 900, 675
    cx      = w // 2
    status  = 'CLEAR' if clear else f'L:{left_wall_x}  R:{right_wall_x}  gap:{right_wall_x - left_wall_x}px'
    n_total = len(kept_info)
    n_kept  = sum(1 for c in kept_info if c['kept'])
    band_h  = roi_bottom - roi_top

    # ── Panel 0: raw camera ───────────────────────────────────────────────────
    p0 = frame.copy()
    cv2.line(p0, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p0, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p0, '0. RAW CAMERA', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p0, 'cyan = ROI borders', (6, PH - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 220), 1)

    # ── Panel 1: full Canny ───────────────────────────────────────────────────
    p1 = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cv2.line(p1, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p1, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p1, '1. FULL CANNY', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p1, 'white = edges  cyan = ROI', (6, PH - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 220), 1)

    # ── Panel 2: ROI raw edges ────────────────────────────────────────────────
    p2 = np.zeros_like(edges)
    p2[roi_top:roi_bottom, :] = edges[roi_top:roi_bottom, :]
    p2 = cv2.cvtColor(p2, cv2.COLOR_GRAY2BGR)
    cv2.line(p2, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p2, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p2, '2. ROI RAW EDGES', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p2, 'white = edges in active band', (6, PH - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 220), 1)

    # ── Panel 3: after morphological close ────────────────────────────────────
    p3 = np.zeros_like(edges)
    p3[roi_top:roi_bottom, :] = band_closed
    p3 = cv2.cvtColor(p3, cv2.COLOR_GRAY2BGR)
    cv2.line(p3, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p3, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p3, '3. AFTER CLOSE', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p3, 'white = closed edges', (6, PH - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 220), 1)

    # ── Panel 4: connected components color-coded ─────────────────────────────
    cc_vis = np.zeros((band_h, w, 3), dtype=np.uint8)
    rng = np.random.default_rng(42)
    max_label = labels.max()
    for i in range(1, max_label + 1):
        color = tuple(rng.integers(80, 255, 3).tolist())
        cc_vis[labels == i] = color
    p4 = np.zeros_like(frame)
    p4[roi_top:roi_bottom, :] = cc_vis
    cv2.line(p4, (0, roi_top), (w, roi_top), (255, 255, 255), 2)
    cv2.line(p4, (0, roi_bottom), (w, roi_bottom), (255, 255, 255), 2)
    for c in kept_info:
        x1 = c['x']
        y1 = roi_top + c['y']
        txt = f"{c['area']}"
        col = (0, 255, 0) if c['kept'] else (0, 100, 255)
        cv2.putText(p4, txt, (x1, max(y1 - 2, roi_top + 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, col, 1)
    cv2.putText(p4, '4. CONNECTED COMPONENTS', (6, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p4, 'random = blobs  grn txt = keep  orn txt = discard', (6, PH - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 220, 220), 1)

    # ── Panel 5: discarded (filtered out) ─────────────────────────────────────
    discarded = np.zeros_like(band_closed)
    for c in kept_info:
        if not c['kept']:
            discarded[labels == c['id']] = 255
    p5 = np.zeros_like(edges)
    p5[roi_top:roi_bottom, :] = discarded
    p5 = cv2.cvtColor(p5, cv2.COLOR_GRAY2BGR)
    cv2.line(p5, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p5, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p5, '5. DISCARDED (filtered)', (6, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p5, 'white = grass/gravel/noise (< MIN_CC_AREA)', (6, PH - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 220, 220), 1)

    # ── Panel 6: kept (final) ─────────────────────────────────────────────────
    p6 = cv2.cvtColor(cleaned_full, cv2.COLOR_GRAY2BGR)
    for c in kept_info:
        if c['kept']:
            x1 = c['x']
            y1 = roi_top + c['y']
            x2 = x1 + c['w']
            y2 = y1 + c['h']
            cv2.rectangle(p6, (x1, y1), (x2, y2), (0, 210, 0), 1)
            cv2.putText(p6, f"{c['area']}", (x1, max(y1 - 2, roi_top + 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 210, 0), 1)
    cv2.line(p6, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p6, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p6, '6. KEPT (final)', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(p6, 'white = edges  green box + txt = kept blob', (6, PH - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 220, 220), 1)

    # ── Panel 7: navigation overlay ───────────────────────────────────────────
    p7 = frame.copy()
    overlay = p7.copy()
    cv2.rectangle(overlay, (0, roi_top), (left_wall_x, roi_bottom),  (0, 0, 120), -1)
    cv2.rectangle(overlay, (right_wall_x, roi_top), (w - 1, roi_bottom), (0, 0, 120), -1)
    cv2.addWeighted(overlay, 0.35, p7, 0.65, 0, p7)
    cv2.line(p7, (left_wall_x,  roi_top), (left_wall_x,  roi_bottom), (0, 0, 255), 2)
    cv2.line(p7, (right_wall_x, roi_top), (right_wall_x, roi_bottom), (0, 0, 255), 2)
    gap_centre = int((left_wall_x + right_wall_x) / 2)
    cv2.line(p7, (cx,         roi_top), (cx,         roi_bottom), (255, 255, 255), 1)
    cv2.line(p7, (gap_centre, roi_top), (gap_centre, roi_bottom),
             (0, 255, 0) if clear else (0, 255, 255), 2)
    cv2.line(p7, (0, roi_top), (w, roi_top), (0, 220, 220), 2)
    cv2.line(p7, (0, roi_bottom), (w, roi_bottom), (0, 220, 220), 2)
    cv2.putText(p7, f'7. NAV  err:{heading:+.1f}px  {status}',
                (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(p7, 'red = walls/dont-go  white = center  grn/yel = gap',
                (6, PH - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 220, 220), 1)
    cv2.putText(p7, f'CC: {n_kept}/{n_total} kept (>{MIN_CC_AREA}px)',
                (6, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 220), 1)

    # ── Assemble 3-row grid ────────────────────────────────────────────────────
    # Rows 0-1: 4 panels each (640×480).  Row 2: 2 observer panels (each 2-col wide).
    BORDER  = 6
    GRID_W  = PW * 4 + BORDER * 3   # 2578 px — total row width

    p = [cv2.resize(p0, (PW, PH)), cv2.resize(p1, (PW, PH)),
         cv2.resize(p2, (PW, PH)), cv2.resize(p3, (PW, PH)),
         cv2.resize(p4, (PW, PH)), cv2.resize(p5, (PW, PH)),
         cv2.resize(p6, (PW, PH)), cv2.resize(p7, (PW, PH))]

    border_h = np.full((PH, BORDER, 3), 255, dtype=np.uint8)
    border_v = np.full((BORDER, GRID_W, 3), 255, dtype=np.uint8)

    row0 = np.hstack([p[0], border_h, p[1], border_h, p[2], border_h, p[3]])
    row1 = np.hstack([p[4], border_h, p[5], border_h, p[6], border_h, p[7]])

    # Observer panels each take exactly half the grid width (minus the one border)
    OBS_W = (GRID_W - BORDER) // 2   # 1286 px

    def _obs_panel(src, label):
        panel = np.zeros((PH, OBS_W, 3), dtype=np.uint8)
        if src is not None:
            sh, sw = src.shape[:2]
            scale  = min(OBS_W / sw, PH / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            resized = cv2.resize(src, (nw, nh))
            x0 = (OBS_W - nw) // 2
            y0 = (PH    - nh) // 2
            panel[y0:y0 + nh, x0:x0 + nw] = resized
        cv2.putText(panel, label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 1)
        return panel

    p8 = _obs_panel(chase_frame,  '8. CHASE CAM')
    p9 = _obs_panel(global_frame, '9. GLOBAL TOP-DOWN')
    row2 = np.hstack([p8, border_h, p9])

    out = np.vstack([row0, border_v, row1, border_v, row2])

    cv2.imshow('Vision Pipeline', out)
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
