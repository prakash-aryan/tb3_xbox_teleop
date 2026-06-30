import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    os.environ.setdefault('TURTLEBOT3_MODEL', 'burger')

    tb3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')
    tb3_launch_dir = os.path.join(tb3_gazebo, 'launch')

    resource_paths = [
        os.environ.get('GZ_SIM_RESOURCE_PATH', ''),
        os.path.join(tb3_gazebo, 'models'),
    ]
    os.environ['GZ_SIM_RESOURCE_PATH'] = os.pathsep.join(p for p in resource_paths if p)

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = os.path.join(tb3_gazebo, 'worlds', 'turtlebot3_house.world')

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r -s -v2 ', world], 'on_exit_shutdown': 'true'}.items())

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': '-g -v2 ', 'on_exit_shutdown': 'true'}.items())

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_launch_dir, 'robot_state_publisher.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items())

    spawn = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_launch_dir, 'spawn_turtlebot3.launch.py')),
        launch_arguments={'x_pose': '-2.0', 'y_pose': '-0.5'}.items())

    return LaunchDescription([gzserver, gzclient, spawn, robot_state_publisher])
