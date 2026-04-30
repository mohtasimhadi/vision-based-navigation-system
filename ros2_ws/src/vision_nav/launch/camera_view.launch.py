from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='camera_bridge',
            arguments=[
                '/camera@sensor_msgs/msg/Image[gz.msgs.Image'
            ],
            remappings=[
                ('/camera', '/camera/image_raw')
            ],
            output='screen'
        ),

        Node(
            package='vision_nav',
            executable='vision_pipeline',
            name='vision_pipeline',
            output='screen'
        ),
    ])
