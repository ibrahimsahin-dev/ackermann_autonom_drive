import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    ros_gz_sim_dir = get_package_share_directory('ros_gz_sim')

    world_path = os.path.join(pkg_dir, 'worlds', 'test_arena.sdf')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'ackermann_car.urdf.xacro')

    headless_arg = DeclareLaunchArgument(
        'headless',
        default_value='false',
        description='Run Gazebo headless (server only) if true'
    )

    # Convert Xacro to URDF
    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    # Gazebo Sim (GUI mode)
    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_dir, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': f'-r -v 2 {world_path}'
        }.items(),
        condition=UnlessCondition(LaunchConfiguration('headless'))
    )

    # Gazebo Sim (Headless mode)
    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_dir, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': f'-s -r -v 2 {world_path}'
        }.items(),
        condition=IfCondition(LaunchConfiguration('headless'))
    )

    # Joint State Publisher
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    # Spawn Robot into Gazebo Sim
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'ackermann_car',
            '-topic', 'robot_description',
            '-x', '-3.5',
            '-y', '-2.5',
            '-z', '0.1',
            '-Y', '0.0'
        ]
    )

    laser_odom_arg = DeclareLaunchArgument(
        'use_laser_odom',
        default_value='true',
        description='Use RF2O laser scan matching odometry if true, else wheel odometry'
    )

    # ROS-Gazebo Parameter Bridge (when Laser Odometry is used)
    bridge_laser = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '/odom_wheel@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
        ],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('use_laser_odom'))
    )

    # ROS-Gazebo Parameter Bridge (fallback when wheel odometry is used directly)
    bridge_wheel = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '/odom_wheel@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/tf_wheel@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            '/camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
        ],
        remappings=[
            ('/odom_wheel', '/odom'),
            ('/tf_wheel', '/tf')
        ],
        parameters=[{'use_sim_time': True}],
        condition=UnlessCondition(LaunchConfiguration('use_laser_odom'))
    )

    # RF2O Laser Scan Matching Odometry Node
    laser_odometry = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        output='screen',
        parameters=[{
            'laser_scan_topic': '/scan',
            'odom_topic': '/odom',
            'publish_tf': True,
            'base_frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'init_pose_from_topic': '',
            'freq': 10.0,
            'use_sim_time': True
        }],
        condition=IfCondition(LaunchConfiguration('use_laser_odom'))
    )

    return LaunchDescription([
        headless_arg,
        laser_odom_arg,
        gazebo_gui,
        gazebo_headless,
        joint_state_publisher,
        robot_state_publisher,
        spawn_robot,
        bridge_laser,
        bridge_wheel,
        laser_odometry
    ])
