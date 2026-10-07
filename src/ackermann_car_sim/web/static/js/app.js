/**
 * ==============================================================================
 * LOGIX AMR - COMMERCIAL FLEET SCADA & SLAM SYSTEM
 * 100% Visual & Functional Parity with Industrial Commercial Fleet Software
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  // Operational State
  const state = {
    connected: false,
    mode: 'nav', // 'nav' or 'slam'
    navStatus: 'STANDBY',
    previousNavStatus: 'STANDBY',
    estop: false,
    battery: 98,
    speed: 0.0,
    steerDeg: 0.0,
    speedLimit: 0.4,
    waypoints: [],
    activeGoal: null,
    mapVersion: 0
  };

  // 1. Initialize High-Precision Fullscreen CAD Map Viewer
  const mapViewer = new MapViewer('map-canvas', {
    onGoalSelected: (x, y, yaw) => dispatchGoal(x, y, yaw),
    onInitialPoseSelected: (x, y, yaw) => setInitialPose(x, y, yaw),
    onWaypointAddRequested: (x, y) => promptAddWaypoint(x, y),
    onWaypointClicked: (wp) => {
      if (confirm(`İstasyon: ${wp.name} (${wp.code})\nRobot bu istasyona sevk edilsin mi?`)) {
        dispatchGoal(wp.x, wp.y, wp.yaw || 0.0, wp.name);
      }
    }
  });

  // DOM Elements - Header
  const elTopConnTag = document.getElementById('top-conn-tag');
  const elBtnTopEstop = document.getElementById('btn-top-estop');
  const elBtnTopFullscreen = document.getElementById('btn-top-fullscreen');
  const elBtnTopLang = document.getElementById('btn-top-lang');

  // DOM Elements - Left Tool Rail
  const elBtnRailRoute = document.getElementById('btn-rail-route');
  const elBtnRailGoal = document.getElementById('btn-rail-goal');
  const elBtnRailStations = document.getElementById('btn-rail-stations');
  const elBtnRailZones = document.getElementById('btn-rail-zones');
  const elBtnRailGrid = document.getElementById('btn-rail-grid');
  const elBtnRailLidar = document.getElementById('btn-rail-lidar');
  const elBtnRailCamera = document.getElementById('btn-rail-camera');
  const elBtnRail2d = document.getElementById('btn-rail-2d');
  const elBtnRailZoomIn = document.getElementById('btn-rail-zoomin');
  const elBtnRailZoomOut = document.getElementById('btn-rail-zoomout');
  const elBtnRailRecenter = document.getElementById('btn-rail-recenter');
  const elBtnRailFit = document.getElementById('btn-rail-fit');

  // DOM Elements - Camera PiP Widget
  const elCameraWidget = document.getElementById('camera-pip-widget');
  const elBtnPipMinimize = document.getElementById('btn-pip-minimize');
  const elBtnPipClose = document.getElementById('btn-pip-close');

  // DOM Elements - Dispatch Drawer
  const elDispatchDrawer = document.getElementById('dispatch-drawer');
  const elBtnCloseDrawer = document.getElementById('btn-close-drawer');
  const elBtnModeNav = document.getElementById('btn-mode-nav');
  const elBtnModeSlam = document.getElementById('btn-mode-slam');
  const elPaneNav = document.getElementById('pane-nav');
  const elPaneSlam = document.getElementById('pane-slam');

  const elBtnPickGoal = document.getElementById('btn-pick-goal');
  const elBtnSaveMap = document.getElementById('btn-save-map');
  const elStationsContainer = document.getElementById('stations-list-container');
  const elBtnAddStation = document.getElementById('btn-add-station');

  const elMissionBox = document.getElementById('nav-mission-box');
  const elMissionDist = document.getElementById('nav-dist-val');
  const elMissionEta = document.getElementById('nav-eta-val');
  const elBtnCancelMission = document.getElementById('btn-cancel-mission');

  // Drawer Footer Telemetry
  const elFootSpeed = document.getElementById('foot-speed');
  const elFootAmcl = document.getElementById('foot-amcl');
  const elFootBattery = document.getElementById('foot-battery');
  const elFootConn = document.getElementById('foot-conn');
  const elToastContainer = document.getElementById('toast-container');

  // ============================================================================
  // 1. DRAWER TOGGLING & RAIL CONTROLS
  // ============================================================================
  function toggleDrawer(forceOpen = null) {
    if (!elDispatchDrawer) return;
    const shouldOpen = forceOpen !== null ? forceOpen : elDispatchDrawer.classList.contains('collapsed');
    if (shouldOpen) {
      elDispatchDrawer.classList.remove('collapsed');
      elBtnRailRoute.classList.add('active');
    } else {
      elDispatchDrawer.classList.add('collapsed');
      elBtnRailRoute.classList.remove('active');
    }
  }

  if (elBtnRailRoute) elBtnRailRoute.addEventListener('click', () => toggleDrawer());
  if (elBtnCloseDrawer) elBtnCloseDrawer.addEventListener('click', () => toggleDrawer(false));

  if (elBtnRailGoal) {
    elBtnRailGoal.addEventListener('click', () => {
      mapViewer.setToolMode('set_goal');
      showToast('🎯 Harita üzerinde hedef ve varış yönünü belirleyin. (İptal: ESC)', 'info');
      elBtnRailGoal.classList.add('active');
      if (window.soundManager) window.soundManager.playClick();
    });
  }

  if (elBtnRailStations) {
    elBtnRailStations.addEventListener('click', () => {
      toggleDrawer(true);
      setMode('nav');
      if (window.soundManager) window.soundManager.playClick();
    });
  }

  if (elBtnRailZones) {
    elBtnRailZones.addEventListener('click', () => {
      const active = elBtnRailZones.classList.toggle('active');
      mapViewer.layers.forbiddenZones = active;
      showToast(active ? 'Yasak bölge çizgileri görünür.' : 'Yasak bölge çizgileri gizlendi.', 'info');
    });
  }

  if (elBtnRailGrid) {
    elBtnRailGrid.addEventListener('click', () => {
      mapViewer.layers.grid = !mapViewer.layers.grid;
      elBtnRailGrid.classList.toggle('active', mapViewer.layers.grid);
      showToast(mapViewer.layers.grid ? 'CAD metrik ızgara açıldı.' : 'CAD metrik ızgara kapatıldı.', 'info');
    });
  }

  if (elBtnRailLidar) {
    elBtnRailLidar.addEventListener('click', () => {
      const active = !mapViewer.layers.lidar;
      mapViewer.layers.lidar = active;
      mapViewer.layers.lidarFov = active;
      elBtnRailLidar.classList.toggle('active', active);
      showToast(active ? 'Lazer tarama ve güvenlik konisi aktif.' : 'Lazer katmanı gizlendi.', 'info');
    });
  }

  if (elBtnRail2d) {
    elBtnRail2d.addEventListener('click', () => {
      mapViewer.fitArena();
      showToast('2D CAD görünümü sıfırlandı.', 'info');
    });
  }

  // ============================================================================
  // CAMERA FPV (RealSense PiP) CONTROLS
  // ============================================================================
  function toggleCameraWidget(force = null) {
    if (!elCameraWidget) return;
    const isHidden = elCameraWidget.classList.contains('hidden');
    const show = force !== null ? force : isHidden;
    if (show) {
      elCameraWidget.classList.remove('hidden');
      if (elBtnRailCamera) elBtnRailCamera.classList.add('active');
      showToast('📹 Canlı kamera akışı açıldı.', 'info');
    } else {
      elCameraWidget.classList.add('hidden');
      if (elBtnRailCamera) elBtnRailCamera.classList.remove('active');
      showToast('📹 Canlı kamera akışı gizlendi.', 'info');
    }
  }

  if (elBtnRailCamera) {
    elBtnRailCamera.addEventListener('click', () => toggleCameraWidget());
  }

  if (elBtnPipClose) {
    elBtnPipClose.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleCameraWidget(false);
    });
  }

  if (elBtnPipMinimize) {
    elBtnPipMinimize.addEventListener('click', (e) => {
      e.stopPropagation();
      if (!elCameraWidget) return;
      const isMin = elCameraWidget.classList.toggle('minimized');
      elBtnPipMinimize.innerHTML = isMin ? '<i class="fa-solid fa-square"></i>' : '<i class="fa-solid fa-minus"></i>';
      elBtnPipMinimize.title = isMin ? 'Genişlet' : 'Küçült';
    });
  }

  // Draggable PiP Header
  const pipHeader = elCameraWidget ? elCameraWidget.querySelector('.camera-pip-header') : null;
  if (pipHeader && elCameraWidget) {
    let isDragging = false;
    let startX = 0, startY = 0;
    let origRight = 24, origBottom = 24;

    pipHeader.style.cursor = 'move';

    pipHeader.addEventListener('mousedown', (e) => {
      if (e.target.closest('.btn-pip-action')) return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;

      const rect = elCameraWidget.getBoundingClientRect();
      origRight = window.innerWidth - rect.right;
      origBottom = window.innerHeight - rect.bottom;

      const onMouseMove = (moveEvt) => {
        if (!isDragging) return;
        const dx = moveEvt.clientX - startX;
        const dy = moveEvt.clientY - startY;
        const newRight = Math.max(10, Math.min(window.innerWidth - 100, origRight - dx));
        const newBottom = Math.max(10, Math.min(window.innerHeight - 50, origBottom - dy));
        elCameraWidget.style.right = `${newRight}px`;
        elCameraWidget.style.bottom = `${newBottom}px`;
      };

      const onMouseUp = () => {
        isDragging = false;
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
      };

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    });
  }

  if (elBtnRailZoomIn) elBtnRailZoomIn.addEventListener('click', () => { mapViewer.zoomIn(); });
  if (elBtnRailZoomOut) elBtnRailZoomOut.addEventListener('click', () => { mapViewer.zoomOut(); });
  if (elBtnRailRecenter) elBtnRailRecenter.addEventListener('click', () => mapViewer.recenterRobot());
  if (elBtnRailFit) elBtnRailFit.addEventListener('click', () => mapViewer.fitArena());

  mapViewer.onToolModeChanged = (m) => {
    if (m === 'pan') {
      if (elBtnPickGoal) {
        elBtnPickGoal.classList.remove('targeting');
        elBtnPickGoal.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> HARİTADAN HEDEF SEÇ';
      }
      if (elBtnRailGoal) {
        elBtnRailGoal.classList.remove('active');
      }
    }
  };

  // Top Bar Fullscreen
  if (elBtnTopFullscreen) {
    elBtnTopFullscreen.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  // ============================================================================
  // 2. TWO-MODE SWITCHING (NAV vs SLAM)
  // ============================================================================
  function setMode(mode) {
    state.mode = mode;
    mapViewer.setToolMode('pan'); // ALWAYS keep Pan/Zoom active!
    if (mode === 'slam') {
      if (elBtnModeSlam) elBtnModeSlam.classList.add('active');
      if (elBtnModeNav) elBtnModeNav.classList.remove('active');
      if (elPaneSlam) elPaneSlam.classList.add('active');
      if (elPaneNav) elPaneNav.classList.remove('active');
      showToast('🗺️ Canlı SLAM Harita Tarama Modu Aktif.', 'warning');
    } else {
      if (elBtnModeNav) elBtnModeNav.classList.add('active');
      if (elBtnModeSlam) elBtnModeSlam.classList.remove('active');
      if (elPaneNav) elPaneNav.classList.add('active');
      if (elPaneSlam) elPaneSlam.classList.remove('active');
      showToast('🚀 Otonom Navigasyon Modu Aktif.', 'success');
    }
    if (window.soundManager) window.soundManager.playClick();
  }

  if (elBtnModeNav) elBtnModeNav.addEventListener('click', () => setMode('nav'));
  if (elBtnModeSlam) elBtnModeSlam.addEventListener('click', () => setMode('slam'));

  // ============================================================================
  // 3. GOAL PICKING & DISPATCH
  // ============================================================================
  if (elBtnPickGoal) {
    elBtnPickGoal.addEventListener('click', () => {
      mapViewer.setToolMode('set_goal');
      elBtnPickGoal.classList.add('targeting');
      elBtnPickGoal.innerHTML = '<i class="fa-solid fa-crosshairs fa-spin"></i> HARİTAYA TIKLAYIN...';
      showToast('Haritada hedef noktaya tıklayıp yönü belirleyin. (İptal: ESC)', 'info');
      if (window.soundManager) window.soundManager.playClick();
    });
  }

  async function dispatchGoal(x, y, yaw, targetName = null) {
    if (elBtnPickGoal) {
      elBtnPickGoal.classList.remove('targeting');
      elBtnPickGoal.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> HARİTADAN HEDEF SEÇ';
    }

    const name = targetName || `[${x.toFixed(1)}, ${y.toFixed(1)}]`;
    showToast(`🚀 Sefer başlatılıyor: ${name}`, 'info');
    if (window.soundManager) window.soundManager.playClick();

    mapViewer.activeGoal = { x, y, yaw };

    try {
      const resp = await fetch('/api/navigation/goal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x, y, yaw, frame_id: 'map' })
      });
      const data = await resp.json();
      if (resp.ok) {
        showToast('✅ Nav2 hedefi onayladı, rota hesaplanıyor...', 'success');
      } else {
        showToast(`❌ Sefer hatası: ${data.detail || 'Bilinmeyen hata'}`, 'error');
      }
    } catch (err) {
      showToast('❌ Bağlantı hatası: Sunucuya ulaşılamadı.', 'error');
    }
  }

  // Cancel Active Mission
  if (elBtnCancelMission) {
    elBtnCancelMission.addEventListener('click', async () => {
      try {
        await fetch('/api/navigation/cancel', { method: 'POST' });
        mapViewer.activeGoal = null;
        mapViewer.globalPath = [];
        mapViewer.localPath = [];
        showToast('⏹️ Sefer kullanıcı tarafından iptal edildi.', 'warning');
        if (window.soundManager) window.soundManager.playClick();
      } catch (e) {
        console.error(e);
      }
    });
  }

  // ============================================================================
  // 4. ONE-CLICK MAP SAVING (SLAM -> ARENA MAP DISK SAVE)
  // ============================================================================
  if (elBtnSaveMap) {
    elBtnSaveMap.addEventListener('click', async () => {
      elBtnSaveMap.disabled = true;
      elBtnSaveMap.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> HARİTA KAYDEDİLİYOR...';

      try {
        const resp = await fetch('/api/map/save', { method: 'POST' });
        const data = await resp.json();

        if (resp.ok) {
          showToast('🎉 Harita başarıyla kaydedildi ve sisteme işlendi!', 'success');
          if (window.soundManager) window.soundManager.playGoalArrived();
          
          // Refresh Map Image in memory and canvas
          mapViewer.reloadMapImage();

          // Auto-switch to Autonomous Navigation mode
          setTimeout(() => {
            setMode('nav');
          }, 1200);
        } else {
          showToast(`⚠️ Kaydetme hatası: ${data.detail || 'SLAM haritası henüz oluşmadı.'}`, 'error');
        }
      } catch (err) {
        showToast('❌ Sunucu iletişim hatası.', 'error');
      } finally {
        elBtnSaveMap.disabled = false;
        elBtnSaveMap.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> HARİTAYI KAYDET VE UYGULA';
      }
    });
  }

  // ============================================================================
  // 5. QUICK STATIONS DISPATCH
  // ============================================================================
  const defaultStations = [
    { id: 'dock', name: 'Şarj İstasyonu', code: 'DOCK', x: 0.0, y: 0.0, yaw: 0.0, type: 'charge' },
    { id: 'st1', name: 'Yükleme İstasyonu', code: 'ST-01', x: 3.0, y: 2.0, yaw: 0.0, type: 'work' },
    { id: 'st2', name: 'Boşaltma İstasyonu', code: 'ST-02', x: 1.5, y: -2.0, yaw: -1.57, type: 'work' }
  ];

  state.waypoints = defaultStations;
  mapViewer.waypoints = state.waypoints;
  renderStationsList();

  function renderStationsList() {
    if (!elStationsContainer) return;
    elStationsContainer.innerHTML = '';

    state.waypoints.forEach((wp) => {
      const isDock = wp.id === 'dock' || wp.type === 'charge';
      const item = document.createElement('div');
      item.className = 'station-row-item';
      item.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="station-badge-code ${isDock ? 'dock' : ''}">${wp.code || 'ST'}</span>
          <span class="station-item-name">${wp.name}</span>
        </div>
        <button class="btn-station-dispatch" data-id="${wp.id}">GİT</button>
      `;

      item.querySelector('.btn-station-dispatch').addEventListener('click', () => {
        dispatchGoal(wp.x, wp.y, wp.yaw || 0.0, wp.name);
      });

      elStationsContainer.appendChild(item);
    });
  }

  // Add Current Pose as Station
  if (elBtnAddStation) {
    elBtnAddStation.addEventListener('click', () => {
      const name = prompt('Yeni İstasyon Adını Girin (Örn: Paketleme, Depo-3):');
      if (!name) return;
      const count = state.waypoints.length + 1;
      const code = `ST-${count < 10 ? '0' + count : count}`;
      const newWp = {
        id: `custom_${Date.now()}`,
        name: name.trim(),
        code: code,
        x: mapViewer.robotPose.x,
        y: mapViewer.robotPose.y,
        yaw: mapViewer.robotPose.yaw,
        type: 'work'
      };
      state.waypoints.push(newWp);
      mapViewer.waypoints = state.waypoints;
      renderStationsList();
      showToast(`📍 Yeni istasyon kaydedildi: ${newWp.name} (${code})`, 'success');
    });
  }

  // ============================================================================
  // 6. INDUSTRIAL EMERGENCY STOP (E-STOP)
  // ============================================================================
  if (elBtnTopEstop) {
    elBtnTopEstop.addEventListener('click', async () => {
      try {
        const resp = await fetch('/api/estop/toggle', { method: 'POST' });
        const data = await resp.json();
        state.estop = data.emergency_stop;
        updateEstopUI(state.estop);
      } catch (err) {
        console.error(err);
      }
    });
  }

  function updateEstopUI(isLatched) {
    if (!elBtnTopEstop) return;
    if (isLatched) {
      elBtnTopEstop.classList.add('latched');
      elBtnTopEstop.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> STOP KİLİTLİ';
      showToast('🛑 ACİL DURDURMA DEVREYE GİRDİ! Robot kilitlendi.', 'error');
      if (window.soundManager) window.soundManager.playEstop();
    } else {
      elBtnTopEstop.classList.remove('latched');
      elBtnTopEstop.innerHTML = '<i class="fa-solid fa-octagon-exclamation"></i> E-STOP';
      showToast('✅ Acil stop kilidi çözüldü. Sistem hazır.', 'success');
      if (window.soundManager) window.soundManager.playClick();
    }
  }

  // ============================================================================
  // 7. TELEOP DRIVING CONTROLS (KEYBOARD & VIRTUAL KEYPAD)
  // ============================================================================
  async function sendCmdVel(linear, angular) {
    if (state.estop) return;
    try {
      await fetch('/api/teleop/cmd_vel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ linear, angular })
      });
    } catch (e) {}
  }

  // Speed Presets
  document.querySelectorAll('.btn-speed-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-speed-pill').forEach(b => {
        b.classList.remove('active');
        b.style.background = '';
        b.style.color = '';
      });
      btn.classList.add('active');
      btn.style.background = 'var(--color-primary)';
      btn.style.color = '#ffffff';
      state.speedLimit = parseFloat(btn.dataset.speed) || 0.4;
      showToast(`Hız limiti: ${state.speedLimit} m/s`, 'info');
    });
  });

  // Virtual Keypad Clicks
  document.querySelectorAll('.btn-mini-key').forEach((btn) => {
    const dir = btn.dataset.dir;

    const startDrive = () => {
      if (dir === 'forward') sendCmdVel(state.speedLimit, 0.0);
      else if (dir === 'backward') sendCmdVel(-state.speedLimit, 0.0);
      else if (dir === 'left') sendCmdVel(state.speedLimit * 0.7, 0.6);
      else if (dir === 'right') sendCmdVel(state.speedLimit * 0.7, -0.6);
      else if (dir === 'stop') sendCmdVel(0.0, 0.0);
    };

    const stopDrive = () => {
      if (dir !== 'stop') sendCmdVel(0.0, 0.0);
    };

    btn.addEventListener('mousedown', startDrive);
    btn.addEventListener('mouseup', stopDrive);
    btn.addEventListener('touchstart', (e) => { e.preventDefault(); startDrive(); });
    btn.addEventListener('touchend', (e) => { e.preventDefault(); stopDrive(); });
  });

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
    const key = e.key.toLowerCase();

    if (key === 'w' || key === 'arrowup') {
      sendCmdVel(state.speedLimit, 0.0);
    } else if (key === 's' || key === 'arrowdown') {
      sendCmdVel(-state.speedLimit, 0.0);
    } else if (key === 'a' || key === 'arrowleft') {
      sendCmdVel(state.speedLimit * 0.7, 0.6);
    } else if (key === 'd' || key === 'arrowright') {
      sendCmdVel(state.speedLimit * 0.7, -0.6);
    } else if (key === ' ' || key === 'escape') {
      sendCmdVel(0.0, 0.0);
    }
  });

  window.addEventListener('keyup', (e) => {
    const key = e.key.toLowerCase();
    if (['w', 's', 'a', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
      sendCmdVel(0.0, 0.0);
    }
  });

  // ============================================================================
  // 8. 20 HZ WEBSOCKET TELEMETRY BRIDGE
  // ============================================================================
  function connectWebSocket() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/telemetry`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      state.connected = true;
      if (elTopConnTag) elTopConnTag.innerText = 'ONLINE (20 Hz)';
      if (elFootConn) {
        elFootConn.innerText = 'ONLINE';
        elFootConn.style.color = 'var(--color-nominal)';
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleTelemetry(data);
      } catch (err) {
        console.error('WS Parse Error', err);
      }
    };

    socket.onclose = () => {
      state.connected = false;
      if (elTopConnTag) elTopConnTag.innerText = 'OFFLINE';
      if (elFootConn) {
        elFootConn.innerText = 'OFFLINE';
        elFootConn.style.color = 'var(--color-alarm)';
      }
      setTimeout(connectWebSocket, 2000);
    };
  }

  function handleTelemetry(data) {
    // 1. Robot Map Pose
    if (data.pose) {
      mapViewer.robotPose = data.pose;
      if (!state.hasCenteredRobot && mapViewer.mapImageLoaded) {
        mapViewer.recenterRobot();
        state.hasCenteredRobot = true;
      }
    }

    // 2. Velocity & Steer
    if (data.velocity) {
      state.speed = data.velocity.speed || 0.0;
      state.steerDeg = data.velocity.steer_deg || 0.0;
      mapViewer.steerDeg = state.steerDeg;
      if (elFootSpeed) elFootSpeed.innerText = `${state.speed.toFixed(2)} m/s`;
    }

    // 3. Battery
    if (data.battery !== undefined) {
      state.battery = data.battery;
      if (elFootBattery) elFootBattery.innerText = `%${Math.round(state.battery)}`;
    }

    // 4. AMCL Covariance Lock
    if (data.pose && data.pose.cov !== undefined && elFootAmcl) {
      const cov = data.pose.cov;
      if (cov < 0.02) {
        elFootAmcl.innerText = 'KİLİTLİ';
        elFootAmcl.style.color = 'var(--color-nominal)';
      } else {
        elFootAmcl.innerText = 'ARANIYOR';
        elFootAmcl.style.color = 'var(--color-warning)';
      }
    }

    // 5. Sensor Points & Paths
    if (data.lidar) mapViewer.lidarPoints = data.lidar;
    if (data.global_plan) mapViewer.globalPath = data.global_plan;
    if (data.local_plan) mapViewer.localPath = data.local_plan;

    // 6. Navigation Status Transitions
    state.previousNavStatus = state.navStatus;
    state.navStatus = data.nav_status || 'STANDBY';

    if (state.navStatus === 'NAVIGATING') {
      if (elMissionBox) elMissionBox.classList.add('active');
      if (data.goal_feedback) {
        const dist = data.goal_feedback.distance_remaining || 0.0;
        const eta = data.goal_feedback.estimated_time_remaining || 0;
        if (elMissionDist) elMissionDist.innerText = `${dist.toFixed(2)} m`;
        if (elMissionEta) elMissionEta.innerText = `${Math.round(eta)} sn`;
      }
    } else {
      if (elMissionBox) elMissionBox.classList.remove('active');
      if (state.previousNavStatus === 'NAVIGATING' && state.navStatus === 'SUCCEEDED') {
        showToast('🎯 Hedefe başarıyla ulaşıldı!', 'success');
        if (window.soundManager) window.soundManager.playGoalArrived();
        mapViewer.activeGoal = null;
        mapViewer.globalPath = [];
      }
    }

    // 7. E-Stop sync
    if (data.estop !== undefined && data.estop !== state.estop) {
      state.estop = data.estop;
      updateEstopUI(state.estop);
    }

    // 8. Live SLAM Map Streaming
    if (data.map_version && data.map_version !== state.mapVersion) {
      state.mapVersion = data.map_version;
      mapViewer.updateDynamicMap(data.map_info);
    }
  }

  // ============================================================================
  // 9. TOAST NOTIFICATION SYSTEM
  // ============================================================================
  function showToast(message, type = 'info') {
    if (!elToastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-circle-check';
    else if (type === 'warning') icon = 'fa-triangle-exclamation';
    else if (type === 'error') icon = 'fa-circle-xmark';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    elToastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3000);
  }

  // Start WebSocket
  connectWebSocket();
});
