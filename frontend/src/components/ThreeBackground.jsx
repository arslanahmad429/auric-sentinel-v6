import React, { useEffect, useRef } from 'react';

const ThreeBackground = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Particles array
    const numParticles = 120;
    const particles = [];
    const mouse = { x: null, y: null, radius: 150 };

    class Particle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        // 3D Depth coordinate Z (1 to 1000)
        this.z = Math.random() * 1000 + 200; 
        this.size = Math.random() * 1.5 + 0.5;
        this.speedX = Math.random() * 0.4 - 0.2;
        this.speedY = Math.random() * 0.4 - 0.2;
        this.color = Math.random() > 0.5 ? '#00f0ff' : '#ff007f';
      }

      update(scrollVelocity) {
        // Move particle based on velocity
        this.x += this.speedX;
        this.y += this.speedY + scrollVelocity * 0.15; // responsive to scroll

        // 3D perspective projection calculations
        this.z -= 1.0; // Slowly zoom forward
        if (this.z <= 0) {
          this.reset();
        }

        // Mouse interaction (repulsion)
        if (mouse.x !== null && mouse.y !== null) {
          const dx = this.x - mouse.x;
          const dy = this.y - mouse.y;
          const distance = Math.hypot(dx, dy);
          if (distance < mouse.radius) {
            const force = (mouse.radius - distance) / mouse.radius;
            this.x += (dx / distance) * force * 3;
            this.y += (dy / distance) * force * 3;
          }
        }

        // Wrap boundaries
        if (this.x < 0 || this.x > width || this.y < 0 || this.y > height) {
          this.reset();
        }
      }

      draw() {
        // Calculate projected 3D size and position
        const fov = 300;
        const scale = fov / (fov + this.z);
        const projX = (this.x - width / 2) * scale + width / 2;
        const projY = (this.y - height / 2) * scale + height / 2;
        const projSize = this.size * scale * 3;

        ctx.beginPath();
        ctx.arc(projX, projY, projSize, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        // Fade out based on depth (Z)
        const opacity = (1000 - this.z) / 1000;
        ctx.globalAlpha = Math.max(0, Math.min(opacity, 0.7));
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }
    }

    // Populate particles
    for (let i = 0; i < numParticles; i++) {
      particles.push(new Particle());
    }

    let scrollY = window.scrollY;
    let scrollVelocity = 0;

    const handleScroll = () => {
      const currentScroll = window.scrollY;
      scrollVelocity = currentScroll - scrollY;
      scrollY = currentScroll;
    };

    const handleMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };

    const handleMouseLeave = () => {
      mouse.x = null;
      mouse.y = null;
    };

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('resize', handleResize);

    // Animation Loop
    const animate = () => {
      ctx.fillStyle = 'rgba(6, 9, 19, 0.2)'; // trail effect
      ctx.fillRect(0, 0, width, height);

      // Slowly decay scroll velocity back to 0
      scrollVelocity *= 0.95;

      particles.forEach((p) => {
        p.update(scrollVelocity);
        p.draw();
      });

      // Draw subtle grid mesh in background
      ctx.strokeStyle = 'rgba(32, 45, 83, 0.05)';
      ctx.lineWidth = 1;
      const gridSize = 60;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return <canvas ref={canvasRef} className="fixed top-0 left-0 w-full h-full -z-10 block pointer-events-none" />;
};

export default ThreeBackground;
