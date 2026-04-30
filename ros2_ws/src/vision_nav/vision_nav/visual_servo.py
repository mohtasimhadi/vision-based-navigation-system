import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64, Int32


class VisualServo(Node):
    """
    Improved Step 4: PD-controller visual servoing with speed modulation.
    """

    def __init__(self):
        super().__init__('visual_servo')

        # ── Parameters ────────────────────────────────────────────────────
        self.Kp = self.declare_parameter('Kp', 0.005).value
        self.Kd = self.declare_parameter('Kd', 0.001).value
        self.linear_x = self.declare_parameter('linear_x', 0.3).value
        self.min_confidence = self.declare_parameter('min_confidence', 2).value
        self.max_angular_z = self.declare_parameter('max_angular_z', 1.0).value
        self.use_vp = self.declare_parameter('use_vp', True).value

        # ── State ─────────────────────────────────────────────────────────
        self.heading_hist = 0.0
        self.heading_vp = 0.0
        self.vp_confidence = 0
        self.corridor_width = 200.0   # pixels, starts optimistic
        self.got_heading = False
        self.last_heading_time = self.get_clock().now()

        self._last_err = 0.0
        self._last_t = self.get_clock().now()

        # ── Subscribers ───────────────────────────────────────────────────
        self.create_subscription(Float64, '/vision/heading_error',
                                 self._heading_cb, 10)
        self.create_subscription(Float64, '/vision/vp_heading_error',
                                 self._vp_heading_cb, 10)
        self.create_subscription(Int32, '/vision/vp_confidence',
                                 self._confidence_cb, 10)
        self.create_subscription(Float64, '/vision/corridor_width',
                                 self._width_cb, 10)

        # ── Publisher + control loop ──────────────────────────────────────
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self._control_loop)  # 20 Hz

        self.get_logger().info(
            f'Visual servo ready. Kp={self.Kp}, Kd={self.Kd}, '
            f'linear_x={self.linear_x}, use_vp={self.use_vp}'
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

    # ── Control loop ─────────────────────────────────────────────────────

    def _control_loop(self):
        twist = Twist()

        # Safety timeout: stop if we lose vision data for > 1 s
        dt = (self.get_clock().now() - self.last_heading_time).nanoseconds / 1e9
        if not self.got_heading or dt > 1.0:
            self.pub_cmd.publish(twist)
            return

        # Choose heading source
        if self.use_vp and self.vp_confidence >= self.min_confidence:
            heading_error = self.heading_vp
            src = 'VP'
        else:
            heading_error = self.heading_hist
            src = 'HIST'

        # ── PD steering ───────────────────────────────────────────────────
        now = self.get_clock().now()
        dt_loop = (now - self._last_t).nanoseconds / 1e9
        if dt_loop <= 0:
            dt_loop = 0.05

        d_err = (heading_error - self._last_err) / dt_loop
        self._last_err = heading_error
        self._last_t = now

        twist.angular.z = -(self.Kp * heading_error + self.Kd * d_err)
        twist.angular.z = max(-self.max_angular_z,
                              min(self.max_angular_z, twist.angular.z))

        # ── Speed modulation ──────────────────────────────────────────────
        # 1. Slow down when far off centre
        err_norm = abs(heading_error) / 320.0  # normalised to ~half image width
        speed_factor = 1.0 - min(err_norm * 1.5, 0.7)  # at most 70% reduction

        # 2. Slow down when corridor is pinched (< 80 px ~ obstacle ahead)
        if self.corridor_width < 80.0:
            speed_factor *= 0.5
        elif self.corridor_width < 120.0:
            speed_factor *= 0.75

        # 3. Slow down when VP confidence is low (rows not visible)
        if self.vp_confidence == 0:
            speed_factor *= 0.6

        twist.linear.x = self.linear_x * speed_factor

        self.pub_cmd.publish(twist)

        # Debug at 2 Hz
        if now.nanoseconds % 500_000_000 < 50_000_000:
            self.get_logger().debug(
                f'cmd: lin={twist.linear.x:.2f} ang={twist.angular.z:.3f} '
                f'[{src}] err={heading_error:.1f}px w={self.corridor_width:.0f} '
                f'conf={self.vp_confidence}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = VisualServo()
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
