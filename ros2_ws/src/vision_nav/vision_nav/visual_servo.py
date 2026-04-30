import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64, Int32


class VisualServo(Node):
    """
    Step 4: P-controller visual servoing.
    Subscribes to heading errors from the vision pipeline and publishes
    Twist messages to /cmd_vel to keep the robot centred between crop rows.
    """

    def __init__(self):
        super().__init__('visual_servo')

        # ── Parameters (tune at runtime) ──────────────────────────────────
        self.Kp = self.declare_parameter('Kp', 0.005).value
        self.linear_x = self.declare_parameter('linear_x', 0.3).value
        self.min_confidence = self.declare_parameter('min_confidence', 2).value
        self.max_angular_z = self.declare_parameter('max_angular_z', 1.0).value
        self.use_vp = self.declare_parameter('use_vp', True).value

        # ── State ─────────────────────────────────────────────────────────
        self.heading_hist = 0.0
        self.heading_vp = 0.0
        self.vp_confidence = 0
        self.got_heading = False
        self.last_heading_time = self.get_clock().now()

        # ── Subscribers ───────────────────────────────────────────────────
        self.create_subscription(Float64, '/vision/heading_error',
                                 self._heading_cb, 10)
        self.create_subscription(Float64, '/vision/vp_heading_error',
                                 self._vp_heading_cb, 10)
        self.create_subscription(Int32, '/vision/vp_confidence',
                                 self._confidence_cb, 10)

        # ── Publisher + control loop ──────────────────────────────────────
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self._control_loop)  # 20 Hz

        self.get_logger().info(
            f'Visual servo ready. Kp={self.Kp}, linear_x={self.linear_x}, '
            f'use_vp={self.use_vp}'
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

    # ── Control loop ─────────────────────────────────────────────────────

    def _control_loop(self):
        twist = Twist()

        # Safety timeout: stop if we lose vision data for > 1 s
        dt = (self.get_clock().now() - self.last_heading_time).nanoseconds / 1e9
        if not self.got_heading or dt > 1.0:
            self.pub_cmd.publish(twist)
            return

        # Choose heading source: vanishing point if confident, else histogram
        if self.use_vp and self.vp_confidence >= self.min_confidence:
            heading_error = self.heading_vp
            src = 'VP'
        else:
            heading_error = self.heading_hist
            src = 'HIST'

        # P-control
        twist.linear.x = self.linear_x
        twist.angular.z = -self.Kp * heading_error
        twist.angular.z = max(-self.max_angular_z,
                              min(self.max_angular_z, twist.angular.z))

        self.pub_cmd.publish(twist)

        # Debug at 2 Hz
        if self.get_clock().now().nanoseconds % 500_000_000 < 50_000_000:
            self.get_logger().debug(
                f'cmd: lin={twist.linear.x:.2f} ang={twist.angular.z:.3f} '
                f'[{src}] err={heading_error:.1f}px conf={self.vp_confidence}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = VisualServo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Send stop command before shutting down
        node.pub_cmd.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
