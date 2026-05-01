import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64, Int32


class FieldTraverser(Node):
    """
    Single-row follower using vision.

    The robot is spawned at the start of a corridor (selected before simulation).
    It follows that corridor using vision and stops when the row ends.
    """

    # Corridor centres must match utils/scenarios.py geometry
    ROWS = [
        {'name': 'C2_left',  'y': -0.675, 'dir':  1, 'x_start': -0.5, 'x_end': 9.4},
        {'name': 'C1_inner', 'y':  0.40, 'dir': -1, 'x_start':  9.4, 'x_end': -0.5},
        {'name': 'C3_right', 'y':  1.40, 'dir':  1, 'x_start': -0.5, 'x_end': 9.4},
    ]

    def __init__(self):
        super().__init__('field_traverser')

        # ── Parameters ────────────────────────────────────────────────────
        self.Kp = self.declare_parameter('Kp', 0.006).value
        self.Kd = self.declare_parameter('Kd', 0.0015).value
        self.linear_x = self.declare_parameter('linear_x', 0.35).value
        self.max_angular_z = self.declare_parameter('max_angular_z', 1.2).value
        self.corridor_idx = self.declare_parameter('corridor_idx', 0).value

        # ── Vision state ──────────────────────────────────────────────────
        self.heading_hist = 0.0
        self.heading_vp = 0.0
        self.vp_confidence = 0
        self.corridor_width = 0.0
        self.left_peak = 0.0
        self.right_peak = 0.0
        self.got_heading = False
        self.last_heading_time = self.get_clock().now()

        self.create_subscription(Float64, '/vision/heading_error',
                                 self._heading_cb, 10)
        self.create_subscription(Float64, '/vision/vp_heading_error',
                                 self._vp_heading_cb, 10)
        self.create_subscription(Int32, '/vision/vp_confidence',
                                 self._confidence_cb, 10)
        self.create_subscription(Float64, '/vision/corridor_width',
                                 self._width_cb, 10)
        self.create_subscription(Float64, '/vision/left_peak',
                                 self._left_peak_cb, 10)
        self.create_subscription(Float64, '/vision/right_peak',
                                 self._right_peak_cb, 10)

        # ── Command output ────────────────────────────────────────────────
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self._control_loop)  # 20 Hz

        # ── State machine ─────────────────────────────────────────────────
        self.state = 'FOLLOW'

        # Dead-reckoning
        row = self.ROWS[self.corridor_idx]
        self.x = float(row['x_start'])
        self.y = float(row['y'])
        self.yaw = 0.0 if row['dir'] == 1 else math.pi
        self._last_v = 0.0
        self._last_w = 0.0
        self._last_t = self.get_clock().now()

        self._trip_dist = 0.0
        self._no_edge_since = None

        self.get_logger().info(
            f'Field traverser ready. Following {row["name"]} '
            f'dir={row["dir"]:+d} x∈[{row["x_start"]},{row["x_end"]}]'
        )

    # ── Callbacks ────────────────────────────────────────────────────────

    def _heading_cb(self, msg: Float64):
        self.heading_hist = msg.data
        self.got_heading = True
        self.last_heading_time = self.get_clock().now()

    def _vp_heading_cb(self, msg: Float64):
        self.heading_vp = msg.data

    def _confidence_cb(self, msg: Int32):
        self.vp_confidence = msg.data

    def _width_cb(self, msg: Float64):
        self.corridor_width = msg.data

    def _left_peak_cb(self, msg: Float64):
        self.left_peak = msg.data

    def _right_peak_cb(self, msg: Float64):
        self.right_peak = msg.data

    # ── Helpers ──────────────────────────────────────────────────────────

    def _heading_error(self):
        return self.heading_hist

    def _steer(self, heading):
        return max(-self.max_angular_z,
                   min(self.max_angular_z, -self.Kp * heading))

    def _speed_factor(self):
        err = abs(self._heading_error()) / 320.0
        factor = 1.0 - min(err * 1.5, 0.5)
        if self.corridor_width < 80.0:
            factor *= 0.5
        elif self.corridor_width < 120.0:
            factor *= 0.75
        if self.vp_confidence == 1:
            factor *= 0.6
        return factor

    def _end_of_row(self):
        """Distance-based end-of-row with optional visual early-exit."""
        row = self.ROWS[self.corridor_idx]
        row_len = abs(row['x_end'] - row['x_start'])
        if self._trip_dist > (row_len - 0.3):
            return True
        visual = (self.vp_confidence == 1 or self.corridor_width > 300)
        return visual and self._trip_dist > (row_len - 2.0)

    # ── Control loop ─────────────────────────────────────────────────────

    def _control_loop(self):
        now = self.get_clock().now()
        dt = (now - self._last_t).nanoseconds / 1e9
        self._last_t = now

        # Safety timeout
        if not self.got_heading:
            self.pub_cmd.publish(Twist())
            return
        vision_age = (now - self.last_heading_time).nanoseconds / 1e9
        if vision_age > 1.0:
            self.pub_cmd.publish(Twist())
            return

        twist = Twist()
        row = self.ROWS[self.corridor_idx]

        if self.state == 'FOLLOW':
            heading = self._heading_error()
            twist.linear.x = self.linear_x * self._speed_factor()
            twist.angular.z = self._steer(heading)
            self._trip_dist += abs(twist.linear.x) * dt

            if self.vp_confidence == 1:
                if self._no_edge_since is None:
                    self._no_edge_since = now
                no_edge_secs = (now - self._no_edge_since).nanoseconds / 1e9
            else:
                self._no_edge_since = None
                no_edge_secs = 0.0

            row_len = abs(row['x_end'] - row['x_start'])
            no_edge_timeout = no_edge_secs >= 3.0 and self._trip_dist > (row_len - 1.0)

            if self._end_of_row() or no_edge_timeout:
                self.get_logger().info(
                    f'Row {row["name"]} complete.'
                )
                self.state = 'DONE'

        elif self.state == 'DONE':
            twist.linear.x = 0.0
            twist.angular.z = 0.0

        # Integrate dead-reckoning
        self.x += twist.linear.x * math.cos(self.yaw) * dt
        self.y += twist.linear.x * math.sin(self.yaw) * dt
        self.yaw += twist.angular.z * dt
        self._last_v = twist.linear.x
        self._last_w = twist.angular.z

        self.pub_cmd.publish(twist)

        if now.nanoseconds % 1_000_000_000 < 55_000_000:
            self.get_logger().info(
                f'[{self.state}] {row["name"]}(dir={row["dir"]:+d}) '
                f'x={self.x:.1f} y={self.y:.1f} yaw={math.degrees(self.yaw):.0f}° '
                f'dist={self._trip_dist:.1f}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = FieldTraverser()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub_cmd.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
