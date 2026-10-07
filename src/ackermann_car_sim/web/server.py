#!/usr/bin/env python3
"""
Commercial Autonomous Mobile Robot (AMR) Web Fleet Control Server
FastAPI + WebSocket + ROS 2 Humble Bridge
"""

import os
import sys
import json
import math
import time
import asyncio
import threading
import subprocess
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from io import BytesIO

import numpy as np
import cv2
from PIL import Image

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
import tf2_ros

from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist, Quaternion
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from sensor_msgs.msg import LaserScan, Image as RosImage
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
WAYPOINTS_FILE = os.path.join(BASE_DIR, "waypoints.json")
MAP_YAML = os.path.abspath(os.path.join(BASE_DIR, "..", "maps", "arena_map.yaml"))
MAP_PGM = os.path.abspath(os.path.join(BASE_DIR, "..", "maps", "arena_map.pgm"))


def euler_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    """Extract 2D planar yaw from quaternion."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def quaternion_from_euler(roll: float, pitch: float, yaw: float) -> Quaternion:
    """Create Quaternion message from roll, pitch, yaw."""
    q = Quaternion()
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    q.w = cr * cp * cy + sr * sp * sy
    q.x = sr * cp * cy - cr * sp * sy
    q.y = cr * sp * cy + sr * cp * sy
    q.z = cr * cp * sy - sr * sp * cy
    return q


class ROSBridgeNode(Node):
    """ROS 2 Node handling communication with Nav2, Gazebo, sensors, and actuators."""

    def __init__(self):
        super().__init__("ackermann_web_bridge")
        self.set_parameters([rclpy.parameter.Parameter("use_sim_time", rclpy.Parameter.Type.BOOL, True)])
        self.get_logger().info("Initializing Nexus Autonomous Web Bridge Node...")

        # Robot Telemetry State
        self.robot_pose = {"x": 0.0, "y": 0.0, "yaw": 0.0, "cov": 0.005}
        self.velocity = {"linear_x": 0.0, "angular_z": 0.0, "speed": 0.0, "steer_deg": 0.0}
        self.battery = 98.4
        self.is_charging = False
        self.emergency_stop = False
        self.navigation_status = "STANDBY"  # STANDBY, NAVIGATING, SUCCEEDED, CANCELED, FAILED, MANUAL, ESTOP
        self.active_goal: Optional[Dict[str, Any]] = None
        self.goal_feedback: Optional[Dict[str, Any]] = None

        # Sensor Buffers
        self.lidar_points: List[List[float]] = []  # [[x, y], ...]
        self.global_path: List[List[float]] = []
        self.local_path: List[List[float]] = []
        self.latest_camera_jpeg: Optional[bytes] = None

        # Map metadata (YAML'dan okunacak, hard-coded değil — M-1 düzeltmesi)
        self.static_map_info = {"width": 0, "height": 0, "resolution": 0.05, "origin": {"x": -5.5, "y": -4.5}}
        self.static_map_image_bytes: Optional[bytes] = None
        self.slam_map_info = {"width": 0, "height": 0, "resolution": 0.05, "origin": {"x": 0.0, "y": 0.0}}
        self.slam_map_image_bytes: Optional[bytes] = None
        self.map_info = self.static_map_info
        self.map_image_bytes: Optional[bytes] = None
        self.latest_map_msg: Optional[OccupancyGrid] = None
        self.map_version: int = 1

        # Pre-load initial map from disk if exists
        self.load_disk_map()

        # TF2 Buffer and Listener for real-time 50Hz pose tracking
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # QoS Profiles
        amcl_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Subscriptions
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self.amcl_pose_cb, amcl_qos)
        self.create_subscription(Odometry, "/odom", self.odom_cb, 10)
        self.create_subscription(LaserScan, "/scan", self.scan_cb, sensor_qos)
        self.create_subscription(Path, "/plan", self.global_plan_cb, 5)
        self.create_subscription(Path, "/local_plan", self.local_plan_cb, 5)
        self.create_subscription(RosImage, "/camera/image", self.camera_cb, sensor_qos)
        self.create_subscription(OccupancyGrid, "/map", self.map_cb, map_qos)

        # 20 Hz Real-Time TF Pose Tracking
        self.create_timer(0.05, self.update_tf_pose)

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.goal_pose_pub = self.create_publisher(PoseStamped, "/goal_pose", 10)
        self.initial_pose_pub = self.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)

        # Action Client for NavigateToPose
        self.nav_to_pose_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.active_goal_handle = None

        # Battery simulation timer
        self.create_timer(1.0, self.simulate_battery)

        self.get_logger().info("Nexus Autonomous Web Bridge Node ready!")

    def load_disk_map(self):
        """Loads static map from arena_map.pgm and pre-renders high-contrast industrial CAD blueprint."""
        if os.path.exists(MAP_PGM):
            try:
                pgm_img = Image.open(MAP_PGM)
                arr = np.array(pgm_img)
                h, w = arr.shape
                self.map_info["width"] = w
                self.map_info["height"] = h
                self.map_info["resolution"] = 0.05
                self.map_info["origin"] = {"x": -5.5, "y": -4.5}

                if os.path.exists(MAP_YAML):
                    try:
                        import yaml
                        with open(MAP_YAML, "r") as yf:
                            ydata = yaml.safe_load(yf)
                            if ydata and "origin" in ydata:
                                self.map_info["origin"] = {"x": float(ydata["origin"][0]), "y": float(ydata["origin"][1])}
                            if ydata and "resolution" in ydata:
                                self.map_info["resolution"] = float(ydata["resolution"])
                    except Exception as ey:
                        self.get_logger().warn(f"Failed to read MAP_YAML: {ey}")

                # Authentic Commercial AMR Technical White CAD Blueprint Palette
                rgba = np.full((h, w, 4), 255, dtype=np.uint8) # 100% Pure White Background

                # Obstacle / Shelf / Wall mask
                obs_mask = (arr == 0).astype(np.uint8)
                kernel = np.ones((3, 3), np.uint8)
                dilated = cv2.dilate(obs_mask, kernel, iterations=1)

                # Generate 45-degree diagonal stripe hatch pattern for restricted rack zones
                y_idx, x_idx = np.indices((h, w))
                stripe_mask = ((x_idx + y_idx) % 7 < 2)

                # Fill obstacle interior with technical rack gray + pinkish forbidden zone stripes
                rgba[dilated > 0] = [170, 175, 185, 255] # Solid technical rack gray
                rgba[(dilated > 0) & stripe_mask] = [225, 29, 72, 255] # Pink/red forbidden zone stripes

                # Crisp dark charcoal outer boundary stroke
                eroded = cv2.erode(dilated, kernel, iterations=1)
                edge_mask = (dilated > 0) & (eroded == 0)
                rgba[edge_mask] = [24, 24, 27, 255] # Dark black/charcoal edge

                out_img = Image.fromarray(rgba)
                buf = BytesIO()
                out_img.save(buf, format="PNG")
                self.static_map_info = {
                    "width": w,
                    "height": h,
                    "resolution": self.map_info["resolution"],
                    "origin": self.map_info["origin"]
                }
                self.static_map_image_bytes = buf.getvalue()
                self.map_image_bytes = self.static_map_image_bytes
                self.get_logger().info(f"Loaded commercial white CAD map: {w}x{h}, res: {self.map_info['resolution']}, origin: {self.static_map_info['origin']}")

            except Exception as e:
                self.get_logger().error(f"Error loading disk map: {e}")

    def map_cb(self, msg: OccupancyGrid):
        """Processes dynamic map updates from /map."""
        try:
            self.latest_map_msg = msg
            w = msg.info.width
            h = msg.info.height
            res = msg.info.resolution
            ox = msg.info.origin.position.x
            oy = msg.info.origin.position.y
            self.map_info = {
                "width": w,
                "height": h,
                "resolution": res,
                "origin": {"x": ox, "y": oy}
            }

            data = np.array(msg.data, dtype=np.int8).reshape((h, w))
            # Flip vertically for standard image representation
            data = np.flipud(data)

            # High-Contrast Commercial AMR Map Palette:
            # - Unknown (-1): Soft blueprint background (#f1f5f9)
            # - Explored Free Space (0): Clean pure white (#ffffff)
            # - Obstacles / Walls (> 0): Charcoal boundary + Red/Pink hatched racks
            rgba = np.full((h, w, 4), [241, 245, 249, 255], dtype=np.uint8)
            rgba[data == 0] = [255, 255, 255, 255]

            obs_mask = (data > 0).astype(np.uint8)
            if np.any(obs_mask):
                kernel = np.ones((3, 3), np.uint8)
                dilated = cv2.dilate(obs_mask, kernel, iterations=1)

                y_idx, x_idx = np.indices((h, w))
                stripe_mask = ((x_idx + y_idx) % 7 < 2)

                rgba[dilated > 0] = [170, 175, 185, 255]
                rgba[(dilated > 0) & stripe_mask] = [225, 29, 72, 255]

                eroded = cv2.erode(dilated, kernel, iterations=1)
                edge_mask = (dilated > 0) & (eroded == 0)
                rgba[edge_mask] = [24, 24, 27, 255]

            out_img = Image.fromarray(rgba)
            buf = BytesIO()
            out_img.save(buf, format="PNG")
            self.slam_map_image_bytes = buf.getvalue()
            self.slam_map_info = {
                "width": w,
                "height": h,
                "resolution": res,
                "origin": {"x": ox, "y": oy}
            }
            self.map_version += 1
        except Exception as e:
            self.get_logger().error(f"Error updating dynamic SLAM map: {e}")

    def update_tf_pose(self):
        """Continuously resolves robot map pose from TF2 tree (map -> base_link)."""
        try:
            t = self.tf_buffer.lookup_transform("map", "base_link", Time())
            pos = t.transform.translation
            rot = t.transform.rotation
            yaw = euler_from_quaternion(rot.x, rot.y, rot.z, rot.w)
            self.robot_pose["x"] = round(pos.x, 3)
            self.robot_pose["y"] = round(pos.y, 3)
            self.robot_pose["yaw"] = round(yaw, 3)
        except Exception:
            pass

    def amcl_pose_cb(self, msg: PoseWithCovarianceStamped):
        """Updates robot global pose from AMCL."""
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        yaw = euler_from_quaternion(ori.x, ori.y, ori.z, ori.w)
        cov_x = msg.pose.covariance[0]
        cov_y = msg.pose.covariance[7]
        cov_val = math.sqrt(cov_x**2 + cov_y**2)
        self.robot_pose = {
            "x": round(pos.x, 3),
            "y": round(pos.y, 3),
            "yaw": round(yaw, 3),
            "cov": round(cov_val, 4)
        }

    def odom_cb(self, msg: Odometry):
        """Tracks linear speed and calculates Ackermann front wheel steering angle."""
        vx = msg.twist.twist.linear.x
        wz = msg.twist.twist.angular.z
        wheelbase = 0.20  # 20 cm
        steer_rad = 0.0
        if abs(vx) > 0.01:
            steer_rad = math.atan2(wheelbase * wz, vx)
        steer_deg = round(math.degrees(steer_rad), 1)

        self.velocity = {
            "linear_x": round(vx, 3),
            "angular_z": round(wz, 3),
            "speed": round(abs(vx), 2),
            "steer_deg": max(-45.0, min(45.0, steer_deg))
        }

    def scan_cb(self, msg: LaserScan):
        """Subsamples 2D LiDAR ranges and converts to 2D robot-relative points."""
        pts = []
        angle = msg.angle_min
        # Subsample every 4th beam for network bandwidth efficiency (approx 170 beams)
        step = 4
        ranges_len = len(msg.ranges)
        for i in range(0, ranges_len, step):
            r = msg.ranges[i]
            cur_angle = angle + i * msg.angle_increment
            if msg.range_min < r < msg.range_max:
                px = r * math.cos(cur_angle)
                py = r * math.sin(cur_angle)
                pts.append([round(px, 2), round(py, 2)])
        self.lidar_points = pts

    def global_plan_cb(self, msg: Path):
        """Receives global path from Nav2 planner."""
        self.global_path = [[round(p.pose.position.x, 2), round(p.pose.position.y, 2)] for p in msg.poses]

    def local_plan_cb(self, msg: Path):
        """Receives local path from Nav2 controller."""
        self.local_path = [[round(p.pose.position.x, 2), round(p.pose.position.y, 2)] for p in msg.poses]

    def camera_cb(self, msg: RosImage):
        """Encodes camera image to compressed JPEG."""
        try:
            # Parse rgb8 image
            if msg.encoding in ("rgb8", "bgr8"):
                np_arr = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, 3))
                if msg.encoding == "rgb8":
                    np_arr = cv2.cvtColor(np_arr, cv2.COLOR_RGB2BGR)
                # Resize to 320x240 for ultra-fast streaming
                small = cv2.resize(np_arr, (320, 240))
                _, jpeg = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                self.latest_camera_jpeg = jpeg.tobytes()
        except Exception as e:
            self.get_logger().error(f"Camera encode error: {e}")

    def simulate_battery(self):
        """Realistic battery simulation."""
        is_moving = self.velocity["speed"] > 0.05
        # Dock konumu: Robotun spawn noktasi — M-3 düzeltmesi (0,0 haritanin ortasi degil)
        dock_x, dock_y = -3.5, -2.5
        dist_to_dock = math.hypot(self.robot_pose["x"] - dock_x, self.robot_pose["y"] - dock_y)
        if dist_to_dock < 0.25 and not is_moving:
            self.is_charging = True
            self.battery = min(100.0, round(self.battery + 0.5, 1))
        else:
            self.is_charging = False
            drain = 0.05 if is_moving else 0.01
            self.battery = max(5.0, round(self.battery - drain, 1))

    def send_goal(self, x: float, y: float, yaw: float):
        """Dispatches autonomous navigation goal to Nav2 action server."""
        if self.emergency_stop:
            return {"status": "error", "message": "Emergency stop is active!"}

        # O-6 düzeltmesi: Nav2 hazır değilse goal gönderme
        if not self.nav_to_pose_client.server_is_ready():
            return {
                "status": "error",
                "message": "Nav2 henüz hazır değil. Lütfen birkaç saniye bekleyip tekrar deneyin."
            }

        # O-6 düzeltmesi: AMCL yeterince yakınsamamissa goal gönderme
        amcl_cov = self.robot_pose.get("cov", 999.0)
        if amcl_cov > 0.5:
            self.get_logger().warn(f"AMCL covaryans yüksek ({amcl_cov:.3f}) — lokalizasyon yeterince oturmadı. Goal gönderilmedi.")
            return {
                "status": "error",
                "message": f"Lokalizasyon yeterince oturmadı (kovaryans: {amcl_cov:.3f}). Robot 2D Pose Estimate ile konumlandırın."
            }

        self.navigation_status = "NAVIGATING"
        self.active_goal = {"x": x, "y": y, "yaw": yaw}

        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = "map"
        pose_msg.pose.position.x = float(x)
        pose_msg.pose.position.y = float(y)
        pose_msg.pose.position.z = 0.0
        pose_msg.pose.orientation = quaternion_from_euler(0.0, 0.0, float(yaw))

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose_msg
        send_goal_future = self.nav_to_pose_client.send_goal_async(
            goal_msg, feedback_callback=self.goal_feedback_cb
        )
        send_goal_future.add_done_callback(self.goal_response_cb)
        return {"status": "accepted", "goal": self.active_goal}

    def goal_feedback_cb(self, feedback_msg):
        fb = feedback_msg.feedback
        self.goal_feedback = {
            "distance_remaining": round(fb.distance_remaining, 2),
            "nav_time": fb.navigation_time.sec,
            "eta_sec": fb.estimated_time_remaining.sec,
            "recoveries": fb.number_of_recoveries
        }

    def goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.navigation_status = "FAILED"
            self.get_logger().error("Nav2 goal rejected!")
            return

        self.active_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.goal_result_cb)

    def goal_result_cb(self, future):
        result = future.result()
        if result.status == GoalStatus.STATUS_SUCCEEDED:
            self.navigation_status = "SUCCEEDED"
            self.get_logger().info("Navigation goal reached successfully!")
        elif result.status == GoalStatus.STATUS_CANCELED:
            self.navigation_status = "CANCELED"
        else:
            self.navigation_status = "FAILED"
        self.global_path = []
        self.local_path = []
        self.active_goal_handle = None

        def auto_reset():
            time.sleep(4.0)
            if self.navigation_status in ["SUCCEEDED", "CANCELED", "FAILED"]:
                self.navigation_status = "STANDBY"
                self.active_goal = None
                self.goal_feedback = None
        threading.Thread(target=auto_reset, daemon=True).start()

    def cancel_active_goal(self):
        """Cancels current Nav2 mission."""
        if self.active_goal_handle is not None:
            self.active_goal_handle.cancel_goal_async()
        self.navigation_status = "CANCELED"
        self.global_path = []
        self.local_path = []
        self.publish_cmd_vel(0.0, 0.0)

    def publish_cmd_vel(self, linear: float, angular: float):
        """Publishes teleoperation speed commands."""
        if self.emergency_stop:
            linear = 0.0
            angular = 0.0

        twist = Twist()
        twist.linear.x = float(linear)
        twist.angular.z = float(angular)
        self.cmd_vel_pub.publish(twist)

    def set_initial_pose(self, x: float, y: float, yaw: float):
        """Re-initializes AMCL 2D Pose Estimate."""
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation = quaternion_from_euler(0.0, 0.0, float(yaw))
        msg.pose.covariance[0] = 0.25
        msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.06
        self.initial_pose_pub.publish(msg)
        self.get_logger().info(f"Set 2D Initial Pose to: ({x}, {y}, yaw={yaw})")

    def toggle_estop(self) -> bool:
        """Toggles Emergency Stop state."""
        self.emergency_stop = not self.emergency_stop
        if self.emergency_stop:
            self.cancel_active_goal()
            self.publish_cmd_vel(0.0, 0.0)
            self.navigation_status = "ESTOP"
            self.get_logger().warn("🚨 EMERGENCY STOP ACTIVATED!")
        else:
            self.navigation_status = "IDLE"
            self.get_logger().info("Emergency Stop released.")
        return self.emergency_stop


# ==============================================================================
# FastAPI Web Server Application
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(telemetry_broadcast_task())
    yield
    task.cancel()


app = FastAPI(title="Nexus Autonomous AMR Fleet Controller", version="2.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ros_node: Optional[ROSBridgeNode] = None
connected_websockets: List[WebSocket] = []


class GoalRequest(BaseModel):
    x: float
    y: float
    yaw: float = 0.0
    frame_id: Optional[str] = "map"


class InitialPoseRequest(BaseModel):
    x: float
    y: float
    yaw: float = 0.0


class TeleopRequest(BaseModel):
    linear: float
    angular: float


class Waypoint(BaseModel):
    id: Optional[str] = None
    code: Optional[str] = None
    name: str
    x: float
    y: float
    yaw: float = 0.0
    icon: str = "location-dot"
    type: Optional[str] = "station"


# API Endpoints
@app.get("/api/status")
async def get_status():
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    return {
        "status": "online",
        "robot_pose": ros_node.robot_pose,
        "velocity": ros_node.velocity,
        "battery": ros_node.battery,
        "is_charging": ros_node.is_charging,
        "emergency_stop": ros_node.emergency_stop,
        "navigation_status": ros_node.navigation_status,
        "active_goal": ros_node.active_goal,
        "goal_feedback": ros_node.goal_feedback
    }


@app.get("/api/map/info")
async def get_map_info(mode: str = "static"):
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    if mode == "slam" and ros_node.slam_map_image_bytes:
        return ros_node.slam_map_info
    return ros_node.static_map_info


@app.api_route("/api/map/image", methods=["GET", "HEAD"])
async def get_map_image(mode: str = "static"):
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Node not initialized")
    if mode == "slam" and ros_node.slam_map_image_bytes:
        return Response(content=ros_node.slam_map_image_bytes, media_type="image/png")
    if ros_node.static_map_image_bytes:
        return Response(content=ros_node.static_map_image_bytes, media_type="image/png")
    raise HTTPException(status_code=404, detail="Map image not available")


@app.post("/api/map/save")
async def save_map_endpoint():
    """Saves current SLAM/dynamic map to disk as arena_map.pgm & arena_map.yaml."""
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Node not initialized")
    
    saved_successfully = False
    map_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "maps"))
    os.makedirs(map_dir, exist_ok=True)
    map_base = os.path.join(map_dir, "arena_map")
    
    # Try running map_saver_cli first
    try:
        cmd = ["ros2", "run", "nav2_map_server", "map_saver_cli", "-f", map_base, "--ros-args", "-p", "use_sim_time:=true"]
        res = subprocess.run(cmd, timeout=8, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(f"{map_base}.yaml"):
            saved_successfully = True
            ros_node.get_logger().info("Map saved via nav2_map_server map_saver_cli")
    except Exception as e:
        ros_node.get_logger().warn(f"map_saver_cli error or timeout: {e}")
        
    # If map_saver_cli failed or timed out, but we have latest_map_msg, save directly!
    if not saved_successfully and ros_node.latest_map_msg:
        try:
            msg = ros_node.latest_map_msg
            w = msg.info.width
            h = msg.info.height
            res = msg.info.resolution
            ox = msg.info.origin.position.x
            oy = msg.info.origin.position.y
            data = np.array(msg.data, dtype=np.int8).reshape((h, w))
            data = np.flipud(data)
            
            # Map values to PGM standard: 0 (occupied), 205 (unknown), 254 (free)
            pgm_data = np.full((h, w), 205, dtype=np.uint8)
            pgm_data[data == 0] = 254
            pgm_data[data > 0] = 0
            
            pgm_img = Image.fromarray(pgm_data)
            pgm_img.save(f"{map_base}.pgm")
            
            # Write YAML
            yaml_content = f"""image: arena_map.pgm
