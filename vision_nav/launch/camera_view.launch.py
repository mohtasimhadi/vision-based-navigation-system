from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'Kp', default_value='0.005',
            description='Proportional gain for heading control (rad/s per px)'
        ),
        DeclareLaunchArgument(
            'Kd', default_value='0.001',
            description='Derivative gain to dampen oscillation'
        ),
        DeclareLaunchArgument(
            'linear_x', default_value='0.2',
            description='Constant forward speed (m/s)'
        ),
        DeclareLaunchArgument(
            'use_vp', default_value='true',
            description='Use vanishing-point heading when confidence is high'
        ),
        DeclareLaunchArgument(
            'corridor_idx', default_value='0',
            description='Which row to follow: 0=C2_left, 1=C1_inner, 2=C3_right'
        ),

        # Bridge: Gazebo /camera  →  ROS 2 /camera/image_raw
        # Bridge: ROS 2 /cmd_vel  →  Gazebo /cmd_vel
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='bridge',
            arguments=[
                '/camera@sensor_msgs/msg/Image[gz.msgs.Image',
                '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            ],
            remappings=[
                ('/camera', '/camera/image_raw'),
            ],
            output='screen'
        ),

        # Vision pipeline: segmentation + vanishing point + display
        Node(
            package='vision_nav',
            executable='vision_pipeline',
            name='vision_pipeline',
            output='screen'
        ),

        # Field traverser: multi-row state machine → /cmd_vel
        Node(
            package='vision_nav',
            executable='field_traverser',
            name='field_traverser',
            output='screen',
            parameters=[{
                'Kp': LaunchConfiguration('Kp'),
                'Kd': LaunchConfiguration('Kd'),
                'linear_x': LaunchConfiguration('linear_x'),
                'corridor_idx': LaunchConfiguration('corridor_idx'),
            }]
        ),
    ])
