import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    launch_dir = os.path.join(get_package_share_directory('tb3_xbox_teleop'), 'launch')
    proximity = LaunchConfiguration('proximity')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'sim.launch.py')))

    teleop = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'teleop.launch.py')),
        launch_arguments={'proximity': proximity}.items())

    return LaunchDescription([
        DeclareLaunchArgument(
            'proximity', default_value='false',
            description='Enable the lidar proximity rumble warning'),
        sim,
        teleop,
    ])
