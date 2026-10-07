import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, Command, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'ackermann_car.urdf.xacro')

    # Argümanlar
    lidar_connection_arg = DeclareLaunchArgument(
        'lidar_connection',
        default_value='serial',
        description='LiDAR baglanti tipi: "serial" (USB) veya "ethernet"'
    )

    lidar_serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyACM0',
        description='Hokuyo LiDAR USB seri port yolu (/dev/ttyACM0 veya /dev/ttyUSB0)'
    )

    lidar_ip_arg = DeclareLaunchArgument(
        'ip_address',
        default_value='192.168.0.10',
        description='Hokuyo Ethernet LiDAR IP adresi'
    )

    use_rf2o_arg = DeclareLaunchArgument(
        'use_rf2o',
        default_value='true',
        description='Tekerlek enkoderi yerine Hokuyo LiDAR tabanli RF2O odometrisi kullan'
    )

    # Robot URDF Açıklaması (Gerçek Robot Boyutları ve TF Ağacı)
    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    # 1. Robot State Publisher (URDF -> TF Dönüşümleri)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False
        }]
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': False}]
    )

    # 2. Hokuyo LiDAR Düğümü (USB Bağlantısı)
    urg_node_serial = Node(
        package='urg_node',
        executable='urg_node_driver',
        name='urg_node_driver',
        output='screen',
        parameters=[{
            'serial_port': LaunchConfiguration('serial_port'),
            'serial_baud': 115200,
            'frame_id': 'lidar_link',
            'calibrate_time': True,
            'publish_intensity': False,
            'publish_multiecho': False,
            'angle_min': -2.35619449,  # -135 derece
            'angle_max': 2.35619449,   # +135 derece (Toplam 270 derece)
            'use_sim_time': False
        }],
        condition=UnlessCondition(PythonExpression(["'", LaunchConfiguration('lidar_connection'), "' == 'ethernet'"]))
    )

    # 3. Hokuyo LiDAR Düğümü (Ethernet Bağlantısı)
    urg_node_ethernet = Node(
        package='urg_node',
        executable='urg_node_driver',
        name='urg_node_driver',
        output='screen',
        parameters=[{
            'ip_address': LaunchConfiguration('ip_address'),
            'ip_port': 10940,
            'frame_id': 'lidar_link',
            'calibrate_time': True,
            'angle_min': -2.35619449,
            'angle_max': 2.35619449,
            'use_sim_time': False
        }],
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('lidar_connection'), "' == 'ethernet'"]))
    )

    # 4. RF2O Lazer Odometri (Tekerlek enkoderi olmadan doğrudan Hokuyo ile hassas odometri)
    laser_odometry = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic': '/scan',
            'odom_topic': '/odom',
            'publish_tf': True,
            'base_frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'freq': 10.0,
            'use_sim_time': False
        }],
        condition=IfCondition(LaunchConfiguration('use_rf2o'))
    )

    return LaunchDescription([
        lidar_connection_arg,
        lidar_serial_port_arg,
        lidar_ip_arg,
        use_rf2o_arg,
        robot_state_publisher,
        joint_state_publisher,
        urg_node_serial,
        urg_node_ethernet,
        laser_odometry
    ])
