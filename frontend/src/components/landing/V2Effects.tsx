"use client";

import { useEffect, useMemo, useRef, type RefObject } from "react";

function useBodyClass(className: string) {
  useEffect(() => {
    document.body.classList.add(className);
    return () => document.body.classList.remove(className);
  }, [className]);
}

function useCustomCursor() {
  const cursorRef = useRef<HTMLDivElement | null>(null);
  const ringRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const cur = cursorRef.current;
    const ring = ringRef.current;
    if (!cur || !ring) return;

    let mx = 0;
    let my = 0;
    let rx = 0;
    let ry = 0;
    let raf = 0;

    const onMove = (e: MouseEvent) => {
      mx = e.clientX;
      my = e.clientY;
      cur.style.left = `${mx}px`;
      cur.style.top = `${my}px`;
    };

    const anim = () => {
      rx += (mx - rx) * 0.12;
      ry += (my - ry) * 0.12;
      ring.style.left = `${rx}px`;
      ring.style.top = `${ry}px`;
      raf = window.requestAnimationFrame(anim);
    };

    const setHover = (isHovering: boolean) => {
      cur.style.width = isHovering ? "16px" : "8px";
      cur.style.height = isHovering ? "16px" : "8px";
      ring.style.width = isHovering ? "48px" : "32px";
      ring.style.height = isHovering ? "48px" : "32px";
      ring.style.opacity = isHovering ? "0.4" : "1";
    };

    const onOver = (e: MouseEvent) => {
      const t = e.target as Element | null;
      if (!t) return;
      const interactive = t.closest("button,a,.sugg-card,.src");
      setHover(Boolean(interactive));
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseover", onOver, { passive: true });
    anim();

    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseover", onOver);
      window.cancelAnimationFrame(raf);
    };
  }, []);

  return { cursorRef, ringRef };
}

function useCanvasStars(canvasRef: RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let W = 0;
    let H = 0;
    let raf = 0;
    let stars: {
      x: number;
      y: number;
      r: number;
      vx: number;
      vy: number;
      alpha: number;
    }[] = [];

    const resize = () => {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };

    const initStars = () => {
      stars = [];
      const n = Math.floor((W * H) / 10000);
      for (let i = 0; i < n; i++) {
        stars.push({
          x: Math.random() * W,
          y: Math.random() * H,
          r: Math.random() * 0.8 + 0.2,
          vx: (Math.random() - 0.5) * 0.12,
          vy: (Math.random() - 0.5) * 0.12,
          alpha: Math.random() * 0.5 + 0.1,
        });
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      for (const s of stars) {
        s.x += s.vx;
        s.y += s.vy;
        if (s.x < 0) s.x = W;
        if (s.x > W) s.x = 0;
        if (s.y < 0) s.y = H;
        if (s.y > H) s.y = 0;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(200,190,255,${s.alpha})`;
        ctx.fill();
      }

      for (let i = 0; i < stars.length; i++) {
        for (let j = i + 1; j < stars.length; j++) {
          const dx = stars[i].x - stars[j].x;
          const dy = stars[i].y - stars[j].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < 100) {
            ctx.beginPath();
            ctx.moveTo(stars[i].x, stars[i].y);
            ctx.lineTo(stars[j].x, stars[j].y);
            ctx.strokeStyle = `rgba(139,124,248,${0.05 * (1 - d / 100)})`;
            ctx.lineWidth = 0.4;
            ctx.stroke();
          }
        }
      }

      raf = window.requestAnimationFrame(draw);
    };

    resize();
    initStars();
    draw();

    const onResize = () => {
      resize();
      initStars();
    };
    window.addEventListener("resize", onResize, { passive: true });

    return () => {
      window.removeEventListener("resize", onResize);
      window.cancelAnimationFrame(raf);
    };
  }, [canvasRef]);
}

export function V2Effects() {
  useBodyClass("sift-v2");

  const { cursorRef, ringRef } = useCustomCursor();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useCanvasStars(canvasRef);

  // Duplicate topics list exactly as in sift-v2.html
  const marqueeItems = useMemo(() => {
    const topics = [
      "Quantum Computing",
      "Machine Learning",
      "Climate Science",
      "Genomics",
      "Astrophysics",
      "Materials Science",
      "Neuroscience",
      "Cryptography",
      "Protein Folding",
      "Dark Matter",
      "CRISPR",
      "Large Language Models",
      "Fusion Energy",
      "Nanotechnology",
    ];
    return [...topics, ...topics, ...topics, ...topics];
  }, []);

  return (
    <>
      <div id="cursor" ref={cursorRef} />
      <div id="cursor-ring" ref={ringRef} />

      <div className="grain" />
      <canvas id="bgCanvas" ref={canvasRef} />

      <div className="marquee-wrap" aria-hidden="true">
        <div className="marquee-track">
          {marqueeItems.map((t, idx) => (
            <span className="marquee-item" key={`${t}-${idx}`}>
              <span>✦</span>
              {t}
            </span>
          ))}
        </div>
      </div>
    </>
  );
}

