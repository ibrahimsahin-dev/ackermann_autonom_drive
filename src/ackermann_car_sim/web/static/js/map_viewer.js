/**
 * ==============================================================================
 * LOGIX AMR - INDUSTRIAL 2D CAD MAP & SENSOR RENDER ENGINE
 * High-Precision 60 FPS HTML5 Canvas Engine for Autonomous Vehicle Fleet Control
 * ==============================================================================
 */

class MapViewer {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    
    // Viewport transform state
    this.zoom = 2.5;
    this.panX = 0;
    this.panY = 0;
    this.isDraggingPan = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    
    // Tool Modes: 'pan' (default), 'set_goal', 'measure'
    this.mode = 'pan';
    this.isSettingGoal = false;
    this.goalStartWorld = null;
    this.goalCurrentAngle = 0;
    
    // Measurement Tool State
    this.measureStart = null;
    this.measureCurrent = null;
    
    // Map Metadata
    this.mapInfo = {
      width: 197,
      height: 157,
      resolution: 0.05,
      origin: { x: -1.42, y: -1.42 }
    };
    this.mapImage = null;
    this.mapImageLoaded = false;
    
    // Dynamic Telemetry & Sensor Buffers
    this.robotPose = { x: 0.0, y: 0.0, yaw: 0.0 };
    this.steerDeg = 0.0;
    this.lidarPoints = []; // [[x, y], ...] robot relative
    this.globalPath = [];  // [[x, y], ...]
    this.localPath = [];   // [[x, y], ...]
    this.waypoints = [];
    this.activeGoal = null;
    this.hoveredWaypoint = null;
    
    // Layer Toggles
    this.layers = {
      lidar: true,
      lidarFov: true,
      globalPath: true,
      localPath: true,
      waypoints: true,
      grid: true,
      safetyFootprint: true,
      forbiddenZones: true
    };
    
    // Callbacks
    this.onGoalSelected = options.onGoalSelected || null;
    this.onInitialPoseSelected = options.onInitialPoseSelected || null;
    this.onWaypointAddRequested = options.onWaypointAddRequested || null;
    this.onWaypointClicked = options.onWaypointClicked || null;
    this.onToolModeChanged = options.onToolModeChanged || null;
    
