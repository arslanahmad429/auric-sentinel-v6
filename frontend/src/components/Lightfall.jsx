import React, { useEffect, useRef } from 'react';

const Lightfall = ({
  colors = ['#A6C8FF', '#5227FF', '#FF9FFC'],
  backgroundColor = '#0A29FF',
  speed = 0.5,
  streakCount = 2,
  streakWidth = 1,
  streakLength = 1,
  glow = 1,
  density = 0.6,
  twinkle = 1,
  zoom = 3,
  backgroundGlow = 0.5,
  opacity = 1,
  mouseInteraction = true,
  mouseStrength = 0.5,
  mouseRadius = 1,
  color1 = '#A6C8FF',
  color2 = '#5227FF',
  color3 = '#FF9FFC',
}) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId;
    const parent = canvas.parentElement || { clientWidth: window.innerWidth, clientHeight: window.innerHeight };
    let width = (canvas.width = parent.clientWidth || window.innerWidth);
    let height = (canvas.height = parent.clientHeight || window.innerHeight);

    // Streaks configuration
    const activeColors = colors && colors.length > 0 ? colors : [color1, color2, color3].filter(Boolean);
    const numStreaks = Math.floor(width * 0.05 * density * streakCount);
    const streaks = [];

    // Background stars configuration
    const numStars = Math.floor(width * 0.1 * twinkle);
    const stars = [];

    const mouse = { x: null, y: null, radius: 150 * mouseRadius };

    class Streak {
      constructor() {
        this.reset(true);
      }

      reset(init = false) {
        this.x = Math.random() * width;
        this.y = init ? Math.random() * height : -150 * streakLength;
        this.vy = (Math.random() * 4 + 3) * speed * zoom;
        this.vx = (Math.random() * 0.4 - 0.2) * speed;
        this.length = (Math.random() * 80 + 60) * streakLength;
        this.weight = (Math.random() * 1.5 + 0.5) * streakWidth;
        this.color = activeColors[Math.floor(Math.random() * activeColors.length)];
        this.alpha = Math.random() * 0.5 + 0.3;
      }

      update() {
        this.y += this.vy;
        this.x += this.vx;

        // Mouse interaction (drifting toward mouse or repelled slightly)
        if (mouseInteraction && mouse.x !== null && mouse.y !== null) {
          const dx = this.x - mouse.x;
          const dy = this.y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < mouse.radius) {
            const force = (mouse.radius - dist) / mouse.radius;
            this.x -= (dx / dist) * force * mouseStrength * 5;
          }
        }

        // Reset if out of bounds
        if (this.y > height + this.length || this.x < -50 || this.x > width + 50) {
          this.reset(false);
        }
      }

      draw() {
        ctx.save();
        ctx.globalAlpha = this.alpha * opacity;
        
        if (glow > 0) {
          ctx.shadowBlur = 10 * glow;
          ctx.shadowColor = this.color;
        }

        const grad = ctx.createLinearGradient(
          this.x - this.vx * this.length * 0.1, 
          this.y - this.length, 
          this.x, 
          this.y
        );
        grad.addColorStop(0, 'transparent');
        grad.addColorStop(0.7, this.color);
        grad.addColorStop(1, '#ffffff');

        ctx.strokeStyle = grad;
        ctx.lineWidth = this.weight;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(this.x - this.vx * this.length * 0.1, this.y - this.length);
        ctx.lineTo(this.x, this.y);
        ctx.stroke();
        ctx.restore();
      }
    }

    class Star {
      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.size = Math.random() * 1.2 + 0.2;
        this.alpha = Math.random();
        this.speed = (Math.random() * 0.02 + 0.01) * twinkle;
      }

      update() {
        this.alpha += this.speed;
        if (this.alpha > 1 || this.alpha < 0) {
          this.speed = -this.speed;
        }
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.globalAlpha = Math.max(0.1, this.alpha * opacity * 0.5);
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }
    }

    // Populate objects
    for (let i = 0; i < numStreaks; i++) {
      streaks.push(new Streak());
    }
    for (let i = 0; i < numStars; i++) {
      stars.push(new Star());
    }

    const handleResize = () => {
      const activeParent = canvas.parentElement || { clientWidth: window.innerWidth, clientHeight: window.innerHeight };
      width = canvas.width = activeParent.clientWidth || window.innerWidth;
      height = canvas.height = activeParent.clientHeight || window.innerHeight;
    };

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouse.x = null;
      mouse.y = null;
    };

    // Track events on window to support background canvas layering
    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    // Animation Loop
    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw background
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, width, height);

      // Draw soft colorized radial glow
      if (backgroundGlow > 0) {
        const glowX = mouse.x !== null ? mouse.x : width / 2;
        const glowY = mouse.y !== null ? mouse.y : height / 2;
        const radialGrad = ctx.createRadialGradient(
          glowX, 
          glowY, 
          0, 
          glowX, 
          glowY, 
          Math.max(width, height) * 0.4
        );
        radialGrad.addColorStop(0, `${color2}33`);
        radialGrad.addColorStop(0.5, `${color3}11`);
        radialGrad.addColorStop(1, 'transparent');
        
        ctx.fillStyle = radialGrad;
        ctx.fillRect(0, 0, width, height);
      }

      // Draw stars
      stars.forEach((star) => {
        star.update();
        star.draw();
      });

      // Draw streaks
      streaks.forEach((streak) => {
        streak.update();
        streak.draw();
      });

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [
    colors,
    backgroundColor,
    speed,
    streakCount,
    streakWidth,
    streakLength,
    glow,
    density,
    twinkle,
    zoom,
    backgroundGlow,
    opacity,
    mouseInteraction,
    mouseStrength,
    mouseRadius,
    color1,
    color2,
    color3,
  ]);

  return <canvas ref={canvasRef} className="absolute top-0 left-0 w-full h-full block pointer-events-none" />;
};

export default Lightfall;
