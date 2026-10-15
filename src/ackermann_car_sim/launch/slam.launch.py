import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _cleanup_old_maps(context, *args, **kwargs):
    """
    Eski .posegraph / .data dosyalarını sil.
    slam_toolbox bunları bulursa eski haritaya devam etmeye çalışır.
    Bu fonksiyon launch sırasında otomatik temizlik yapar.
    """
    import glob
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    maps_dir = os.path.join(pkg_dir, '..', '..', '..', '..', 'maps')
    home_dir = os.path.expanduser('~')

    # Temizlenecek desenler
    patterns = [
        os.path.join(home_dir, '*.posegraph'),
        os.path.join(home_dir, '*.data'),
        '/tmp/*.posegraph',
        '/tmp/*.data',
    ]
    for pattern in patterns:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
                print(f'[slam.launch] 🧹 Eski posegraph/data silindi: {f}')
            except Exception:
                pass
    return []


def generate_launch_description():
    pkg_dir = get_package_share_directory('ackermann_car_sim')
    slam_config = os.path.join(pkg_dir, 'config', 'slam_toolbox_params.yaml')

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Gerçek robot için false, Gazebo simülasyonu için true'
    )

    # RViz varsayılan olarak KAPALI — Pi üzerinde gereksiz CPU yükü yaratır
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='RViz2 açılsin mi? Gerçek robot testlerinde false olsun.'
    )

    # ----------------------------------------------------------------
    # SLAM Toolbox — Headless (ekransız), boş haritadan başlar
    # ----------------------------------------------------------------
    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_config,
            {
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                # Kesinlikle eski harita yüklenmemesi için:
                'map_file_name':     '',   # Boş string = haritasız başla
                'map_start_at_dock': False,
            }
        ]
    )

    # ----------------------------------------------------------------
    # RViz2 — isteğe bağlı (use_rviz:=true ile açılır)
    # ----------------------------------------------------------------
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    return LaunchDescription([
        use_sim_time_arg,
        use_rviz_arg,
        # Eski posegraph dosyalarını temizle
        OpaqueFunction(function=_cleanup_old_maps),
        slam_node,
        rviz_node,
    ])