    this.initCanvasSize();
    this.bindEvents();
    this.loadMapImage();
    this.startRenderLoop();
  }

  initCanvasSize() {
    const rect = this.canvas.getBoundingClientRect();
    const w = Math.floor(rect.width || (window.innerWidth - 48));
    const h = Math.floor(rect.height || (window.innerHeight - 42));
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.floor(w * dpr);
    this.canvas.height = Math.floor(h * dpr);
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.scale(dpr, dpr);
    this.displayWidth = w;
    this.displayHeight = h;

    // Center viewport initially
    if (!this.panX && !this.panY) {
      const drawerW = w > 700 ? 290 : 0;
      this.panX = drawerW + (w - drawerW) / 2;
      this.panY = h / 2;
    }
  }

  loadMapImage() {
    fetch('/api/map/info')
      .then(res => res.json())
      .then(info => {
        if (info && info.width > 0) {
          this.mapInfo.width = info.width;
          this.mapInfo.height = info.height;
          this.mapInfo.resolution = info.resolution || 0.05;
          if (info.origin) {
            this.mapInfo.origin.x = info.origin.x !== undefined ? info.origin.x : -1.42;
            this.mapInfo.origin.y = info.origin.y !== undefined ? info.origin.y : -1.42;
          }
        }
        this.fitArena();
      })
      .catch(() => {});

    this.mapImage = new Image();
    this.mapImage.src = '/api/map/image?t=' + Date.now();
    this.mapImage.onload = () => {
      this.mapImageLoaded = true;
      if (this.mapImage.naturalWidth) this.mapInfo.width = this.mapImage.naturalWidth;
      if (this.mapImage.naturalHeight) this.mapInfo.height = this.mapImage.naturalHeight;
      this.fitArena();
    };
    this.mapImage.onerror = () => {
      setTimeout(() => this.loadMapImage(), 2000);
    };
  }

  reloadMapImage() {
    this.loadMapImage();
  }

  updateDynamicMap(newInfo) {
    if (this.isUpdatingMap) return;
    this.isUpdatingMap = true;

    const img = new Image();
    img.src = '/api/map/image?t=' + Date.now();
    img.onload = () => {
      this.mapImage = img;
      this.mapImageLoaded = true;
      if (newInfo) {
        if (newInfo.width) this.mapInfo.width = newInfo.width;
        if (newInfo.height) this.mapInfo.height = newInfo.height;
        if (newInfo.resolution) this.mapInfo.resolution = newInfo.resolution;
        if (newInfo.origin) {
          this.mapInfo.origin.x = newInfo.origin.x !== undefined ? newInfo.origin.x : this.mapInfo.origin.x;
          this.mapInfo.origin.y = newInfo.origin.y !== undefined ? newInfo.origin.y : this.mapInfo.origin.y;
        }
      }
      this.isUpdatingMap = false;
    };
    img.onerror = () => {
      this.isUpdatingMap = false;
    };
  }

  fitArena() {
    const mapPixelW = (this.mapImage && this.mapImage.naturalWidth) || this.mapInfo.width || 197;
    const mapPixelH = (this.mapImage && this.mapImage.naturalHeight) || this.mapInfo.height || 157;
    
    // Check if dispatch drawer is currently expanded
    const drawerEl = document.getElementById('dispatch-drawer');
    const isDrawerOpen = drawerEl && !drawerEl.classList.contains('collapsed');
    const drawerW = (isDrawerOpen && this.displayWidth > 700) ? 290 : 0;
    const availW = Math.max(200, this.displayWidth - drawerW);
    const availH = Math.max(200, this.displayHeight);

    const scaleX = (availW * 0.78) / mapPixelW;
    const scaleY = (availH * 0.78) / mapPixelH;
    this.zoom = Math.max(0.2, Math.min(25.0, Math.min(scaleX, scaleY)));
    
    this.panX = drawerW + availW / 2;
    this.panY = availH / 2;
  }

  recenterRobot() {
    const drawerEl = document.getElementById('dispatch-drawer');
    const isDrawerOpen = drawerEl && !drawerEl.classList.contains('collapsed');
    const drawerW = (isDrawerOpen && this.displayWidth > 700) ? 290 : 0;
    const targetX = drawerW + (this.displayWidth - drawerW) / 2;
    const targetY = this.displayHeight / 2;

    const cur = this.worldToScreen(this.robotPose.x, this.robotPose.y);
    this.panX += (targetX - cur.x);
    this.panY += (targetY - cur.y);
  }

  // Smooth Zoom Centered on Given Point (or Screen Center)
  zoomBy(factor, centerX = null, centerY = null) {
    const cx = centerX !== null ? centerX : (this.displayWidth / 2);
    const cy = centerY !== null ? centerY : (this.displayHeight / 2);
    const newZoom = Math.max(0.1, Math.min(50.0, this.zoom * factor));
    this.panX = cx - (cx - this.panX) * (newZoom / this.zoom);
    this.panY = cy - (cy - this.panY) * (newZoom / this.zoom);
    this.zoom = newZoom;
  }

  zoomIn() {
    this.zoomBy(1.25);
  }

  zoomOut() {
    this.zoomBy(0.80);
  }

  // ============================================================================
  // COORDINATE TRANSFORMATIONS (World <-> Screen)
  // ============================================================================
  worldToScreen(wx, wy) {
    const ox = this.mapInfo.origin.x;
    const oy = this.mapInfo.origin.y;
    const res = this.mapInfo.resolution;
    const h = this.mapInfo.height;
    const w = this.mapInfo.width;
    
    const u = (wx - ox) / res;
    const v = h - 1 - (wy - oy) / res;
    
    const sx = this.panX + (u - w / 2) * this.zoom;
    const sy = this.panY + (v - h / 2) * this.zoom;
    return { x: sx, y: sy };
  }

  screenToWorld(sx, sy) {
    const ox = this.mapInfo.origin.x;
    const oy = this.mapInfo.origin.y;
    const res = this.mapInfo.resolution;
    const h = this.mapInfo.height;
    const w = this.mapInfo.width;
    
    const u = (sx - this.panX) / this.zoom + w / 2;
    const v = (sy - this.panY) / this.zoom + h / 2;
    
    const wx = ox + u * res;
    const wy = oy + (h - 1 - v) * res;
    return { x: wx, y: wy };
  }

  // ============================================================================
  // USER INTERACTION & INPUT HANDLING (Pan, Zoom, Target)
  // ============================================================================
  bindEvents() {
    window.addEventListener('resize', () => {
      this.initCanvasSize();
    });

    // Right-click cancels goal placement tool
    this.canvas.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      if (this.mode !== 'pan') {
        this.setToolMode('pan');
        if (this.onToolModeChanged) this.onToolModeChanged('pan');
      }
    });

    // Double click zooms in centered on cursor
    this.canvas.addEventListener('dblclick', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      this.zoomBy(1.4, mx, my);
    });

    // Mouse Controls
    this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    window.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    window.addEventListener('mouseup', (e) => this.handleMouseUp(e));
    this.canvas.addEventListener('wheel', (e) => this.handleWheel(e), { passive: false });

    // Touch Controls (Pinch to zoom + Pan)
    this.touchState = { dist: 0, lastX: 0, lastY: 0 };
    this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
    this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
    this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e));

    // Keyboard ESC cancels goal selection
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.mode !== 'pan') {
        this.setToolMode('pan');
        if (this.onToolModeChanged) this.onToolModeChanged('pan');
      }
    });
  }

  handleMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;

    // 1. Check if clicking inside bottom-left Mini-Map HUD
    const mmW = 145;
    const mmH = 115;
    const mmX = 60;
    const mmY = this.displayHeight - mmH - 16;
    if (sx >= mmX && sx <= mmX + mmW && sy >= mmY && sy <= mmY + mmH) {
      const normX = (sx - mmX) / mmW;
      const normY = (sy - mmY) / mmH;
      const worldTargetX = this.mapInfo.origin.x + normX * (this.mapInfo.width * this.mapInfo.resolution);
      const worldTargetY = this.mapInfo.origin.y + (1 - normY) * (this.mapInfo.height * this.mapInfo.resolution);
      const cur = this.worldToScreen(worldTargetX, worldTargetY);
      this.panX += (this.displayWidth / 2 - cur.x);
      this.panY += (this.displayHeight / 2 - cur.y);
      return;
    }

    // 2. Check if clicking on registered waypoint
    for (const wp of this.waypoints) {
      const wpScreen = this.worldToScreen(wp.x, wp.y);
      const dist = Math.hypot(sx - wpScreen.x, sy - wpScreen.y);
      if (dist <= 20) {
        if (this.onWaypointClicked) this.onWaypointClicked(wp);
        return;
      }
    }

    const world = this.screenToWorld(sx, sy);

    // 3. Goal Selection Mode (Active only when user explicitly chose goal tool)
    if (this.mode === 'set_goal' || this.mode === 'navigate') {
      if (e.button === 0) {
        this.isSettingGoal = true;
        this.goalStartWorld = world;
        this.goalCurrentAngle = 0;
        return;
      }
    }

    // 4. Measure Tool Mode
    if (this.mode === 'measure') {
      if (!this.measureStart) {
        this.measureStart = world;
        this.measureCurrent = world;
      } else {
        this.measureCurrent = world;
      }
      return;
    }

    // 5. DEFAULT BEHAVIOR: Left Click (0) or Middle Click (1) -> Smooth Pan!
    if (e.button === 0 || e.button === 1) {
      this.isDraggingPan = true;
      this.dragStartX = e.clientX - this.panX;
      this.dragStartY = e.clientY - this.panY;
      this.canvas.style.cursor = 'grabbing';
    }
  }

  handleMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;

    if (this.isDraggingPan) {
      this.panX = e.clientX - this.dragStartX;
      this.panY = e.clientY - this.dragStartY;
      return;
    }

    if (this.isSettingGoal && this.goalStartWorld) {
      const currentWorld = this.screenToWorld(sx, sy);
      const dx = currentWorld.x - this.goalStartWorld.x;
      const dy = currentWorld.y - this.goalStartWorld.y;
      if (Math.hypot(dx, dy) > 0.05) {
        this.goalCurrentAngle = Math.atan2(dy, dx);
      }
      return;
    }

    if (this.mode === 'measure' && this.measureStart) {
      this.measureCurrent = this.screenToWorld(sx, sy);
      return;
    }

    // Waypoint hover check
    let foundWp = null;
    for (const wp of this.waypoints) {
      const wpScreen = this.worldToScreen(wp.x, wp.y);
      const dist = Math.hypot(sx - wpScreen.x, sy - wpScreen.y);
      if (dist <= 20) {
        foundWp = wp;
        break;
      }
    }
    this.hoveredWaypoint = foundWp;
    if (foundWp) {
      this.canvas.style.cursor = 'pointer';
    } else if (this.mode === 'set_goal' || this.mode === 'navigate') {
      this.canvas.style.cursor = 'crosshair';
    } else {
      this.canvas.style.cursor = 'grab';
    }
  }

  handleMouseUp(e) {
    if (this.isDraggingPan) {
      this.isDraggingPan = false;
      this.canvas.style.cursor = (this.mode === 'set_goal' || this.mode === 'navigate') ? 'crosshair' : 'grab';
    }

    if (this.isSettingGoal && this.goalStartWorld) {
      const gx = this.goalStartWorld.x;
      const gy = this.goalStartWorld.y;
      const yaw = this.goalCurrentAngle;

      this.isSettingGoal = false;
      this.goalStartWorld = null;

      if (this.onGoalSelected) {
        this.onGoalSelected(gx, gy, yaw);
      }

      // Revert automatically to pan mode so user can pan/zoom immediately!
      this.setToolMode('pan');
      if (this.onToolModeChanged) this.onToolModeChanged('pan');
    }
  }

  handleWheel(e) {
    e.preventDefault();
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Smooth exponential zoom factor for mouse wheel or touchpad
    const delta = e.deltaY;
    const zoomFactor = delta < 0 ? 1.15 : 0.87;
    this.zoomBy(zoomFactor, mx, my);
  }

  handleTouchStart(e) {
    if (e.touches.length === 1) {
      const t = e.touches[0];
      this.handleMouseDown({ button: 0, clientX: t.clientX, clientY: t.clientY });
    } else if (e.touches.length === 2) {
      this.isDraggingPan = false;
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      this.touchState.dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      this.touchState.lastX = (t1.clientX + t2.clientX) / 2;
      this.touchState.lastY = (t1.clientY + t2.clientY) / 2;
    }
  }

  handleTouchMove(e) {
    if (e.touches.length === 1) {
      const t = e.touches[0];
      this.handleMouseMove({ clientX: t.clientX, clientY: t.clientY });
    } else if (e.touches.length === 2) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const newDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      if (this.touchState.dist > 0 && newDist > 0) {
        const factor = newDist / this.touchState.dist;
        const rect = this.canvas.getBoundingClientRect();
        const midX = (t1.clientX + t2.clientX) / 2 - rect.left;
        const midY = (t1.clientY + t2.clientY) / 2 - rect.top;
        this.zoomBy(factor, midX, midY);
        this.touchState.dist = newDist;
      }
    }
  }

  handleTouchEnd(e) {
    if (e.touches.length === 0) {
      this.handleMouseUp({ button: 0 });
      this.touchState.dist = 0;
    }
  }

  setToolMode(mode) {
    this.mode = mode;
    if (mode !== 'measure') {
      this.measureStart = null;
      this.measureCurrent = null;
    }
    this.canvas.style.cursor = (mode === 'set_goal' || mode === 'navigate') ? 'crosshair' : 'grab';
  }

  // ============================================================================
  // MAIN RENDER LOOP (60 FPS)
  // ============================================================================
  startRenderLoop() {
    const loop = () => {
      try {
        this.render();
      } catch (err) {
        console.error("Map render loop error:", err);
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  render() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.displayWidth, this.displayHeight);

    // 1. Clean White Engineering CAD Canvas (#ffffff)
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    // 2. Subtle Metric CAD Grid (Light gray)
    if (this.layers.grid) {
      this.drawMetricGrid(ctx);
    }

    // 3. Static CAD Map Image (Raw SLAM Obstacles & Hatched Racks)
    if (this.mapImageLoaded && this.mapImage) {
      const wPx = this.mapInfo.width * this.zoom;
      const hPx = this.mapInfo.height * this.zoom;

      ctx.save();
      ctx.imageSmoothingEnabled = false; // Sharp CAD pixels, no blur
      ctx.drawImage(
        this.mapImage,
        this.panX - (this.mapInfo.width / 2) * this.zoom,
        this.panY - (this.mapInfo.height / 2) * this.zoom,
        wPx,
        hPx
      );
      
      // Clean 1px CAD boundary border
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 1;
      ctx.strokeRect(
        this.panX - (this.mapInfo.width / 2) * this.zoom,
        this.panY - (this.mapInfo.height / 2) * this.zoom,
        wPx,
        hPx
      );
      ctx.restore();
    }

    // 4. Forbidden Zone / No-Go Markers (⊘) and Station Badges inside Racks
    this.drawForbiddenZoneMarkers(ctx);

    // 5. Global Planned Route
    if (this.layers.globalPath && this.globalPath.length > 1) {
      this.drawGlobalPath(ctx);
    }

    // 6. Local Trajectory Arc
    if (this.layers.localPath && this.localPath.length > 1) {
      this.drawLocalPath(ctx);
    }

    // 7. Laser Scanner Active Safety Field (Purple/Violet Zigzag Cone)
    if (this.layers.lidarFov) {
      this.drawLidarSafetyField(ctx);
    }

    // 8. 2D LiDAR Scan Points (Vivid Emerald-Teal Laser Returns #00e5c8)
    if (this.layers.lidar && this.lidarPoints.length > 0) {
      this.drawLidarPoints(ctx);
    }

    // 9. Station / Waypoint Markers
    if (this.layers.waypoints && this.waypoints.length > 0) {
      this.drawWaypoints(ctx);
    }

    // 10. Active Navigation Goal Marker
    if (this.activeGoal) {
      this.drawActiveGoalPin(ctx);
    }

    // 11. Goal Placement Drag Preview
    if (this.isSettingGoal && this.goalStartWorld) {
      this.drawGoalPlacementPreview(ctx);
    }

    // 12. Measurement Dimension Line
    if (this.mode === 'measure' && this.measureStart && this.measureCurrent) {
      this.drawMeasurementLine(ctx);
    }

    // 13. Commercial Industrial AGV Vehicle Model
    this.drawRobotModel(ctx);

    // 14. Bottom-Left Mini-Map Overview HUD (Picture-in-Picture)
    this.drawMiniMap(ctx);
  }

  // ============================================================================
  // DRAWING LAYERS (Commercial White CAD Standards)
  // ============================================================================

  drawMetricGrid(ctx) {
    ctx.save();
    const step = 1.0; // 1 meter grid
    const minCoord = -10;
    const maxCoord = 15;

    ctx.font = '10px "JetBrains Mono", monospace';

    // Vertical Lines
    for (let wx = minCoord; wx <= maxCoord; wx += step) {
      const p1 = this.worldToScreen(wx, minCoord);
      const p2 = this.worldToScreen(wx, maxCoord);

      const isMajor = Math.abs(wx) % 5 === 0;
      ctx.strokeStyle = isMajor ? 'rgba(0, 0, 0, 0.08)' : 'rgba(0, 0, 0, 0.03)';
      ctx.lineWidth = isMajor ? 1.0 : 0.6;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();

      if (Math.abs(wx) % 2 === 0) {
        ctx.fillStyle = 'rgba(100, 116, 139, 0.5)';
        ctx.fillText(`${wx > 0 ? '+' : ''}${wx}m`, p1.x + 3, this.displayHeight - 8);
      }
    }

    // Horizontal Lines
    for (let wy = minCoord; wy <= maxCoord; wy += step) {
      const p1 = this.worldToScreen(minCoord, wy);
      const p2 = this.worldToScreen(maxCoord, wy);

      const isMajor = Math.abs(wy) % 5 === 0;
      ctx.strokeStyle = isMajor ? 'rgba(0, 0, 0, 0.08)' : 'rgba(0, 0, 0, 0.03)';
      ctx.lineWidth = isMajor ? 1.0 : 0.6;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();

      if (Math.abs(wy) % 2 === 0) {
        ctx.fillStyle = 'rgba(100, 116, 139, 0.5)';
        ctx.fillText(`${wy > 0 ? '+' : ''}${wy}m`, 56, p1.y - 3);
      }
    }

    // CAD World Origin Crosshair (0,0)
    const oScreen = this.worldToScreen(0, 0);
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(oScreen.x, oScreen.y);
    ctx.lineTo(oScreen.x + 20, oScreen.y);
    ctx.stroke();

    ctx.strokeStyle = '#10b981';
    ctx.beginPath();
    ctx.moveTo(oScreen.x, oScreen.y);
    ctx.lineTo(oScreen.x, oScreen.y - 20);
    ctx.stroke();

    ctx.fillStyle = '#64748b';
    ctx.fillText('(0,0)', oScreen.x + 4, oScreen.y + 12);
    ctx.restore();
  }

  // Draw ⊘ (Forbidden Zone / No-Entry) symbols inside storage racks matching reference screenshot
  drawForbiddenZoneMarkers(ctx) {
    ctx.save();
    const rackNodes = [
      { x: -0.5, y: 3.5, label: '⊘' },
      { x: 1.5, y: 3.5, label: '⊘' },
      { x: 3.5, y: 3.5, label: '⊘' },
      { x: -0.5, y: 2.2, label: '⊘' },
      { x: 2.5, y: 2.2, label: '③ ⊘' },
      { x: -0.5, y: 0.8, label: '⊘' },
      { x: 2.0, y: 0.8, label: '⊘' },
      { x: -0.5, y: -0.8, label: '⊘' },
      { x: 2.0, y: -0.8, label: '⊘' },
      { x: -0.5, y: -2.2, label: '⊘' },
      { x: 2.0, y: -2.2, label: '⊘' },
      { x: -0.5, y: -3.5, label: '⊘' },
      { x: 2.0, y: -3.5, label: '⊘' }
    ];

    ctx.font = '700 11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (const node of rackNodes) {
      const s = this.worldToScreen(node.x, node.y);
      if (s.x < 0 || s.x > this.displayWidth || s.y < 0 || s.y > this.displayHeight) continue;

      // Clean white disc with black border
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#18181b';
      ctx.lineWidth = 1.0;
      ctx.beginPath();
      ctx.arc(s.x, s.y, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#18181b';
      ctx.fillText(node.label, s.x, s.y);
    }
    ctx.restore();
  }

  // Purple/Violet Zigzag Sensor FOV Cone matching commercial reference screenshot
  drawLidarSafetyField(ctx) {
    ctx.save();
    const rx = this.robotPose.x;
    const ry = this.robotPose.y;
    const yaw = this.robotPose.yaw;
    const s = this.worldToScreen(rx, ry);

    const fovRad = (240 * Math.PI) / 180;
    const halfFov = fovRad / 2;
    const rangeM = 3.6;
    const rangePx = (rangeM / this.mapInfo.resolution) * this.zoom;

    ctx.translate(s.x, s.y);
    ctx.rotate(-yaw);

    // Purple wash cone
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, rangePx, -halfFov, halfFov);
    ctx.closePath();

    ctx.fillStyle = 'rgba(192, 132, 252, 0.08)';
    ctx.fill();

    ctx.strokeStyle = 'rgba(168, 85, 247, 0.35)';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 4]);
    ctx.stroke();

    // Concentric purple zigzag bands
    ctx.strokeStyle = 'rgba(192, 132, 252, 0.25)';
    ctx.lineWidth = 1.0;
    ctx.setLineDash([]);
    for (let r = rangePx * 0.35; r < rangePx; r += rangePx * 0.28) {
      ctx.beginPath();
      ctx.arc(0, 0, r, -halfFov * 0.85, halfFov * 0.85);
      ctx.stroke();
    }

    ctx.restore();
  }

  // Exact Match to Screenshot: Vivid Emerald-Teal (#00e5c8) Laser Points
  drawLidarPoints(ctx) {
    ctx.save();
    const rx = this.robotPose.x;
    const ry = this.robotPose.y;
    const yaw = this.robotPose.yaw;
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);

    ctx.fillStyle = '#00e5c8'; // Vivid Emerald-Teal
    ctx.strokeStyle = '#0f766e';
    ctx.lineWidth = 0.5;

    for (let i = 0; i < this.lidarPoints.length; i++) {
      const lx = this.lidarPoints[i][0];
      const ly = this.lidarPoints[i][1];
      const wx = rx + (lx * cosY - ly * sinY);
      const wy = ry + (lx * sinY + ly * cosY);
      const s = this.worldToScreen(wx, wy);

      ctx.beginPath();
      ctx.arc(s.x, s.y, 2.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  drawGlobalPath(ctx) {
    ctx.save();
    // Industrial Navigation Path: Clean 2.5px solid engineering blue with direction chevrons
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    const start = this.worldToScreen(this.globalPath[0][0], this.globalPath[0][1]);
    ctx.moveTo(start.x, start.y);
    for (let i = 1; i < this.globalPath.length; i++) {
      const pt = this.worldToScreen(this.globalPath[i][0], this.globalPath[i][1]);
      ctx.lineTo(pt.x, pt.y);
    }
    ctx.stroke();

    // Draw small directional chevrons along path
    const interval = Math.max(4, Math.floor(this.globalPath.length / 8));
    ctx.fillStyle = '#60a5fa';
    for (let i = interval; i < this.globalPath.length - 1; i += interval) {
      const p1 = this.worldToScreen(this.globalPath[i][0], this.globalPath[i][1]);
      const p2 = this.worldToScreen(this.globalPath[i + 1][0], this.globalPath[i + 1][1]);
      const ang = Math.atan2(p2.y - p1.y, p2.x - p1.x);

      ctx.save();
      ctx.translate(p1.x, p1.y);
      ctx.rotate(ang);
      ctx.beginPath();
      ctx.moveTo(-4, -3);
      ctx.lineTo(3, 0);
      ctx.lineTo(-4, 3);
      ctx.stroke();
      ctx.restore();
    }

    ctx.restore();
  }

  drawLocalPath(ctx) {
    ctx.save();
    // Crisp emerald trajectory arc from local controller
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2.0;
    ctx.setLineDash([3, 2]);

    ctx.beginPath();
    const start = this.worldToScreen(this.localPath[0][0], this.localPath[0][1]);
    ctx.moveTo(start.x, start.y);
    for (let i = 1; i < this.localPath.length; i++) {
      const pt = this.worldToScreen(this.localPath[i][0], this.localPath[i][1]);
      ctx.lineTo(pt.x, pt.y);
    }
    ctx.stroke();
    ctx.restore();
  }

  drawWaypoints(ctx) {
    ctx.save();
    ctx.font = '700 11px "JetBrains Mono", monospace';

    for (const wp of this.waypoints) {
      const s = this.worldToScreen(wp.x, wp.y);
      const isHovered = this.hoveredWaypoint && this.hoveredWaypoint.id === wp.id;
      const isDock = wp.type === 'charge' || wp.id === 'dock';
      const code = wp.code || (isDock ? 'DOCK' : wp.name.substring(0, 5).toUpperCase());

      // Outer badge shape with high contrast
      ctx.fillStyle = isDock ? '#059669' : (isHovered ? '#1d4ed8' : '#2563eb');
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;

      const bw = 54;
      const bh = 22;
      ctx.beginPath();
      ctx.roundRect(s.x - bw / 2, s.y - bh / 2, bw, bh, 4);
      ctx.fill();
      ctx.stroke();

      // Pin center dot
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(s.x - bw / 2 + 8, s.y, 3.5, 0, Math.PI * 2);
      ctx.fill();

      // Station Code Text
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(code, s.x + 5, s.y);

      // On Hover or Click: Show detailed popover
      if (isHovered) {
        ctx.font = '600 12px "Inter", sans-serif';
        const labelW = ctx.measureText(wp.name).width + 20;
        ctx.fillStyle = '#111827';
        ctx.strokeStyle = '#60a5fa';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.roundRect(s.x - labelW / 2, s.y - 38, labelW, 24, 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.fillText(wp.name, s.x, s.y - 26);
        ctx.font = '700 11px "JetBrains Mono", monospace';
      }
    }
    ctx.restore();
  }

  drawActiveGoalPin(ctx) {
    ctx.save();
    const s = this.worldToScreen(this.activeGoal.x, this.activeGoal.y);
    const yaw = this.activeGoal.yaw;

    // Industrial Target Crosshair
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;

    // Crosshair rings
    ctx.beginPath();
    ctx.arc(s.x, s.y, 16, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(s.x, s.y, 5, 0, Math.PI * 2);
    ctx.stroke();

    // Cross ticks
    ctx.beginPath();
    ctx.moveTo(s.x - 22, s.y); ctx.lineTo(s.x + 22, s.y);
    ctx.moveTo(s.x, s.y - 22); ctx.lineTo(s.x, s.y + 22);
    ctx.stroke();

    // Heading arrow
    const arrLen = 32;
    const tx = s.x + Math.cos(-yaw) * arrLen;
    const ty = s.y + Math.sin(-yaw) * arrLen;
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(tx, ty);
    ctx.strokeStyle = '#f87171';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Clean technical coordinate badge
    ctx.font = '700 11px "JetBrains Mono", monospace';
    ctx.fillStyle = '#111827';
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 1.5;
    const tag = `HEDEF: [${this.activeGoal.x.toFixed(2)}, ${this.activeGoal.y.toFixed(2)}]`;
    const tw = ctx.measureText(tag).width + 16;

    ctx.beginPath();
    ctx.roundRect(s.x - tw / 2, s.y + 22, tw, 20, 4);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(tag, s.x, s.y + 32);

    ctx.restore();
  }

  drawGoalPlacementPreview(ctx) {
    ctx.save();
    const s = this.worldToScreen(this.goalStartWorld.x, this.goalStartWorld.y);
    const yaw = this.goalCurrentAngle;

    ctx.strokeStyle = this.mode === 'navigate' ? '#3b82f6' : '#10b981';
    ctx.fillStyle = this.mode === 'navigate' ? 'rgba(59, 130, 246, 0.25)' : 'rgba(16, 185, 129, 0.25)';
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.arc(s.x, s.y, 18, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    const arrLen = 46;
    const tx = s.x + Math.cos(-yaw) * arrLen;
    const ty = s.y + Math.sin(-yaw) * arrLen;
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(tx, ty);
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Arrowhead
    const headLen = 12;
    const angle = -yaw;
    ctx.beginPath();
    ctx.moveTo(tx, ty);
    ctx.lineTo(tx - headLen * Math.cos(angle - Math.PI / 6), ty - headLen * Math.sin(angle - Math.PI / 6));
    ctx.moveTo(tx, ty);
    ctx.lineTo(tx - headLen * Math.cos(angle + Math.PI / 6), ty - headLen * Math.sin(angle + Math.PI / 6));
    ctx.stroke();

    const deg = Math.round((yaw * 180) / Math.PI);
    ctx.font = '700 12px "JetBrains Mono", monospace';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.fillText(`${deg}°`, s.x, s.y - 24);

    ctx.restore();
  }

  drawMeasurementLine(ctx) {
    ctx.save();
    const p1 = this.worldToScreen(this.measureStart.x, this.measureStart.y);
    const p2 = this.worldToScreen(this.measureCurrent.x, this.measureCurrent.y);
    const dist = Math.hypot(this.measureCurrent.x - this.measureStart.x, this.measureCurrent.y - this.measureStart.y);

    ctx.strokeStyle = '#f59e0b'; // Amber ruler line
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();

    // Terminal crossbars
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(p1.x, p1.y, 5, 0, Math.PI * 2);
    ctx.arc(p2.x, p2.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#f59e0b';
    ctx.fill();

    // Dimension Tag
    const midX = (p1.x + p2.x) / 2;
    const midY = (p1.y + p2.y) / 2;
    const text = `${dist.toFixed(2)} m`;
    ctx.font = '700 12px "JetBrains Mono", monospace';
    const tw = ctx.measureText(text).width + 16;

    ctx.fillStyle = '#111827';
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(midX - tw / 2, midY - 12, tw, 24, 4);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#fbbf24';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, midX, midY);

    ctx.restore();
  }

  // ============================================================================
  // TRUE-TO-SCALE INDUSTRIAL ACKERMANN AMR MODEL
  // ============================================================================
  drawRobotModel(ctx) {
    ctx.save();
    const s = this.worldToScreen(this.robotPose.x, this.robotPose.y);
    const yaw = this.robotPose.yaw;
    const steerRad = (this.steerDeg * Math.PI) / 180;

    ctx.translate(s.x, s.y);
    ctx.rotate(-yaw);

    const res = this.mapInfo.resolution || 0.05;
    // Physical vehicle dimensions: 0.34m long, 0.22m wide
    // Guarantee minimum size of 40x26px so robot is ALWAYS clearly visible
    const rawL = (0.34 / res) * this.zoom;
    const rawW = (0.22 / res) * this.zoom;
    const carLengthPx = Math.max(40, rawL);
    const carWidthPx = Math.max(26, rawW);
    const scale = carLengthPx / 0.34;
    const wheelLen = Math.max(10, 0.08 * scale);
    const wheelWid = Math.max(5, 0.035 * scale);

    const hx = carLengthPx / 2;
    const hy = carWidthPx / 2;

    // 1. Safety Clearance Footprint (Dashed boundary)
    if (this.layers.safetyFootprint) {
      const bufLen = carLengthPx * 1.25;
      const bufWid = carWidthPx * 1.35;
      ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(-bufLen / 2, -bufWid / 2, bufLen, bufWid);
      ctx.setLineDash([]);
    }

    // 2. Commercial Red AMR Chassis Body (Matching Reference Screenshot)
    ctx.fillStyle = '#991b1b';       // Dark red industrial chassis
    ctx.strokeStyle = '#0f172a';     // Solid black heavy border
    ctx.lineWidth = 2.0;

    ctx.beginPath();
    ctx.roundRect(-hx, -hy, carLengthPx, carWidthPx, 4);
    ctx.fill();
    ctx.stroke();

    // Inner metallic surface plate
    ctx.fillStyle = '#dc2626';
    ctx.beginPath();
    ctx.roundRect(-hx + 3, -hy + 3, carLengthPx - 6, carWidthPx - 6, 2);
    ctx.fill();

    // 3. Black Safety Bumpers (Front & Rear)
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(hx - 4, -hy, 4, carWidthPx);
    ctx.fillRect(-hx, -hy, 4, carWidthPx);

    // 4. Rear Drive Wheels (Heavy Black Rubber Tires)
    ctx.fillStyle = '#0f172a';
    const rearX = -hx + wheelLen * 0.75;
    ctx.fillRect(rearX - wheelLen / 2, -hy - wheelWid, wheelLen, wheelWid);
    ctx.fillRect(rearX - wheelLen / 2, hy, wheelLen, wheelWid);

    // Wheel rims
    ctx.fillStyle = '#64748b';
    ctx.fillRect(rearX - wheelLen / 4, -hy - wheelWid + 1, wheelLen / 2, wheelWid - 2);
    ctx.fillRect(rearX - wheelLen / 4, hy + 1, wheelLen / 2, wheelWid - 2);

    // 5. Front Steered Wheels (Rotated by Ackermann steerRad)
    const frontX = hx - wheelLen * 0.75;

    // Front Left Wheel
    ctx.save();
    ctx.translate(frontX, -hy - wheelWid / 2);
    ctx.rotate(-steerRad);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(-wheelLen / 2, -wheelWid / 2, wheelLen, wheelWid);
    ctx.fillStyle = '#64748b';
    ctx.fillRect(-wheelLen / 4, -wheelWid / 2 + 1, wheelLen / 2, wheelWid - 2);
    ctx.restore();

    // Front Right Wheel
    ctx.save();
    ctx.translate(frontX, hy + wheelWid / 2);
    ctx.rotate(-steerRad);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(-wheelLen / 2, -wheelWid / 2, wheelLen, wheelWid);
    ctx.fillStyle = '#64748b';
    ctx.fillRect(-wheelLen / 4, -wheelWid / 2 + 1, wheelLen / 2, wheelWid - 2);
    ctx.restore();

    // 6. Center Rotation Axis Crosshair
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(rearX - 6, 0); ctx.lineTo(rearX + 6, 0);
    ctx.moveTo(rearX, -6); ctx.lineTo(rearX, 6);
    ctx.stroke();

    // 7. Hokuyo LiDAR Scanner (Front Center)
    const lidarX = hx - 8;
    ctx.beginPath();
    ctx.arc(lidarX, 0, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#0284c7';
    ctx.fill();
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(lidarX + 2, 0, 2, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    // 8. Forward Direction Arrow (High-Vis Cyan/White)
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(hx, 0);
    ctx.lineTo(hx + 20, 0);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(hx + 20, 0);
    ctx.lineTo(hx + 12, -5);
    ctx.lineTo(hx + 12, 5);
    ctx.closePath();
    ctx.fillStyle = '#38bdf8';
    ctx.fill();

    // 9. AGV Unit Label
    ctx.font = '800 10px "JetBrains Mono", monospace';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('AGV-01', 0, 0);

    ctx.restore(); // Restores vehicle coordinate transform

    // 10. Floating Unit Status Tag above vehicle
    ctx.save();
    ctx.translate(s.x, s.y - hy - 18);
    const tagText = 'AGV-01 [AKTİF]';
    ctx.font = '700 10px "JetBrains Mono", monospace';
    const tagW = ctx.measureText(tagText).width + 18;
    ctx.fillStyle = 'rgba(17, 24, 34, 0.9)';
    ctx.strokeStyle = '#00e5c8';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(-tagW / 2, -10, tagW, 20, 3);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#22c55e';
    ctx.beginPath();
    ctx.arc(-tagW / 2 + 7, 0, 3, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(tagText, 3, 0);
    ctx.restore();
  }

  // Bottom-Left Floating Overview Mini-Map HUD matching commercial reference screenshot
  drawMiniMap(ctx) {
    if (!this.mapImageLoaded || !this.mapImage) return;

    ctx.save();
    // Position at bottom-left: offset by 60px from the left toolbar, width 145px, height 115px
    const mmW = 145;
    const mmH = 115;
    const mmX = 60;
    const mmY = this.displayHeight - mmH - 16;

    // Dark container box with solid border (as in screenshot)
    ctx.fillStyle = '#475569';
    ctx.fillRect(mmX, mmY, mmW, mmH);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.0;
    ctx.strokeRect(mmX, mmY, mmW, mmH);

    // Mini map image fitted inside
    const mapAspect = this.mapInfo.width / this.mapInfo.height;
    let targetW = mmW - 10;
    let targetH = targetW / mapAspect;
    if (targetH > mmH - 10) {
      targetH = mmH - 10;
      targetW = targetH * mapAspect;
    }
    const imgX = mmX + (mmW - targetW) / 2;
    const imgY = mmY + (mmH - targetH) / 2;

    ctx.drawImage(this.mapImage, imgX, imgY, targetW, targetH);

    // Current viewport rectangle on mini-map
    const visWorldTL = this.screenToWorld(0, 0);
    const visWorldBR = this.screenToWorld(this.displayWidth, this.displayHeight);

    const ox = this.mapInfo.origin.x;
    const oy = this.mapInfo.origin.y;
    const res = this.mapInfo.resolution;
    const mapW = this.mapInfo.width;
    const mapH = this.mapInfo.height;

    const u1 = (visWorldTL.x - ox) / res;
    const v1 = mapH - 1 - (visWorldTL.y - oy) / res;
    const u2 = (visWorldBR.x - ox) / res;
    const v2 = mapH - 1 - (visWorldBR.y - oy) / res;

    const rectU1 = Math.max(0, Math.min(mapW, Math.min(u1, u2)));
    const rectU2 = Math.max(0, Math.min(mapW, Math.max(u1, u2)));
    const rectV1 = Math.max(0, Math.min(mapH, Math.min(v1, v2)));
    const rectV2 = Math.max(0, Math.min(mapH, Math.max(v1, v2)));

    const vpX = imgX + (rectU1 / mapW) * targetW;
    const vpY = imgY + (rectV1 / mapH) * targetH;
    const vpW = Math.max(8, ((rectU2 - rectU1) / mapW) * targetW);
    const vpH = Math.max(8, ((rectV2 - rectV1) / mapH) * targetH);

    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 1.5;
    ctx.fillStyle = 'rgba(56, 189, 248, 0.2)';
    ctx.fillRect(vpX, vpY, vpW, vpH);
    ctx.strokeRect(vpX, vpY, vpW, vpH);

    // Robot indicator dot on mini-map
    const robU = (this.robotPose.x - ox) / res;
    const robV = mapH - 1 - (this.robotPose.y - oy) / res;
    const robMmX = imgX + (robU / mapW) * targetW;
    const robMmY = imgY + (robV / mapH) * targetH;

    ctx.fillStyle = '#dc2626';
    ctx.beginPath();
    ctx.arc(robMmX, robMmY, 3.0, 0, Math.PI * 2);
    ctx.fill();

    // Tiny resize icon at top-right of mini-map
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.font = '11px sans-serif';
    ctx.fillText('⤢', mmX + mmW - 14, mmY + 14);

    ctx.restore();
  }

  drawCoordinateLegend(ctx) {
    ctx.save();
    ctx.font = '600 11px "JetBrains Mono", monospace';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    
    const rx = this.robotPose.x.toFixed(2);
    const ry = this.robotPose.y.toFixed(2);
    const yawDeg = Math.round((this.robotPose.yaw * 180) / Math.PI);
    const steer = this.steerDeg.toFixed(1);
    
    ctx.fillText(`AGV-01: [${rx}m, ${ry}m, ${yawDeg}°] | STEER: ${steer}° | ZOOM: ${(this.zoom * 10).toFixed(0)}%`, 220, this.displayHeight - 16);
    ctx.restore();
  }
}

window.MapViewer = MapViewer;
