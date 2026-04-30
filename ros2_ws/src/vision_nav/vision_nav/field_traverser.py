import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64, Int32


class FieldTraverser(Node):
    """
    Multi-row field traversal using vision + dead-reckoning.

    Starts at the LEFT corridor (C2) and works rightward:
      C2_left → C1_inner → C3_right

    Pattern for each corridor:
      FOLLOW forward  → end-of-row detected
      TURN_PRE  90° left   (face +Y, toward next corridor)
      TRANSVERSE 1.3 m     (drive across headland)
      TURN_POST 90° right  (face +X, align with next corridor)
      ALIGN                (verify corridor ahead)
      FOLLOW forward
    """

    def __init__(self):
        super().__init__('field_traverser')

        # ── Parameters ────────────────────────────────────────────────────
        self.Kp = self.declare_parameter('Kp', 0.006).value
        self.Kd = self.declare_parameter('Kd', 0.0015).value
        self.linear_x = self.declare_parameter('linear_x', 0.35).value
        self.max_angular_z = self.declare_parameter('max_angular_z', 1.2).value

        self.turn_speed = 0.6          # rad/s for 90° turns
        self.transverse_speed = 0.25   # m/s for headland driving
        self.align_speed = 0.5         # rad/s for corridor search
        self.row_length = 9.5          # m, visual-cue backup distance

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

        # ── Command ───────────────────────────────────────────────────────
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self._control_loop)  # 20 Hz

        # ── State machine ─────────────────────────────────────────────────
        self.state = 'FOLLOW'
        self.corridor_idx = 0          # 0=C2_left, 1=C1_inner, 2=C3_right
        self.corridor_names = ['C2_left', 'C1_inner', 'C3_right']

        # Dead-reckoning (integrated from /cmd_vel)
        self.x = -0.5
        self.y = -1.3
        self.yaw = 0.0
        self._last_v = 0.0
        self._last_w = 0.0
        self._last_t = self.get_clock().now()

        self._trip_dist = 0.0          # distance since last state change
        self._turn_start_yaw = 0.0

        self.get_logger().info(
            'Field traverser ready. Start=%s Kp=%.4f Kd=%.4f lin=%.2f' %
            (self.corridor_names[self.corridor_idx], self.Kp, self.Kd, self.linear_x)
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
        if self.vp_confidence >= 2:
            return self.heading_vp
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
        if self.vp_confidence == 0:
            factor *= 0.6
        return factor

    def _end_of_row(self):
        """Visual end-of-row detection."""
        visual = (self.vp_confidence == 0 or self.corridor_width > 300)
        return visual and self._trip_dist > 7.0

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

        if self.state == 'FOLLOW':
            heading = self._heading_error()
            twist.linear.x = self.linear_x * self._speed_factor()
            twist.angular.z = self._steer(heading)
            self._trip_dist += abs(twist.linear.x) * dt

            if self._end_of_row():
                if self.corridor_idx >= 2:
                    self._change_state('DONE')
                else:
                    self._change_state('TURN_PRE')

        elif self.state == 'TURN_PRE':
            # Turn left 90° (from +X to +Y)
            twist.linear.x = 0.0
            twist.angular.z = self.turn_speed
            self.yaw += twist.angular.z * dt
            if self.yaw - self._turn_start_yaw >= math.pi / 2 - 0.05:
                self._change_state('TRANSVERSE')

        elif self.state == 'TRANSVERSE':
            # Drive straight across headland toward next corridor
            twist.linear.x = self.transverse_speed
            twist.angular.z = 0.0
            self._trip_dist += abs(twist.linear.x) * dt
            if self._trip_dist >= 1.35:  # 1.3 m + small margin
                self._change_state('TURN_POST')

        elif self.state == 'TURN_POST':
            # Turn right 90° (from +Y back to +X)
            twist.linear.x = 0.0
            twist.angular.z = -self.turn_speed
            self.yaw += twist.angular.z * dt
            if self._turn_start_yaw - self.yaw >= math.pi / 2 - 0.05:
                self._change_state('ALIGN')

        elif self.state == 'ALIGN':
            # Fine-tune: spin slowly until corridor is solidly ahead
            twist.linear.x = 0.0
            twist.angular.z = self.align_speed * 0.3
            self.yaw += twist.angular.z * dt
            if self.corridor_width > 100 and abs(self.heading_hist) < 50:
                self.corridor_idx += 1
                self._change_state('FOLLOW')
                self.get_logger().info(
                    f'→ Entered {self.corridor_names[self.corridor_idx]}'
                )

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
                f'[{self.state}] {self.corridor_names[min(self.corridor_idx,2)]} '
                f'x={self.x:.1f} y={self.y:.1f} yaw={math.degrees(self.yaw):.0f}° '
                f'dist={self._trip_dist:.1f}'
            )

    def _change_state(self, new_state):
        self.get_logger().info(f'{self.state} → {new_state}')
        self.state = new_state
        self._trip_dist = 0.0
        self._turn_start_yaw = self.yaw


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
