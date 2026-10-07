/**
 * ==============================================================================
 * LOGIX AMR - INDUSTRIAL MANUAL TELEOP & JOG SHUTTLE CONTROLLER
 * Safety Compliant with Deadman Switch (ISO 3691-4 Standards)
 * ==============================================================================
 */

class VirtualJoystick {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    
    this.maxSpeed = options.maxSpeed || 0.4;     // m/s
    this.maxSteer = options.maxSteer || 1.2;     // rad/s
    this.onChange = options.onChange || null;

    this.width = this.canvas.width = 180;
    this.height = this.canvas.height = 180;
    this.centerX = this.width / 2;
    this.centerY = this.height / 2;
    this.baseRadius = 68;
    this.handleRadius = 24;

    this.handleX = this.centerX;
    this.handleY = this.centerY;
    this.isActive = false;
    this.deadmanActive = false;

    // Keyboard state
    this.keys = { KeyW: false, KeyS: false, KeyA: false, KeyD: false, ArrowUp: false, ArrowDown: false, ArrowLeft: false, ArrowRight: false };

    this.bindEvents();
    this.bindKeyboard();
    this.draw();
  }

  setDeadman(active) {
    this.deadmanActive = active;
    if (!active) {
      // Immediate stop when deadman is released
      this.handleX = this.centerX;
      this.handleY = this.centerY;
      if (this.onChange) this.onChange(0.0, 0.0);
    }
    this.draw();
  }

  setMaxSpeed(speed) {
    this.maxSpeed = Number(speed);
  }

  bindEvents() {
    const onStart = (e) => {
      this.isActive = true;
      this.handleMove(e);
    };

    const onMove = (e) => {
      if (!this.isActive) return;
      this.handleMove(e);
    };

    const onEnd = () => {
      if (!this.isActive) return;
      this.isActive = false;
      this.handleX = this.centerX;
      this.handleY = this.centerY;
      this.draw();
      if (this.onChange) {
        this.onChange(0.0, 0.0);
      }
    };

    // Mouse Events
    this.canvas.addEventListener('mousedown', onStart);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);

    // Touch Events
    this.canvas.addEventListener('touchstart', (e) => {
      e.preventDefault();
      onStart(e.touches[0]);
    }, { passive: false });

    window.addEventListener('touchmove', (e) => {
      if (!this.isActive) return;
      onMove(e.touches[0]);
    }, { passive: false });

    window.addEventListener('touchend', onEnd);
  }

  handleMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX || e.pageX) - rect.left;
    const y = (e.clientY || e.pageY) - rect.top;

    let dx = x - this.centerX;
    let dy = y - this.centerY;
    const dist = Math.hypot(dx, dy);

    if (dist > this.baseRadius) {
      dx = (dx / dist) * this.baseRadius;
      dy = (dy / dist) * this.baseRadius;
    }

    this.handleX = this.centerX + dx;
    this.handleY = this.centerY + dy;
    this.draw();

    // If deadman is not held, do not transmit velocity commands
    if (!this.deadmanActive) {
      if (this.onChange) this.onChange(0.0, 0.0);
      return;
    }

    const normX = dx / this.baseRadius;
    const normY = -dy / this.baseRadius;

    // Y -> Linear speed (Forward/Reverse)
    // X -> Angular steering velocity
    const linear = Number((normY * this.maxSpeed).toFixed(3));
    const angular = Number((-normX * this.maxSteer).toFixed(3));

    if (this.onChange) {
      this.onChange(linear, angular);
    }
  }

  bindKeyboard() {
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code in this.keys) {
        this.keys[e.code] = true;
        this.updateKeyboardSpeed();
      }
    });

    window.addEventListener('keyup', (e) => {
      if (e.code in this.keys) {
        this.keys[e.code] = false;
        this.updateKeyboardSpeed();
      }
    });
  }

  updateKeyboardSpeed() {
    let forward = 0;
    let turn = 0;

    if (this.keys.KeyW || this.keys.ArrowUp) forward += 1;
    if (this.keys.KeyS || this.keys.ArrowDown) forward -= 1;
    if (this.keys.KeyA || this.keys.ArrowLeft) turn += 1;
    if (this.keys.KeyD || this.keys.ArrowRight) turn -= 1;

    const linear = forward * this.maxSpeed;
    const angular = turn * this.maxSteer;

    if (forward !== 0 || turn !== 0) {
      this.handleX = this.centerX - turn * this.baseRadius * 0.6;
      this.handleY = this.centerY - forward * this.baseRadius * 0.6;
      this.draw();

      if (this.deadmanActive && this.onChange) {
        this.onChange(linear, angular);
      }
    } else if (!this.isActive) {
      this.handleX = this.centerX;
      this.handleY = this.centerY;
      this.draw();
      if (this.onChange) this.onChange(0.0, 0.0);
    }
  }

  draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    // 1. Industrial Machined Outer Base
    ctx.beginPath();
    ctx.arc(this.centerX, this.centerY, this.baseRadius, 0, Math.PI * 2);
    ctx.fillStyle = '#111827';
    ctx.fill();
    ctx.strokeStyle = this.deadmanActive ? '#3b82f6' : '#27354a';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 2. Degree Angle Marks on Dial
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    for (let deg = 0; deg < 360; deg += 30) {
      const rad = (deg * Math.PI) / 180;
      const isMajor = deg % 90 === 0;
      const r1 = this.baseRadius - (isMajor ? 8 : 4);
      const r2 = this.baseRadius - 1;

      ctx.beginPath();
      ctx.moveTo(this.centerX + Math.cos(rad) * r1, this.centerY + Math.sin(rad) * r1);
      ctx.lineTo(this.centerX + Math.cos(rad) * r2, this.centerY + Math.sin(rad) * r2);
      ctx.stroke();
    }

    // 3. Center Crosshair
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(this.centerX - this.baseRadius + 12, this.centerY);
    ctx.lineTo(this.centerX + this.baseRadius - 12, this.centerY);
    ctx.moveTo(this.centerX, this.centerY - this.baseRadius + 12);
    ctx.lineTo(this.centerX, this.centerY + this.baseRadius - 12);
    ctx.stroke();

    // 4. Deflection Vector Line
    if (this.handleX !== this.centerX || this.handleY !== this.centerY) {
      ctx.beginPath();
      ctx.moveTo(this.centerX, this.centerY);
      ctx.lineTo(this.handleX, this.handleY);
      ctx.strokeStyle = this.deadmanActive ? '#3b82f6' : '#64748b';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // 5. Heavy-Duty Machined Jog Knob
    ctx.beginPath();
    ctx.arc(this.handleX, this.handleY, this.handleRadius, 0, Math.PI * 2);
    ctx.fillStyle = '#1e293b';
    ctx.fill();
    ctx.strokeStyle = this.deadmanActive ? (this.isActive ? '#60a5fa' : '#3b82f6') : '#475569';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Knob Grip Indent
    ctx.beginPath();
    ctx.arc(this.handleX, this.handleY, 7, 0, Math.PI * 2);
    ctx.fillStyle = this.deadmanActive ? (this.isActive ? '#2563eb' : '#334155') : '#1e293b';
    ctx.fill();
  }
}

window.VirtualJoystick = VirtualJoystick;
