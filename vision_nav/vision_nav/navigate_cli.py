#!/usr/bin/env python3
"""Simple CLI to send row-navigation commands to the field traverser."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


ROWS = ['C2_left', 'C1_inner', 'C3_right']


def main(args=None):
    rclpy.init(args=args)
    node = Node('navigate_cli')
    pub = node.create_publisher(Int32, '/target_row', 10)

    print('\n=== Row Navigator ===')
    print('Available rows:')
    for i, name in enumerate(ROWS):
        print(f'  {i} = {name}')
    print('  q = quit')
    print('=====================\n')

    # Wait for publisher to connect
    import time
    time.sleep(0.5)

    while rclpy.ok():
        try:
            choice = input('Select row (0/1/2/q): ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == 'q':
            break

        if choice not in ('0', '1', '2'):
            print('Invalid choice. Use 0, 1, 2, or q.')
            continue

        idx = int(choice)
        pub.publish(Int32(data=idx))
        print(f'Sent command: navigate to {ROWS[idx]} (row {idx})')

    print('Exiting.')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
