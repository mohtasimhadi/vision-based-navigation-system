import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


GREEN_LOW  = np.array([25,  40,  40])   # yellow-green to green (crops)
GREEN_HIGH = np.array([85, 255, 255])

SOIL_LOW   = np.array([ 5,  30,  20])   # brown/orange (bare soil)
SOIL_HIGH  = np.array([20, 200, 200])


class RowDetector(Node):
    def __init__(self):
        super().__init__('row_detector')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self._callback,
            10
        )
        self.get_logger().info('Row detector ready.')

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        green_mask = cv2.inRange(hsv, GREEN_LOW, GREEN_HIGH)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)

        roi_top = h // 3
        green_roi = green_mask[roi_top:, :]

        col_green = np.sum(green_roi, axis=0).astype(np.float32)

        threshold = col_green.max() * 0.3
        corridor_cols = np.where(col_green < threshold)[0]

        if len(corridor_cols) > 0:
            corridor_x = int(np.median(corridor_cols))
        else:
            corridor_x = w // 2   # fallback: assume centred

        heading_error = corridor_x - w // 2   # negative = veer left

        self.get_logger().debug(f'corridor_x={corridor_x}  error={heading_error:+d}px')

        annotated = frame.copy()

        overlay = np.zeros_like(frame)
        overlay[green_mask > 0] = (0, 200, 0)
        annotated = cv2.addWeighted(annotated, 1.0, overlay, 0.4, 0)

        cv2.line(annotated, (0, roi_top), (w, roi_top), (0, 220, 220), 1)

        cv2.line(annotated, (w // 2, roi_top), (w // 2, h), (255, 255, 255), 1)

        cv2.line(annotated, (corridor_x, roi_top), (corridor_x, h), (0, 0, 255), 2)

        label = f'heading error: {heading_error:+d} px'
        cv2.putText(annotated, label, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow('Green Mask', green_mask)
        cv2.imshow('Row Detection', annotated)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = RowDetector()
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
