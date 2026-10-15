import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value='',
        description='Kayitli harita dosyasi (SLAM modunda bos birakın)'
    )

    nav2_params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_dir, 'config', 'nav2_params.yaml'),
        description='Full path to the ROS2 parameters file to use for all launched nodes'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Gerçek robot için false, Gazebo simülasyonu için true'
    )

    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='RViz2 açilsin mi? Pi üzerinde varsayilan false'
    )


    slam_arg = DeclareLaunchArgument(
        'slam',
        default_value='False',
        description='Whether to run SLAM (live mapping) instead of AMCL'
    )

    slam_params_arg = DeclareLaunchArgument(
        'slam_params_file',
        default_value=os.path.join(pkg_dir, 'config', 'slam_toolbox_params.yaml'),
        description='Full path to the ROS2 parameters file to use for the slam_toolbox node'
    )

    # Nav2 Bringup (AMCL/SLAM, Planner, Controller, Costmaps, Lifecycle Manager)
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': LaunchConfiguration('params_file'),
            'slam': LaunchConfiguration('slam'),
            'slam_params_file': LaunchConfiguration('slam_params_file'),
            'autostart': 'true'
        }.items()
    )

    # RViz2 with Nav2 configuration
    custom_rviz_config = os.path.join(pkg_dir, 'config', 'nav2_rviz.rviz')
    default_rviz_config = os.path.join(nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz')
    rviz_config = custom_rviz_config if os.path.exists(custom_rviz_config) else default_rviz_config

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    return LaunchDescription([
        map_arg,
        nav2_params_arg,
        use_sim_time_arg,
        use_rviz_arg,
        slam_arg,
        slam_params_arg,
        nav2_bringup,
        rviz_node
    ])
