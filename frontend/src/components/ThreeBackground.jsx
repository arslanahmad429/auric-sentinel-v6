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

    // 3D Sphere parameters
    const pointsCount = 180;
    const sphereRadius = Math.min(width, height) * 0.28;
    const points = [];
    
    // Generate points on a sphere using Fibonacci lattice for even distribution
    for (let i = 0; i < pointsCount; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / pointsCount);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      
      points.push({
        x: Math.cos(theta) * Math.sin(phi) * sphereRadius,
        y: Math.sin(theta) * Math.sin(phi) * sphereRadius,
        z: Math.cos(phi) * sphereRadius,
        color: i % 2 === 0 ? 'rgba(0, 240, 255, 0.7)' : 'rgba(197, 168, 128, 0.7)' // Cyan and Gold
      });
    }

    let rotX = 0.002;
    let rotY = 0.003;
    let targetRotX = 0.002;
    let targetRotY = 0.003;
    
    let mouse = { x: 0, y: 0, isDown: false, lastX: 0, lastY: 0 };
    let scrollOffset = 0;
    let currentScroll = window.scrollY;

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e) => {
      if (mouse.isDown) {
        const deltaX = e.clientX - mouse.lastX;
        const deltaY = e.clientY - mouse.lastY;
        targetRotY += deltaX * 0.005;
        targetRotX += deltaY * 0.005;
      }
      mouse.lastX = e.clientX;
      mouse.lastY = e.clientY;
      
      // Gentle shift in globe center based on hover position
      mouse.x = (e.clientX - width / 2) * 0.05;
      mouse.y = (e.clientY - height / 2) * 0.05;
    };

    const handleMouseDown = (e) => {
      mouse.isDown = true;
      mouse.lastX = e.clientX;
      mouse.lastY = e.clientY;
    };

    const handleMouseUp = () => {
      mouse.isDown = false;
    };

    const handleScroll = () => {
      const newScroll = window.scrollY;
      scrollOffset += (newScroll - currentScroll) * 0.1;
      currentScroll = newScroll;
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('scroll', handleScroll);

    // Animation Loop
    const animate = () => {
      ctx.fillStyle = '#05070e'; // Luxurious deep slate background
      ctx.fillRect(0, 0, width, height);

      // Dampen rotation inertia
      rotX += (targetRotX - rotX) * 0.08;
      rotY += (targetRotY - rotY) * 0.08;
      
      // Auto rotation drift
      targetRotY += 0.001;
      targetRotX *= 0.98; // Decay vertical rotation to default

      scrollOffset *= 0.92; // Decay scroll velocity

      // Global coordinates shift
      const centerX = width / 2 + mouse.x;
      const centerY = height / 2 + mouse.y + scrollOffset;

      const fov = 500;
      const projected = [];

      // Rotate and project points
      points.forEach((p) => {
        // Rotate around Y axis
        let x1 = p.x * Math.cos(rotY) - p.z * Math.sin(rotY);
        let z1 = p.x * Math.sin(rotY) + p.z * Math.cos(rotY);

        // Rotate around X axis
        let y2 = p.y * Math.cos(rotX) - z1 * Math.sin(rotX);
        let z2 = p.y * Math.sin(rotX) + z1 * Math.cos(rotX);

        // Perspective scaling
        const scale = fov / (fov + z2 + 100);
        const projX = x1 * scale + centerX;
        const projY = y2 * scale + centerY;

        projected.push({
          x: projX,
          y: projY,
          z: z2,
          color: p.color,
          scale: scale
        });
      });

      // Draw connections (edges) first to keep them behind points
      ctx.lineWidth = 0.5;
      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const dx = projected[i].x - projected[j].x;
          const dy = projected[i].y - projected[j].y;
          const dist = Math.hypot(dx, dy);

          // Only draw connection if points are close and not on far backside
          if (dist < sphereRadius * 0.45 && projected[i].z < 100 && projected[j].z < 100) {
            const alpha = Math.max(0, (1 - dist / (sphereRadius * 0.45)) * 0.12);
            ctx.strokeStyle = `rgba(32, 45, 83, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(projected[i].x, projected[i].y);
            ctx.lineTo(projected[j].x, projected[j].y);
            ctx.stroke();
          }
        }
      }

      // Sort points by depth (Z-index) to draw front ones over back ones
      projected.sort((a, b) => b.z - a.z);

      // Draw projected points
      projected.forEach((p) => {
        const radius = Math.max(0.5, p.scale * 2.5);
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        
        // Dynamic opacity based on depth (front is brighter)
        const depthOpacity = Math.max(0.1, Math.min(1.0, (sphereRadius - p.z) / (sphereRadius * 1.5)));
        ctx.fillStyle = p.color;
        ctx.globalAlpha = depthOpacity * 0.75;
        ctx.fill();
        
        // Add soft glow around front points
        if (p.z < 0) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, radius * 2.5, 0, Math.PI * 2);
          ctx.fillStyle = p.color === 'rgba(0, 240, 255, 0.7)' ? 'rgba(0, 240, 255, 0.12)' : 'rgba(197, 168, 128, 0.12)';
          ctx.fill();
        }
      });
      ctx.globalAlpha = 1.0;

      // Draw subtle futuristic geometric ring around the globe
      ctx.strokeStyle = 'rgba(197, 168, 128, 0.04)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, sphereRadius * 1.25, sphereRadius * 0.25, Math.PI / 6, 0, Math.PI * 2);
      ctx.stroke();

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return <canvas ref={canvasRef} className="fixed top-0 left-0 w-full h-full -z-10 block pointer-events-none cursor-grab active:cursor-grabbing" />;
};

export default ThreeBackground;
