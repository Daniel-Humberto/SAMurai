"use client";

import React, { useRef, useEffect, useState } from "react";

interface Agent {
  id: string;
  name: string;
  role: string;
  team: "yellow" | "blue" | "ball";
  x: number; // Pitch coords [-50 to 50]
  y: number; // Pitch coords [-35 to 35]
  vx: number;
  vy: number;
  battery: number;
  temp: number;
  status: string;
  history: { x: number; y: number }[];
}

export function ExoticFieldExperience() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // React State for details panel (only updates when a DIFFERENT agent is focused)
  const [activeAgent, setActiveAgent] = useState<Agent | null>(null);
  const [metrics, setMetrics] = useState({ fps: 60, latency: 12, quality: 99.2 });

  // Refs to store mouse positions and active agents for the 60fps render loop
  const mousePosRef = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const activeAgentRef = useRef<Agent | null>(null);

  // Initialize agents
  const agentsRef = useRef<Agent[]>([
    { id: "Y-1", name: "SAM-Y1", role: "Stryker", team: "yellow", x: -25, y: -5, vx: 0.1, vy: 0.05, battery: 94, temp: 36.5, status: "ATACANDO", history: [] },
    { id: "Y-2", name: "SAM-Y2", role: "Midfield", team: "yellow", x: -10, y: 15, vx: -0.05, vy: -0.08, battery: 89, temp: 38.2, status: "COBERTURA", history: [] },
    { id: "Y-3", name: "SAM-Y3", role: "Goalkeeper", team: "yellow", x: -45, y: 0, vx: 0, vy: 0.03, battery: 98, temp: 34.1, status: "BLOQUEADO", history: [] },
    { id: "B-1", name: "BOT-B1", role: "Stryker", team: "blue", x: 20, y: 5, vx: -0.12, vy: 0.07, battery: 91, temp: 37.8, status: "PRESIONANDO", history: [] },
    { id: "B-2", name: "BOT-B2", role: "Defender", team: "blue", x: 35, y: -15, vx: 0.04, vy: -0.02, battery: 87, temp: 39.0, status: "MARCAJE", history: [] },
    { id: "B-3", name: "BOT-B3", role: "Goalkeeper", team: "blue", x: 45, y: 0, vx: 0, vy: -0.02, battery: 95, temp: 35.5, status: "POSICIONADO", history: [] },
    { id: "BALL", name: "FutBall", role: "Target", team: "ball", x: 0, y: 0, vx: 0.25, vy: 0.15, battery: 100, temp: 24.0, status: "EN_JUEGO", history: [] },
  ]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let scanLineProgress = 0;
    let lastTime = performance.now();
    let frameCount = 0;
    let fpsTimer = 0;

    // Handle high-DPI sizing (Only fires on window resize and initial load!)
    const resizeCanvas = () => {
      const parent = containerRef.current;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.scale(dpr, dpr);
    };

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Dynamic log generator for cyberpunk overlay
    const logs: string[] = [
      "SYSTEM RUNNING: OK",
      "SAM2.1 SEGMENTATION: ACTIVA",
      "BYTETRACKING: PERSISTENTE",
      "HOMOGRAFIA: CALIBRADA",
    ];

    const runLoop = (time: number) => {
      const delta = time - lastTime;
      lastTime = time;

      // FPS Calculation
      frameCount++;
      fpsTimer += delta;
      if (fpsTimer >= 1000) {
        setMetrics((prev) => ({
          ...prev,
          fps: frameCount,
          latency: Math.floor(10 + Math.random() * 5),
          quality: +(98.5 + Math.random() * 1.2).toFixed(1),
        }));
        frameCount = 0;
        fpsTimer = 0;
      }

      // Update scan line
      scanLineProgress += 0.003;
      if (scanLineProgress > 1) scanLineProgress = 0;

      // Update positions
      const agents = agentsRef.current;
      const ball = agents.find((a) => a.team === "ball")!;

      // Physics/Behavior simulation (agents chase ball lightly or defend)
      agents.forEach((agent) => {
        if (agent.team === "ball") {
          // Ball physics & boundary checks
          agent.x += agent.vx;
          agent.y += agent.vy;

          if (agent.x > 48 || agent.x < -48) {
            agent.vx *= -1;
            agent.x = Math.max(-48, Math.min(48, agent.x));
          }
          if (agent.y > 33 || agent.y < -33) {
            agent.vy *= -1;
            agent.y = Math.max(-33, Math.min(33, agent.y));
          }

          // Friction or random kick
          if (Math.random() < 0.015) {
            agent.vx = (Math.random() - 0.5) * 0.8;
            agent.vy = (Math.random() - 0.5) * 0.6;
          }
        } else {
          // Robots move around and react to ball
          const dx = ball.x - agent.x;
          const dy = ball.y - agent.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (agent.role === "Goalkeeper") {
            // Keep near goal, track ball y-axis
            const targetY = Math.max(-10, Math.min(10, ball.y));
            agent.y += (targetY - agent.y) * 0.04;
          } else {
            // Move towards ball or position
            if (dist < 20 && agent.team === "yellow") {
              // Intercept ball
              agent.vx += (dx / dist) * 0.01;
              agent.vy += (dy / dist) * 0.01;
            } else if (dist < 20 && agent.team === "blue") {
              // Block path
              agent.vx += (dx / dist - agent.vx) * 0.015;
              agent.vy += (dy / dist - agent.vy) * 0.015;
            } else {
              // Rest positioning
              const restX = agent.id.includes("1") ? 15 : 30;
              const sideFactor = agent.team === "yellow" ? -1 : 1;
              agent.vx += (restX * sideFactor - agent.x) * 0.002;
              agent.vy += (0 - agent.y) * 0.002;
            }

            // Cap speeds
            const speed = Math.sqrt(agent.vx * agent.vx + agent.vy * agent.vy);
            const maxSpeed = 0.25;
            if (speed > maxSpeed) {
              agent.vx = (agent.vx / speed) * maxSpeed;
              agent.vy = (agent.vy / speed) * maxSpeed;
            }

            agent.x += agent.vx;
            agent.y += agent.vy;
          }
        }

        // Add history trails
        agent.history.push({ x: agent.x, y: agent.y });
        if (agent.history.length > 28) agent.history.shift();
      });

      // Clear canvas
      const w = canvas.width / (window.devicePixelRatio || 1);
      const h = canvas.height / (window.devicePixelRatio || 1);
      ctx.clearRect(0, 0, w, h);

      // Rendering setup
      const cx = w / 2;
      const cy = h / 2 + 15;
      
      // Perspective projection parameters
      const scaleX = w * 0.0075;
      const scaleY = h * 0.0078;
      const tilt = 0.58;
      const theta = -0.15; // Rotate angle slightly for exotic 3D look

      const project = (px: number, py: number) => {
        // Apply rotation
        const rx = px * Math.cos(theta) - py * Math.sin(theta);
        const ry = px * Math.sin(theta) + py * Math.cos(theta);
        // Apply perspective tilt
        const sx = cx + rx * scaleX;
        const sy = cy + ry * scaleY * tilt;
        return { x: sx, y: sy };
      };

      // Draw background grid
      ctx.strokeStyle = "rgba(30, 41, 59, 0.4)";
      ctx.lineWidth = 1;
      for (let gX = -60; gX <= 60; gX += 10) {
        ctx.beginPath();
        const start = project(gX, -40);
        const end = project(gX, 40);
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }
      for (let gY = -40; gY <= 40; gY += 10) {
        ctx.beginPath();
        const start = project(-60, gY);
        const end = project(60, gY);
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }

      // Draw Soccer Pitch Lines (glowing emerald/cyan)
      ctx.strokeStyle = "rgba(34, 211, 238, 0.28)";
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 10;
      ctx.shadowColor = "rgba(34, 211, 238, 0.35)";

      // Touchlines
      ctx.beginPath();
      const tl1 = project(-50, -35);
      const tl2 = project(50, -35);
      const tl3 = project(50, 35);
      const tl4 = project(-50, 35);
      ctx.moveTo(tl1.x, tl1.y);
      ctx.lineTo(tl2.x, tl2.y);
      ctx.lineTo(tl3.x, tl3.y);
      ctx.lineTo(tl4.x, tl4.y);
      ctx.closePath();
      ctx.stroke();

      // Half-way line
      ctx.beginPath();
      const hw1 = project(0, -35);
      const hw2 = project(0, 35);
      ctx.moveTo(hw1.x, hw1.y);
      ctx.lineTo(hw2.x, hw2.y);
      ctx.stroke();

      // Center Circle
      ctx.beginPath();
      const segments = 32;
      for (let i = 0; i <= segments; i++) {
        const angle = (i / segments) * Math.PI * 2;
        const rad = 10;
        const pt = project(Math.cos(angle) * rad, Math.sin(angle) * rad);
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.stroke();

      // Penalty Area Left
      ctx.beginPath();
      const paL1 = project(-50, -18);
      const paL2 = project(-35, -18);
      const paL3 = project(-35, 18);
      const paL4 = project(-50, 18);
      ctx.moveTo(paL1.x, paL1.y);
      ctx.lineTo(paL2.x, paL2.y);
      ctx.lineTo(paL3.x, paL3.y);
      ctx.lineTo(paL4.x, paL4.y);
      ctx.stroke();

      // Penalty Area Right
      ctx.beginPath();
      const paR1 = project(50, -18);
      const paR2 = project(35, -18);
      const paR3 = project(35, 18);
      const paR4 = project(50, 18);
      ctx.moveTo(paR1.x, paR1.y);
      ctx.lineTo(paR2.x, paR2.y);
      ctx.lineTo(paR3.x, paR3.y);
      ctx.lineTo(paR4.x, paR4.y);
      ctx.stroke();

      // Goals
      ctx.strokeStyle = "rgba(251, 191, 36, 0.4)";
      ctx.beginPath();
      const gL1 = project(-50, -7);
      const gL2 = project(-53, -7);
      const gL3 = project(-53, 7);
      const gL4 = project(-50, 7);
      ctx.moveTo(gL1.x, gL1.y);
      ctx.lineTo(gL2.x, gL2.y);
      ctx.lineTo(gL3.x, gL3.y);
      ctx.lineTo(gL4.x, gL4.y);
      ctx.stroke();

      ctx.beginPath();
      const gR1 = project(50, -7);
      const gR2 = project(53, -7);
      const gR3 = project(53, 7);
      const gR4 = project(50, 7);
      ctx.moveTo(gR1.x, gR1.y);
      ctx.lineTo(gR2.x, gR2.y);
      ctx.lineTo(gR3.x, gR3.y);
      ctx.lineTo(gR4.x, gR4.y);
      ctx.stroke();

      ctx.shadowBlur = 0; // Reset shadow

      // Draw Sweep Laser Line (Exotic Scanning Effect)
      const sweepX = -50 + scanLineProgress * 100;
      ctx.fillStyle = "rgba(34, 211, 238, 0.04)";
      ctx.beginPath();
      const laser1 = project(sweepX - 4, -35);
      const laser2 = project(sweepX, -35);
      const laser3 = project(sweepX, 35);
      const laser4 = project(sweepX - 4, 35);
      ctx.moveTo(laser1.x, laser1.y);
      ctx.lineTo(laser2.x, laser2.y);
      ctx.lineTo(laser3.x, laser3.y);
      ctx.lineTo(laser4.x, laser4.y);
      ctx.fill();

      // Bright leading edge
      ctx.strokeStyle = "rgba(34, 211, 238, 0.6)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      const edgeTop = project(sweepX, -35);
      const edgeBot = project(sweepX, 35);
      ctx.moveTo(edgeTop.x, edgeTop.y);
      ctx.lineTo(edgeBot.x, edgeBot.y);
      ctx.stroke();

      // Find nearest agent to mouse for HUD overlay
      let nearestAgent: Agent | null = null;
      let minDistance = Infinity;

      const currentMousePos = mousePosRef.current;
      if (currentMousePos) {
        for (const agent of agents) {
          const pt = project(agent.x, agent.y);
          const dx = currentMousePos.x - pt.x;
          const dy = currentMousePos.y - pt.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < minDistance && dist < 32) {
            minDistance = dist;
            nearestAgent = agent;
          }
        }
      }

      // Check if active agent selection changed, and update state/ref
      if (nearestAgent?.id !== activeAgentRef.current?.id) {
        activeAgentRef.current = nearestAgent;
        setActiveAgent(nearestAgent);
      }

      // Render Agents
      agents.forEach((agent) => {
        const pt = project(agent.x, agent.y);

        // Draw Trails
        if (agent.history.length > 1) {
          ctx.beginPath();
          const startPt = project(agent.history[0].x, agent.history[0].y);
          ctx.moveTo(startPt.x, startPt.y);
          for (let i = 1; i < agent.history.length; i++) {
            const histPt = project(agent.history[i].x, agent.history[i].y);
            ctx.lineTo(histPt.x, histPt.y);
          }
          ctx.lineWidth = 1.5;
          if (agent.team === "yellow") ctx.strokeStyle = `rgba(245, 158, 11, 0.12)`;
          else if (agent.team === "blue") ctx.strokeStyle = `rgba(34, 211, 238, 0.12)`;
          else ctx.strokeStyle = `rgba(244, 63, 94, 0.15)`;
          ctx.stroke();
        }

        // Draw node
        ctx.beginPath();
        let color = "";
        let glowColor = "";
        if (agent.team === "yellow") {
          color = "#fbbf24";
          glowColor = "rgba(251, 191, 36, 0.5)";
        } else if (agent.team === "blue") {
          color = "#22d3ee";
          glowColor = "rgba(34, 211, 238, 0.5)";
        } else {
          color = "#f43f5e";
          glowColor = "rgba(244, 63, 94, 0.6)";
        }

        const radius = agent.team === "ball" ? 4.5 : 7;
        ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.shadowBlur = 12;
        ctx.shadowColor = glowColor;
        ctx.fill();
        ctx.shadowBlur = 0; // reset

        // Draw halo ring on hover or scan intersect
        const dxToLaser = Math.abs(agent.x - sweepX);
        const isSelected = activeAgentRef.current?.id === agent.id;
        
        if (isSelected || dxToLaser < 3) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          const ringRad = radius + (dxToLaser < 3 ? 6 - dxToLaser : 5 + Math.sin(time * 0.01) * 2);
          ctx.arc(pt.x, pt.y, ringRad, 0, Math.PI * 2);
          ctx.stroke();
          
          if (isSelected && agent.team !== "ball") {
            // Target lock ticks
            ctx.beginPath();
            ctx.moveTo(pt.x - 12, pt.y);
            ctx.lineTo(pt.x - 7, pt.y);
            ctx.moveTo(pt.x + 12, pt.y);
            ctx.lineTo(pt.x + 7, pt.y);
            ctx.moveTo(pt.x, pt.y - 12);
            ctx.lineTo(pt.x, pt.y - 7);
            ctx.moveTo(pt.x, pt.y + 12);
            ctx.lineTo(pt.x, pt.y + 7);
            ctx.stroke();
          }
        }

        // Draw tiny label
        if (agent.team !== "ball") {
          ctx.fillStyle = "#ffffff";
          ctx.font = "8px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(agent.id, pt.x, pt.y - 12);
        }
      });

      // Render Ball Prediction Path
      if (ball.history.length > 0) {
        ctx.strokeStyle = "rgba(244, 63, 94, 0.35)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        const ballPt = project(ball.x, ball.y);
        ctx.moveTo(ballPt.x, ballPt.y);
        // Draw ahead into future
        const fut1 = project(ball.x + ball.vx * 12, ball.y + ball.vy * 12);
        const fut2 = project(ball.x + ball.vx * 24 + 2, ball.y + ball.vy * 24 - 1);
        ctx.quadraticCurveTo(fut1.x, fut1.y, fut2.x, fut2.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Draw mouse scanning coordinates crosshair
      if (currentMousePos) {
        ctx.strokeStyle = "rgba(148, 163, 184, 0.15)";
        ctx.lineWidth = 0.8;
        // Horizontal scanline
        ctx.beginPath();
        ctx.moveTo(0, currentMousePos.y);
        ctx.lineTo(w, currentMousePos.y);
        ctx.stroke();
        // Vertical scanline
        ctx.beginPath();
        ctx.moveTo(currentMousePos.x, 0);
        ctx.lineTo(currentMousePos.x, h);
        ctx.stroke();

        // If hovered agent is selected, draw vector line from cursor to it
        const selectedAgent = activeAgentRef.current;
        if (selectedAgent) {
          const pt = project(selectedAgent.x, selectedAgent.y);
          ctx.strokeStyle = selectedAgent.team === "yellow" ? "rgba(251, 191, 36, 0.4)" : "rgba(34, 211, 238, 0.4)";
          ctx.lineWidth = 1;
          ctx.setLineDash([2, 4]);
          ctx.beginPath();
          ctx.moveTo(currentMousePos.x, currentMousePos.y);
          ctx.lineTo(pt.x, pt.y);
          ctx.stroke();
          ctx.setLineDash([]);

          // Draw floating range tooltip in canvas
          const dist = Math.sqrt((currentMousePos.px - selectedAgent.x) ** 2 + (currentMousePos.py - selectedAgent.y) ** 2);
          ctx.fillStyle = "rgba(2, 6, 23, 0.85)";
          ctx.fillRect(currentMousePos.x + 10, currentMousePos.y - 30, 95, 20);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
          ctx.strokeRect(currentMousePos.x + 10, currentMousePos.y - 30, 95, 20);
          
          ctx.fillStyle = "#ffffff";
          ctx.font = "8.5px Courier New, monospace";
          ctx.textAlign = "left";
          ctx.fillText(`DIST: ${dist.toFixed(1)}m | LOC`, currentMousePos.x + 15, currentMousePos.y - 17);
        }
      }

      // HUD Decorations
      // Calibration square corners
      ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
      ctx.lineWidth = 1;
      const margin = 10;
      // Top-Left
      ctx.beginPath(); ctx.moveTo(margin, margin + 10); ctx.lineTo(margin, margin); ctx.lineTo(margin + 10, margin); ctx.stroke();
      // Top-Right
      ctx.beginPath(); ctx.moveTo(w - margin, margin + 10); ctx.lineTo(w - margin, margin); ctx.lineTo(w - margin - 10, margin); ctx.stroke();
      // Bottom-Left
      ctx.beginPath(); ctx.moveTo(margin, h - margin - 10); ctx.lineTo(margin, h - margin); ctx.lineTo(margin + 10, h - margin); ctx.stroke();
      // Bottom-Right
      ctx.beginPath(); ctx.moveTo(w - margin, h - margin - 10); ctx.lineTo(w - margin, h - margin); ctx.lineTo(w - margin - 10, h - margin); ctx.stroke();

      // Telemetry panel - drawing textual telemetry logs directly on canvas
      ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
      ctx.font = "7.5px Courier New, monospace";
      ctx.textAlign = "left";
      logs.forEach((log, i) => {
        ctx.fillText(`>> ${log}`, 15, h - 50 + i * 10);
      });

      // Pitch coordinate telemetry at cursor
      if (currentMousePos) {
        ctx.fillStyle = "rgba(34, 211, 238, 0.7)";
        ctx.fillText(`DRONE_CAM_COORD: X=${currentMousePos.px.toFixed(2)} Y=${currentMousePos.py.toFixed(2)}`, w - 165, h - 15);
      }

      animationFrameId = requestAnimationFrame(runLoop);
    };

    animationFrameId = requestAnimationFrame(runLoop);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", resizeCanvas);
    };
  }, []); // Run ONCE on mount

  // Handle MouseMove on Canvas to capture local relative grid positions
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Inverse projection to find pitch coordinates (approximated for demo)
    const w = rect.width;
    const h = rect.height;
    const cx = w / 2;
    const cy = h / 2 + 15;
    const scaleX = w * 0.0075;
    const scaleY = h * 0.0078;
    const tilt = 0.58;
    const theta = -0.15;

    // Convert screen coords relative to center
    const dx = x - cx;
    const dy = (y - cy) / (tilt * scaleY);
    
    // Reverse rotation
    const rx = dx / scaleX;
    const ry = dy;
    const px = rx * Math.cos(-theta) - ry * Math.sin(-theta);
    const py = rx * Math.sin(-theta) + ry * Math.cos(-theta);

    mousePosRef.current = { x, y, px, py };
  };

  const handleMouseLeave = () => {
    mousePosRef.current = null;
    activeAgentRef.current = null;
    setActiveAgent(null);
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[280px] sm:h-[320px] lg:h-[380px] rounded-[1.5rem] border border-white/5 bg-slate-950/40 backdrop-blur-sm overflow-hidden group shadow-[inset_0_2px_20px_rgba(0,0,0,0.8)]"
    >
      {/* Absolute background visual details */}
      <div className="absolute top-4 left-4 font-mono text-[9px] uppercase tracking-widest text-slate-400 select-none">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping mr-1.5" />
        RADAR DE SEGUIMIENTO EN VIVO
      </div>

      {/* Cyberpunk Ticker Info */}
      <div className="absolute top-4 right-4 font-mono text-[9.5px] text-right text-slate-400 space-y-1 select-none">
        <div className="text-cyan-300 font-bold uppercase tracking-wider">SAMurAI-CALIBRATOR v2.1</div>
        <div className="flex gap-2 justify-end text-[8.5px] text-slate-500">
          <span>FPS: <strong className="text-slate-300">{metrics.fps}</strong></span>
          <span>LAT: <strong className="text-slate-300">{metrics.latency}ms</strong></span>
          <span>CONF: <strong className="text-slate-300">{metrics.quality}%</strong></span>
        </div>
      </div>

      {/* Canvas for high performance drawing */}
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="block w-full h-full cursor-crosshair"
      />

      {/* Hover Information HUD Panel - HTML overlay for premium aesthetics */}
      <div className="absolute bottom-4 right-4 max-w-[200px] rounded-lg border border-white/10 bg-slate-950/90 p-3 shadow-xl backdrop-blur-md transition-all duration-300 pointer-events-none select-none opacity-90">
        <div className="text-[9px] uppercase tracking-wider text-slate-400">TELEMETRIA SELECCIONADA</div>
        {activeAgent ? (
          <div className="mt-2 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-bold ${activeAgent.team === "yellow" ? "text-amber-300" : activeAgent.team === "blue" ? "text-cyan-300" : "text-rose-400"}`}>
                {activeAgent.name}
              </span>
              <span className="text-[7.5px] px-1 rounded bg-slate-800 text-slate-300 font-mono">{activeAgent.role}</span>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[8.5px] font-mono text-slate-300 border-t border-white/5 pt-1.5">
              <div>SYS: <span className="text-emerald-400">OK</span></div>
              <div>BATERIA: <span className="text-slate-200">{activeAgent.battery}%</span></div>
              <div>TEMP: <span className="text-slate-200">{activeAgent.temp}°C</span></div>
              <div>ESTADO: <span className="text-amber-200">{activeAgent.status}</span></div>
            </div>
          </div>
        ) : (
          <div className="mt-2 text-[8.5px] leading-relaxed text-slate-500 font-mono">
            Pasa el cursor sobre los robots para fijar lock-on y capturar telemetría táctica en tiempo real.
          </div>
        )}
      </div>

      {/* Scan overlay text animation */}
      <div className="absolute bottom-4 left-4 font-mono text-[9px] text-slate-500 select-none">
        GRID: 10x8m | MODE: AUTO_TRACK
      </div>
    </div>
  );
}
