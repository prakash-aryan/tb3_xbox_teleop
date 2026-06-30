import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    xbox_cfg = os.path.join(
        get_package_share_directory('teleop_twist_joy'), 'config', 'xbox.config.yaml')
    proximity = LaunchConfiguration('proximity')

    return LaunchDescription([
        DeclareLaunchArgument(
            'proximity', default_value='false',
            description='Enable the lidar proximity rumble warning'),

        Node(
            package='joy', executable='joy_node', name='joy_node',
            parameters=[{
                'device_id': 0,
                'deadzone': 0.1,
                'autorepeat_rate': 20.0,
            }]),

        Node(
            package='teleop_twist_joy', executable='teleop_node',
            name='teleop_twist_joy_node',
            parameters=[xbox_cfg, {
                'publish_stamped_twist': True,
                'require_enable_button': False,
                'axis_linear.x': 1,
                'scale_linear.x': 0.22,
                'scale_linear_turbo.x': 0.22,
                'axis_angular.yaw': 2,
                'scale_angular.yaw': 2.84,
            }],
            remappings=[('/cmd_vel', '/cmd_vel_teleop')]),

        Node(
            package='tb3_xbox_teleop', executable='teleop_brake_rumble',
            name='teleop_brake_rumble',
            parameters=[{
                'proximity_warning': ParameterValue(proximity, value_type=bool),
            }]),
    ])
