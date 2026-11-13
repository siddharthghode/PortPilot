#!/usr/bin/env python3
"""
PortPilot Showcase Image Generator
Generates a 1300x985 portfolio card showcase JPEG matching portfolio specifications:
- 1300x985 pixels
- JFIF 1.01 standard
- 96x96 DPI
- JPEG quality 75
- Comment: CREATOR: gd-jpeg v1.0 (using IJG JPEG v62), quality = 75
"""

import os
import subprocess
from pathlib import Path
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PORTFOLIO_DIR = Path("/home/archsid/git/portfolio")

def get_svg(filename: str, fill: str = None) -> str:
    path = PORTFOLIO_DIR / "src/Assets/TechIcons" / filename
    if not path.exists():
        return ""
    svg = path.read_text(encoding="utf-8").strip()
    if fill:
        if 'fill="' in svg[:100]:
            svg = svg.replace('fill="none"', f'fill="{fill}"', 1)
        else:
            svg = svg.replace('<svg ', f'<svg fill="{fill}" ', 1)
    return svg

def generate():
    python_svg = get_svg("Python.svg")
    linux_svg = get_svg("linux.svg")
    docker_svg = get_svg("Docker.svg")
    git_svg = get_svg("Git.svg")
    postgres_svg = get_svg("postgresql.svg", fill="#38bdf8")
    redis_svg = get_svg("redis.svg", fill="#f43f5e")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @font-face {{
    font-family: 'JetBrains Mono';
    src: local('JetBrainsMono Nerd Font'), local('JetBrains Mono');
  }}
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}
  body {{
    width: 1300px;
    height: 985px;
    background: #0b0914;
    background-image: 
      radial-gradient(circle at 18% 18%, rgba(147, 51, 234, 0.16) 0%, transparent 42%),
      radial-gradient(circle at 82% 82%, rgba(79, 70, 229, 0.14) 0%, transparent 45%),
      radial-gradient(circle at 50% 50%, rgba(192, 132, 252, 0.05) 0%, transparent 60%);
    color: #e2e8f0;
    font-family: 'Adwaita Sans', 'Liberation Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 24px 32px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
    position: relative;
  }}

  .bg-grid {{
    position: absolute;
    inset: 0;
    background-size: 36px 36px;
    background-image: 
      linear-gradient(to right, rgba(255, 255, 255, 0.018) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
    pointer-events: none;
    z-index: 0;
  }}

  .header-bar {{
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 2px 10px 14px 10px;
  }}
  .brand-left {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .brand-logo {{
    font-size: 27px;
    font-weight: 900;
    background: linear-gradient(135deg, #e879f9 0%, #c084fc 50%, #9333ea 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
    filter: drop-shadow(0 0 12px rgba(192, 132, 252, 0.45));
  }}
  .brand-divider {{
    color: #4b5563;
    font-size: 20px;
    font-weight: 300;
  }}
  .brand-title {{
    font-size: 13.5px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #94a3b8;
    text-transform: uppercase;
  }}
  .nav-pills {{
    display: flex;
    gap: 8px;
  }}
  .nav-item {{
    font-size: 12.5px;
    font-weight: 600;
    padding: 6px 16px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
  }}
  .nav-item.active {{
    background: rgba(168, 85, 247, 0.16);
    border-color: rgba(192, 132, 252, 0.5);
    color: #f3e8ff;
    box-shadow: 0 0 14px rgba(168, 85, 247, 0.28);
  }}

  .main-workspace {{
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 785px 431px;
    gap: 20px;
    height: 812px;
  }}

  .terminal-card {{
    background: #090712;
    border: 1px solid rgba(168, 85, 247, 0.28);
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 24px rgba(139, 92, 246, 0.12);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .terminal-titlebar {{
    background: #130f24;
    border-bottom: 1px solid rgba(168, 85, 247, 0.2);
    padding: 10px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .window-buttons {{
    display: flex;
    gap: 8px;
  }}
  .btn-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }}
  .btn-red {{ background: #ff5f56; box-shadow: 0 0 6px rgba(255, 95, 86, 0.5); }}
  .btn-yellow {{ background: #ffbd2e; box-shadow: 0 0 6px rgba(255, 189, 46, 0.5); }}
  .btn-green {{ background: #27c93f; box-shadow: 0 0 6px rgba(39, 201, 63, 0.5); }}

  .window-title-pill {{
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 4px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #cbd5e1;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .window-branch {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    color: #c084fc;
    background: rgba(168, 85, 247, 0.14);
    padding: 3px 9px;
    border-radius: 5px;
    border: 1px solid rgba(168, 85, 247, 0.3);
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .terminal-content {{
    padding: 16px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    line-height: 1.52;
    color: #e2e8f0;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .term-cmd {{
    color: #ffffff;
    font-weight: 700;
  }}
  .term-user {{ color: #c084fc; font-weight: 700; }}
  .term-host {{ color: #60a5fa; }}
  .term-path {{ color: #34d399; }}
  .term-sep {{ color: #64748b; }}

  .cli-banner {{
    color: #a5b4fc;
    line-height: 1.25;
    font-weight: 700;
    margin: 4px 0;
  }}
  .table-box {{
    background: rgba(18, 14, 34, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 12px;
    margin: 2px 0;
  }}
  .table-header {{
    color: #94a3b8;
    font-weight: 700;
    letter-spacing: 0.5px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 5px;
    margin-bottom: 5px;
  }}
  .badge-fail {{
    color: #ef4444;
    background: rgba(239, 68, 68, 0.16);
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 700;
  }}
  .badge-pass {{
    color: #22c55e;
    background: rgba(34, 197, 94, 0.16);
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 700;
  }}
  .col-port {{ color: #38bdf8; font-weight: 600; }}
  .col-proto {{ color: #c084fc; }}
  .col-svc {{ color: #f1f5f9; }}
  .col-pid {{ color: #fbbf24; }}
  .col-proc {{ color: #f472b6; }}
  .col-addr {{ color: #94a3b8; }}

  .summary-line {{
    color: #fbbf24;
    font-weight: 600;
    font-size: 11.5px;
  }}

  .inspect-box {{
    background: rgba(168, 85, 247, 0.08);
    border-left: 3px solid #a855f7;
    border-radius: 0 6px 6px 0;
    padding: 6px 12px;
    font-size: 11.5px;
    line-height: 1.45;
  }}
  .inspect-key {{ color: #c084fc; font-weight: 600; }}
  .inspect-val {{ color: #e2e8f0; }}
  .inspect-sys {{ color: #38bdf8; }}

  .docker-box {{
    background: rgba(56, 189, 248, 0.08);
    border-left: 3px solid #38bdf8;
    border-radius: 0 6px 6px 0;
    padding: 6px 12px;
    font-size: 11.5px;
    line-height: 1.45;
  }}
  .docker-warn {{ color: #f87171; font-weight: 600; }}
  .docker-ok {{ color: #4ade80; font-weight: 700; }}

  .kill-box {{
    background: rgba(34, 197, 94, 0.08);
    border-left: 3px solid #22c55e;
    border-radius: 0 6px 6px 0;
    padding: 6px 12px;
    font-size: 11.5px;
    line-height: 1.45;
  }}

  .right-column {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 16px;
  }}

  .overview-card {{
    background: #110d24;
    border: 1px solid rgba(168, 85, 247, 0.28);
    border-radius: 16px;
    padding: 22px 22px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(139, 92, 246, 0.1);
    display: flex;
    flex-direction: column;
    gap: 13px;
  }}
  .overview-header {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}
  .app-icon {{
    width: 52px;
    height: 52px;
    border-radius: 14px;
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 18px rgba(124, 58, 237, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.18);
  }}
  .app-icon svg {{
    width: 28px;
    height: 28px;
    fill: none;
    stroke: #ffffff;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }}
  .title-group {{
    display: flex;
    flex-direction: column;
  }}
  .app-title {{
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
  }}
  .app-tagline {{
    font-size: 13px;
    font-weight: 600;
    color: #c084fc;
  }}
  .app-platform {{
    font-size: 11.5px;
    color: #94a3b8;
    margin-top: 2px;
  }}

  .project-desc {{
    font-size: 12.8px;
    line-height: 1.55;
    color: #cbd5e1;
  }}

  .feature-list {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .feature-item {{
    display: flex;
    align-items: flex-start;
    gap: 9px;
    font-size: 12px;
    line-height: 1.4;
    color: #e2e8f0;
    background: rgba(255, 255, 255, 0.035);
    padding: 7px 11px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }}
  .feat-icon {{
    font-size: 13px;
    margin-top: 1px;
  }}
  .feat-text strong {{
    color: #f3e8ff;
  }}

  .badge-row {{
    display: flex;
    gap: 8px;
    padding-top: 2px;
  }}
  .metric-badge {{
    flex: 1;
    text-align: center;
    background: rgba(168, 85, 247, 0.1);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 8px;
    padding: 6px 4px;
  }}
  .metric-num {{
    font-size: 14.5px;
    font-weight: 800;
    color: #38bdf8;
    font-family: 'JetBrains Mono', monospace;
  }}
  .metric-lbl {{
    font-size: 9.5px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .stack-card {{
    background: #110d24;
    border: 1px solid rgba(168, 85, 247, 0.28);
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(139, 92, 246, 0.1);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .stack-title {{
    font-size: 11.5px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #c084fc;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .stack-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }}
  .stack-item {{
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .stack-item-icon {{
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .stack-item-icon svg {{
    width: 24px;
    height: 24px;
  }}
  .stack-item-text {{
    display: flex;
    flex-direction: column;
  }}
  .stack-name {{
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
  }}
  .stack-role {{
    font-size: 10px;
    color: #94a3b8;
  }}

  .bottom-bar {{
    position: relative;
    z-index: 1;
    background: rgba(19, 15, 36, 0.85);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 12px;
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  }}
  .feat-tag {{
    font-size: 12.5px;
    color: #cbd5e1;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .sparkle {{
    color: #c084fc;
    font-size: 14px;
  }}
  .gh-badge {{
    background: rgba(168, 85, 247, 0.12);
    border: 1px solid rgba(168, 85, 247, 0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 600;
    color: #e9d5ff;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
</style>
</head>
<body>
  <div class="bg-grid"></div>

  <!-- Header -->
  <div class="header-bar">
    <div class="brand-left">
      <span class="brand-logo">SG.</span>
      <span class="brand-divider">|</span>
      <span class="brand-title">Siddharth Ghode • Developer Portfolio</span>
    </div>
    <div class="nav-pills">
      <span class="nav-item">Home</span>
      <span class="nav-item">About</span>
      <span class="nav-item active">Projects</span>
      <span class="nav-item">Resume</span>
      <span class="nav-item">GitHub</span>
    </div>
  </div>

  <!-- Main Workspace -->
  <div class="main-workspace">

    <!-- Terminal Window -->
    <div class="terminal-card">
      <div class="terminal-titlebar">
        <div class="window-buttons">
          <div class="btn-dot btn-red"></div>
          <div class="btn-dot btn-yellow"></div>
          <div class="btn-dot btn-green"></div>
        </div>
        <div class="window-title-pill">
          <span style="color:#c084fc;">⚡</span>
          <span>bash — portpilot: scan, inspect &amp; preflight — 128×38</span>
        </div>
        <div class="window-branch">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#c084fc" stroke-width="2.5">
            <line x1="6" y1="3" x2="6" y2="15"></line>
            <circle cx="18" cy="6" r="3"></circle>
            <circle cx="6" cy="18" r="3"></circle>
            <path d="M18 9a9 9 0 0 1-9 9"></path>
          </svg>
          <span>main</span>
        </div>
      </div>

      <div class="terminal-content">
        <!-- Command 1: Scan -->
        <div>
          <div>
            <span class="term-user">siddharth@archlinux</span><span class="term-sep">:</span><span class="term-path">~/git/PortPilot</span><span class="term-sep">$</span>
            <span class="term-cmd"> portpilot scan --ports 5432,6379,8000,8080,9000</span>
          </div>

          <div class="cli-banner">
            ═══════════════════════════════════════════════════════════════════════<br>
            &nbsp;&nbsp;PORTPILOT — Linux Port &amp; Process Management CLI<br>
            ═══════════════════════════════════════════════════════════════════════
          </div>

          <div class="table-box">
            <div class="table-header">
              STATUS&nbsp;&nbsp;&nbsp;PORT&nbsp;&nbsp;&nbsp;&nbsp;PROTO&nbsp;&nbsp;SERVICE&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PID&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PROCESS&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ADDRESS
            </div>
            <div><span class="badge-fail">[FAIL]</span>&nbsp;&nbsp;&nbsp;<span class="col-port">5432</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proto">TCP</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-svc">PostgreSQL</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-pid">1184</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proc">postgres</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-addr">0.0.0.0:5432</span></div>
            <div><span class="badge-fail">[FAIL]</span>&nbsp;&nbsp;&nbsp;<span class="col-port">6379</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proto">TCP</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-svc">Redis</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-pid">1420</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proc">redis-server</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-addr">127.0.0.1:6379</span></div>
            <div><span class="badge-fail">[FAIL]</span>&nbsp;&nbsp;&nbsp;<span class="col-port">8000</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proto">TCP</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-svc">Django, FastAPI</span>&nbsp;&nbsp;<span class="col-pid">2951</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proc">uvicorn</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-addr">127.0.0.1:8000</span></div>
            <div><span class="badge-pass">[PASS]</span>&nbsp;&nbsp;&nbsp;<span class="col-port">8080</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proto">TCP</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-svc">HTTP Alt</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-pid">-</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proc">-</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-addr">-</span></div>
            <div><span class="badge-pass">[PASS]</span>&nbsp;&nbsp;&nbsp;<span class="col-port">9000</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proto">TCP</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-svc">SonarQube</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-pid">-</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-proc">-</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="col-addr">-</span></div>
          </div>
          <div class="summary-line">
            ⚠ Found 3 occupied ports out of 5 checked. Potential developer collision detected!
          </div>
        </div>

        <!-- Command 2: Inspect -->
        <div>
          <div>
            <span class="term-user">siddharth@archlinux</span><span class="term-sep">:</span><span class="term-path">~/git/PortPilot</span><span class="term-sep">$</span>
            <span class="term-cmd"> portpilot inspect --port 5432</span>
          </div>
          <div class="inspect-box">
            <div><span class="inspect-key">● Process:</span> <span class="inspect-val">postgres</span> (PID: 1184, PPID: 1, User: postgres)</div>
            <div><span class="inspect-key">● Systemd:</span> <span class="inspect-sys">postgresql.service</span> (status: active, daemon-managed)</div>
            <div><span class="inspect-key">● Command:</span> <span class="inspect-val">/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/data</span></div>
            <div><span class="inspect-key">● Guard:</span> Database daemon detected — safe graceful SIGTERM required</div>
          </div>
        </div>

        <!-- Command 3: Docker-check -->
        <div>
          <div>
            <span class="term-user">siddharth@archlinux</span><span class="term-sep">:</span><span class="term-path">~/git/PortPilot</span><span class="term-sep">$</span>
            <span class="term-cmd"> portpilot docker-check -f docker-compose.yml</span>
          </div>
          <div class="docker-box">
            <div><span class="inspect-key">▶ Preflight Check:</span> Parsing 3 compose services (api:8000, db:5432, redis:6379)...</div>
            <div><span class="docker-warn">✖ Collision:</span> Host port 6379 already allocated by redis-server (PID: 1420).</div>
          </div>
        </div>

        <!-- Command 4: Kill / Resolve -->
        <div>
          <div>
            <span class="term-user">siddharth@archlinux</span><span class="term-sep">:</span><span class="term-path">~/git/PortPilot</span><span class="term-sep">$</span>
            <span class="term-cmd"> portpilot kill --port 6379 --signal SIGTERM</span>
          </div>
          <div class="kill-box">
            <div><span class="inspect-key">✔ Termination:</span> Sent SIGTERM to PID 1420 (redis-server) — verified exited in 0.12s.</div>
            <div><span class="docker-ok">✔ Resolved: Port 6379 is now free! Ready for docker compose up.</span></div>
          </div>
        </div>

        <!-- Cursor Prompt -->
        <div>
          <span class="term-user">siddharth@archlinux</span><span class="term-sep">:</span><span class="term-path">~/git/PortPilot</span><span class="term-sep">$</span>
          <span style="color:#a855f7;">▌</span>
        </div>
      </div>
    </div>

    <!-- Right Sidebar -->
    <div class="right-column">

      <!-- Overview Card -->
      <div class="overview-card">
        <div class="overview-header">
          <div class="app-icon">
            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9"/>
              <path d="M12 3v9l6 3"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <div class="title-group">
            <span class="app-title">PortPilot CLI</span>
            <span class="app-tagline">Linux Port &amp; Process Manager</span>
            <span class="app-platform">🐧 Linux Kernel • Netlink &amp; procfs</span>
          </div>
        </div>

        <p class="project-desc">
          Production-quality Linux developer utility designed to detect socket collisions, inspect process tree metadata, and safely terminate blocking ports before launching applications or Docker containers.
        </p>

        <div class="feature-list">
          <div class="feature-item">
            <span class="feat-icon">⚡</span>
            <div class="feat-text"><strong>Non-Invasive Netlink Scanner:</strong> Zero bind-probe intrusion; direct Linux kernel socket table parsing with fallback.</div>
          </div>
          <div class="feature-item">
            <span class="feat-icon">🛡️</span>
            <div class="feat-text"><strong>Fail-Safe Process Guard:</strong> Rejects PID 0/1, mitigates PID reuse races, and enforces graceful SIGTERM escalation.</div>
          </div>
          <div class="feature-item">
            <span class="feat-icon">🐳</span>
            <div class="feat-text"><strong>Docker Preflight Verification:</strong> Validates Compose port bindings before container startup to eliminate bind errors.</div>
          </div>
        </div>

        <div class="badge-row">
          <div class="metric-badge">
            <div class="metric-num">86%</div>
            <div class="metric-lbl">Coverage</div>
          </div>
          <div class="metric-badge">
            <div class="metric-num">102</div>
            <div class="metric-lbl">Pytests</div>
          </div>
          <div class="metric-badge">
            <div class="metric-num">0 ms</div>
            <div class="metric-lbl">Bind Probe</div>
          </div>
          <div class="metric-badge">
            <div class="metric-num">MIT</div>
            <div class="metric-lbl">License</div>
          </div>
        </div>
      </div>

      <!-- Core Tech Stack -->
      <div class="stack-card">
        <div class="stack-title">
          <span>Core Tech Stack</span>
          <span style="color:#94a3b8; font-weight:600;">Systems &amp; CLI</span>
        </div>

        <div class="stack-grid">
          <div class="stack-item">
            <div class="stack-item-icon">
              {python_svg}
            </div>
            <div class="stack-item-text">
              <span class="stack-name">Python 3.12+</span>
              <span class="stack-role">Async &amp; CLI Core</span>
            </div>
          </div>

          <div class="stack-item">
            <div class="stack-item-icon">
              {linux_svg}
            </div>
            <div class="stack-item-text">
              <span class="stack-name">Linux procfs</span>
              <span class="stack-role">Kernel Sockets</span>
            </div>
          </div>

          <div class="stack-item">
            <div class="stack-item-icon">
              {docker_svg}
            </div>
            <div class="stack-item-text">
              <span class="stack-name">Docker Engine</span>
              <span class="stack-role">Compose Preflight</span>
            </div>
          </div>

          <div class="stack-item">
            <div class="stack-item-icon">
              {git_svg}
            </div>
            <div class="stack-item-text">
              <span class="stack-name">Git &amp; CI</span>
              <span class="stack-role">Automated Testing</span>
            </div>
          </div>

          <div class="stack-item">
            <div class="stack-item-icon">
              {postgres_svg}
            </div>
            <div class="stack-item-text">
              <span class="stack-name">PostgreSQL</span>
              <span class="stack-role">Port 5432 Guard</span>
            </div>
          </div>

          <div class="stack-item">
            <div class="stack-item-icon">
              {redis_svg}
            </div>
            <div class="stack-item-text">
              <span class="stack-name">Redis Engine</span>
              <span class="stack-role">Port 6379 Daemon</span>
            </div>
          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- Bottom Bar -->
  <div class="bottom-bar">
    <div class="feat-tag">
      <span class="sparkle">✦</span>
      <span><strong>Featured Project:</strong> PortPilot — Linux Port &amp; Process Management CLI (Netlink + Docker Preflight + Sockets)</span>
    </div>
    <div class="gh-badge">
      <span>★</span>
      <span>github.com/siddharthghode/PortPilot</span>
    </div>
  </div>

</body>
</html>
"""

    temp_html = "/tmp/portpilot_showcase_render.html"
    temp_png = "/tmp/portpilot_showcase_render.png"

    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    subprocess.run([
        "brave",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--window-size=1300,985",
        f"--screenshot={temp_png}",
        temp_html
    ], check=True)

    img = Image.open(temp_png).convert("RGB")
    if img.size != (1300, 985):
        img = img.resize((1300, 985), Image.Resampling.LANCZOS)

    output_paths = [
        PORTFOLIO_DIR / "src/Assets/Projects/portpilot.jpg",
        REPO_ROOT / "portpilot.jpg"
    ]

    for p in output_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        img.save(
            p,
            "JPEG",
            quality=75,
            dpi=(96, 96),
            comment=b"CREATOR: gd-jpeg v1.0 (using IJG JPEG v62), quality = 75"
        )
        print(f"Generated: {p}")

if __name__ == "__main__":
    generate()