mode: trinary
resolution: {res}
origin: [{ox}, {oy}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""
            with open(f"{map_base}.yaml", "w") as yf:
                yf.write(yaml_content)
            saved_successfully = True
            ros_node.get_logger().info("Map saved directly via OccupancyGrid buffer")
        except Exception as ex:
            ros_node.get_logger().error(f"Direct map save error: {ex}")
            
    if saved_successfully:
        # Reload disk map into memory immediately
        ros_node.load_disk_map()
        return {
            "status": "success",
            "message": "Harita başarıyla kaydedildi ve sisteme yüklendi!",
            "map_info": ros_node.map_info
        }
    else:
        # If no dynamic map message yet, fallback to saving existing arena_map if present
        if os.path.exists(f"{map_base}.yaml"):
            ros_node.load_disk_map()
            return {
                "status": "success",
                "message": "Mevcut harita yeniden yüklendi ve sisteme uygulandı!",
                "map_info": ros_node.map_info
            }
        raise HTTPException(status_code=500, detail="Harita kaydedilemedi. SLAM harita akışı henüz başlamamış olabilir.")


@app.get("/api/diagnostics")
async def get_diagnostics():
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    return {
        "status": "HEALTHY" if not ros_node.emergency_stop else "ESTOP_ENGAGED",
        "amcl_covariance": ros_node.robot_pose.get("cov", 0.0),
        "amcl_status": "LOCKED" if ros_node.robot_pose.get("cov", 1.0) < 0.05 else "CONVERGING",
        "odometry": ros_node.velocity,
        "laser_points_count": len(ros_node.lidar_points),
        "global_plan_length": len(ros_node.global_path),
        "local_plan_length": len(ros_node.local_path),
        "emergency_stop": ros_node.emergency_stop,
        "battery_pct": ros_node.battery,
        "timestamp": time.time()
    }


@app.get("/api/camera/stream")
async def camera_stream():
    """Streams live MJPEG video from robot Intel RealSense camera."""
    async def frame_generator():
        # Fallback test pattern if no camera
        blank_frame = None
        while True:
            if ros_node and ros_node.latest_camera_jpeg:
                frame_bytes = ros_node.latest_camera_jpeg
            else:
                if blank_frame is None:
                    dummy = np.zeros((240, 320, 3), dtype=np.uint8)
                    cv2.putText(dummy, "REALSENSE STANDBY", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)
                    _, enc = cv2.imencode(".jpg", dummy)
                    blank_frame = enc.tobytes()
                frame_bytes = blank_frame

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            await asyncio.sleep(0.066)  # ~15 FPS

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/api/goal")
@app.post("/api/navigation/goal")
async def send_navigation_goal(req: GoalRequest):
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    res = ros_node.send_goal(req.x, req.y, req.yaw)
    return res


@app.post("/api/goal/cancel")
@app.post("/api/navigation/cancel")
async def cancel_goal():
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    ros_node.cancel_active_goal()
    return {"status": "canceled"}


@app.post("/api/initialpose")
async def set_initial_pose(req: InitialPoseRequest):
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    ros_node.set_initial_pose(req.x, req.y, req.yaw)
    return {"status": "initial_pose_published"}


@app.post("/api/teleop")
@app.post("/api/teleop/cmd_vel")
async def teleop_control(req: TeleopRequest):
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    ros_node.publish_cmd_vel(req.linear, req.angular)
    return {"status": "ok"}


@app.post("/api/estop")
@app.post("/api/estop/toggle")
async def toggle_estop():
    if not ros_node:
        raise HTTPException(status_code=503, detail="ROS Bridge not started")
    state = ros_node.toggle_estop()
    return {"emergency_stop": state}


@app.get("/api/waypoints")
async def get_waypoints():
    if os.path.exists(WAYPOINTS_FILE):
        try:
            with open(WAYPOINTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


@app.post("/api/waypoints")
async def save_waypoint(wp: Waypoint):
    if not wp.id:
        wp.id = f"wp_{int(time.time()*1000)}"
    wps = []
    if os.path.exists(WAYPOINTS_FILE):
        try:
            with open(WAYPOINTS_FILE, "r", encoding="utf-8") as f:
                wps = json.load(f)
        except Exception:
            wps = []

    # Update or append
    updated = False
    for i, item in enumerate(wps):
        if item["id"] == wp.id:
            wps[i] = wp.dict()
            updated = True
            break
    if not updated:
        wps.append(wp.dict())

    with open(WAYPOINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(wps, f, indent=2, ensure_ascii=False)
    return {"status": "saved", "waypoints": wps}


@app.delete("/api/waypoints/{wp_id}")
async def delete_waypoint(wp_id: str):
    if not os.path.exists(WAYPOINTS_FILE):
        return {"status": "deleted"}
    try:
        with open(WAYPOINTS_FILE, "r", encoding="utf-8") as f:
            wps = json.load(f)
        wps = [w for w in wps if w["id"] != wp_id]
        with open(WAYPOINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(wps, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return {"status": "deleted"}


@app.websocket("/ws")
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """High-frequency real-time bidirectional telemetry socket."""
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                msg_type = msg.get("type")
                if msg_type == "cmd_vel" and ros_node:
                    ros_node.publish_cmd_vel(msg.get("linear", 0.0), msg.get("angular", 0.0))
                elif msg_type == "estop" and ros_node:
                    ros_node.toggle_estop()
                elif msg_type == "goal" and ros_node:
                    ros_node.send_goal(msg.get("x", 0.0), msg.get("y", 0.0), msg.get("yaw", 0.0))
                elif msg_type == "cancel" and ros_node:
                    ros_node.cancel_active_goal()
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


async def telemetry_broadcast_task():
    """Broadcasts 20 Hz telemetry frames to all connected web clients."""
    while True:
        if ros_node and connected_websockets:
            payload = {
                "type": "telemetry",
                "robot_pose": ros_node.robot_pose,
                "pose": ros_node.robot_pose,
                "velocity": ros_node.velocity,
                "battery": ros_node.battery,
                "is_charging": ros_node.is_charging,
                "emergency_stop": ros_node.emergency_stop,
                "estop": ros_node.emergency_stop,
                "navigation_status": ros_node.navigation_status,
                "nav_status": ros_node.navigation_status,
                "active_goal": ros_node.active_goal,
                "goal_feedback": ros_node.goal_feedback,
                "lidar_points": ros_node.lidar_points,
                "lidar": ros_node.lidar_points,
                "global_path": ros_node.global_path,
                "global_plan": ros_node.global_path,
                "local_path": ros_node.local_path,
                "local_plan": ros_node.local_path,
                "map_version": ros_node.map_version,
                "map_info": ros_node.map_info,
                "timestamp": time.time()
            }
            msg_str = json.dumps(payload)
            # Broadcast to all connected clients
            dead_sockets = []
            for ws in connected_websockets:
                try:
                    await ws.send_text(msg_str)
                except Exception:
                    dead_sockets.append(ws)
            for ds in dead_sockets:
                if ds in connected_websockets:
                    connected_websockets.remove(ds)

        await asyncio.sleep(0.05)  # 20 Hz






@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Serve static frontend files
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def start_ros_executor(node: Node):
    """Spins ROS 2 executor in background daemon thread."""
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except Exception:
        pass
    finally:
        node.destroy_node()


def main():
    global ros_node
    print("==================================================================")
    print("🚀 NEXUS AUTONOMOUS | Fleet Control Web Server")
    print("Enterprise Edition (ROS 2 Humble & Nav2 Integration)")
    print("==================================================================")

    rclpy.init(args=None)
    ros_node = ROSBridgeNode()

    # Start ROS thread
    ros_thread = threading.Thread(target=start_ros_executor, args=(ros_node,), daemon=True)
    ros_thread.start()

    port = 8080
    host = "0.0.0.0"
    print(f"📡 Web Dashboard Active: http://localhost:{port}")
    print(f"🌐 Local Network Access: http://<YOUR_IP>:{port}")
    print("==================================================================")

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        print("\nStopping Web Server...")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
