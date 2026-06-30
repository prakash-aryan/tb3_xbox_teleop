import os
from glob import glob

from setuptools import setup

package_name = 'tb3_xbox_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Prakash Aryan',
    maintainer_email='prakasharyan25@gmail.com',
    description='Xbox controller teleop for TurtleBot3 in Gazebo with brake and haptic feedback',
    license='MIT',
    entry_points={
        'console_scripts': [
            'teleop_brake_rumble = tb3_xbox_teleop.teleop_brake_rumble:main',
        ],
    },
)
