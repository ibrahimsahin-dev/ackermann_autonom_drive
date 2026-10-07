import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    slam_config = os.path.join(pkg_dir, 'config', 'slam_toolbox_params.yaml')
    rviz_config = os.path.join(pkg_dir, 'config', 'sim_rviz.rviz')

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_config,
            {'use_sim_time': True}
        ]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config] if os.path.exists(rviz_config) else [],
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        slam_node,
        rviz_node
    ])
