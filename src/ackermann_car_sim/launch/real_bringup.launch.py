import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, Command, EqualsSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# urg_node ROS 2'de scan frame_id olarak varsayılan 'laser' kullanır.
# RF2O scan mesajının header.frame_id'sine bakarak TF arar.
# Bu nedenle 'lidar_link' yerine 'laser' frame'i tanımlanmalı.
LIDARFRAME = 'laser'

def generate_launch_description():
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'ackermann_car.urdf.xacro')

    # Argümanlar
    lidar_connection_arg = DeclareLaunchArgument(
        'lidar_connection',
        default_value='serial',
        description='LiDAR baglanti tipi: "serial" (USB) veya "ethernet"'
    )

    # Hokuyo LiDAR için otomatik port tespiti (/dev/serial/by-id)
    default_lidar_port = '/dev/ttyACM0'
    by_id_dir = '/dev/serial/by-id'
    if os.path.exists(by_id_dir):
        for entry in os.listdir(by_id_dir):
            if any(k in entry.lower() for k in ['hokuyo', 'urg', 'laser']):
                default_lidar_port = os.path.realpath(os.path.join(by_id_dir, entry))
                break

    lidar_serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value=default_lidar_port,
        description='Hokuyo LiDAR USB seri port yolu (/dev/ttyACM0, /dev/ttyACM1 vb.)'
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

    # ── 'laser' frame'i için static TF (base_link → laser) ──────────────────
    # urg_node varsayılan olarak 'laser' frame_id ile scan yayınlar.
    # RF2O scan.header.frame_id'yi okuyarak TF arar: base_footprint → laser.
    # URDF'deki lidar_link pozisyonuyla aynı (x=0.12 m, z=0.12 m).
    laser_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_laser_tf',
        output='screen',
        arguments=['0.0', '0.0', '0.12',    # x=0.0 (şasi tam merkezi), y=0.0, z=0.12 m
                   '0.0',  '0.0', '0.0',    # roll pitch yaw
                   'base_link', 'laser']    # parent → child
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
            'frame_id': 'laser',        # urg_node varsayılanı 'laser' — RF2O ile uyumlu
            'calibrate_time': True,
            'publish_intensity': False,
            'publish_multiecho': False,
            'angle_min': -2.35619449,   # -135 derece
            'angle_max': 2.35619449,    # +135 derece (Toplam 270 derece)
            'use_sim_time': False
        }],
        condition=UnlessCondition(EqualsSubstitution(LaunchConfiguration('lidar_connection'), 'ethernet'))
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
            'frame_id': 'laser',        # RF2O ile uyumlu
            'calibrate_time': True,
            'angle_min': -2.35619449,
            'angle_max': 2.35619449,
            'use_sim_time': False
        }],
        condition=IfCondition(EqualsSubstitution(LaunchConfiguration('lidar_connection'), 'ethernet'))
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
        laser_static_tf,    # base_link → laser static TF (RF2O için zorunlu)
        urg_node_serial,
        urg_node_ethernet,
        laser_odometry
    ])
