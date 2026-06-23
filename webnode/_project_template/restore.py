import json
import os
import sys

# Add current dir to path to import node_backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Define all template contents
tech_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberCore AI — Next-Gen Cognitive Cloud Compute</title>
    <!-- Bootstrap 5 CSS CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Outfit:wght@300;400;500;600;700&family=Courier+Prime&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/static/tech.css">
</head>
<body>

<!-- Scroll Progress Bar -->
<div class="scroll-progress" id="scrollProgress"></div>

<!-- Glassmorphism Navbar -->
<nav class="navbar navbar-expand-lg sticky-top">
    <div class="container">
        <a class="navbar-brand font-orbitron" href="/">CYBER<span>CORE</span> ⚡</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto font-orbitron">
                <li class="nav-item"><a class="nav-link" href="#features">Features</a></li>
                <li class="nav-item"><a class="nav-link" href="#telemetry">Telemetry</a></li>
                <li class="nav-item"><a class="nav-link" href="#terminal">Terminal</a></li>
                <li class="nav-item"><a class="nav-link" href="#calculator">Pricing</a></li>
                <li class="nav-item"><a class="nav-link btn-action-nav ms-lg-3" href="#calculator">Deploy Node</a></li>
            </ul>
        </div>
    </div>
</nav>

<!-- Hero Section -->
<section class="hero-section text-center position-relative overflow-hidden">
    <div class="glow-sphere sphere-1"></div>
    <div class="glow-sphere sphere-2"></div>
    <div class="container position-relative z-index-10">
        <div class="badge-custom mb-3 reveal">INFRASTRUCTURE V4.1</div>
        <h1 class="hero-title font-orbitron mb-4 reveal">
            Decentralized Cognitive <br><span>Compute Fabrics</span>
        </h1>
        <p class="hero-subtitle mb-5 mx-auto reveal" style="max-width: 700px;">
            Deploy neural training weights and deep learning workloads instantly across a globally clustered low-latency network with custom core allocation.
        </p>
        <div class="d-flex justify-content-center gap-3 reveal">
            <a href="#calculator" class="btn-cyan">Launch Instance ➔</a>
            <a href="#terminal" class="btn-outline-cyber">Open Terminal</a>
        </div>
    </div>
    <div class="hero-grid-bg"></div>
</section>

<!-- Features Section (Scroll-Driven Animations) -->
<section class="py-5" id="features">
    <div class="container my-5">
        <div class="text-center mb-5">
            <h2 class="section-title font-orbitron reveal">GRID CAPABILITIES</h2>
            <p class="text-muted reveal">Engineered for extreme performance and dynamic horizontal scalability.</p>
        </div>
        
        <div class="row g-4">
            <!-- Feature Card 1 (Slide Left) -->
            <div class="col-md-4 reveal-left">
                <div class="feature-card">
                    <div class="icon">🌌</div>
                    <h3>Distributed Clusters</h3>
                    <p>Execute edge query jobs dynamically using zero-latency peer nodes across continental pipelines.</p>
                </div>
            </div>
            <!-- Feature Card 2 (Fade Up) -->
            <div class="col-md-4 reveal">
                <div class="feature-card">
                    <div class="icon">⚡</div>
                    <h3>Hot Core Swapping</h3>
                    <p>Scale GPU and TPU processors instantly while live workloads run without cold restart buffers.</p>
                </div>
            </div>
            <!-- Feature Card 3 (Slide Right) -->
            <div class="col-md-4 reveal-right">
                <div class="feature-card">
                    <div class="icon">🔒</div>
                    <h3>Zero-Trust Security</h3>
                    <p>Each computational node is cryptographically verified using end-to-end sandbox tunnels.</p>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Live Telemetry Section (Real-Time AJAX Dashboard) -->
<section class="py-5 section-dark" id="telemetry">
    <div class="container my-5">
        <div class="row align-items-center g-5">
            <div class="col-lg-5 reveal-left">
                <div class="badge-custom mb-3">TELEMETRY STATS</div>
                <h2 class="section-title font-orbitron mb-4 text-start">LIVE CORE ENGINE STATUS</h2>
                <p class="text-muted mb-4">
                    Monitor live telemetry metrics. Our backend engine periodically pushes cluster logs to check computational node limits.
                </p>
                <div class="d-flex gap-3 mb-4">
                    <button class="btn-cyan py-2" onclick="refreshTelemetry()">Force Diagnostics</button>
                    <div class="status-indicator d-flex align-items-center gap-2">
                        <span class="status-dot pulsing"></span>
                        <span style="font-size: 13px; color: var(--neon-green);">ENGINE OPERATIONAL</span>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-7 reveal-right">
                <div class="dashboard-panel">
                    <div class="row g-4">
                        <div class="col-sm-6">
                            <div class="stat-box">
                                <div class="label">CPU ENGINE LOAD</div>
                                <div class="val text-cyan" id="stat-cpu">24%</div>
                                <div class="progress progress-cyber">
                                    <div class="progress-bar bg-cyan" id="progress-cpu" style="width: 24%"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-6">
                            <div class="stat-box">
                                <div class="label">ACTIVE NEURAL NODES</div>
                                <div class="val text-purple" id="stat-nodes">148</div>
                                <div class="progress progress-cyber">
                                    <div class="progress-bar bg-purple" id="progress-nodes" style="width: 60%"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-6">
                            <div class="stat-box">
                                <div class="label">LATENCY / EDGE</div>
                                <div class="val text-orange" id="stat-latency">12 ms</div>
                                <div class="progress progress-cyber">
                                    <div class="progress-bar bg-orange" id="progress-latency" style="width: 15%"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-6">
                            <div class="stat-box">
                                <div class="label">Uptime</div>
                                <div class="val" style="color: #fff;" id="stat-uptime">99.998%</div>
                                <div class="progress progress-cyber">
                                    <div class="progress-bar bg-light" id="progress-uptime" style="width: 99.9%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Virtual Terminal CLI (Interactive Command Console) -->
<section class="py-5" id="terminal">
    <div class="container my-5">
        <div class="text-center mb-5">
            <h2 class="section-title font-orbitron reveal">CORE SHELL INTERACTIVE CLI</h2>
            <p class="text-muted reveal">Type diagnostic command hooks to interact with our backend directly.</p>
        </div>
        
        <div class="row justify-content-center reveal">
            <div class="col-lg-8">
                <div class="cli-console">
                    <div class="cli-header">
                        <span class="cli-dot red"></span>
                        <span class="cli-dot yellow"></span>
                        <span class="cli-dot green"></span>
                        <span class="cli-title">root@cybercore:~#</span>
                    </div>
                    <div class="cli-body" id="cliBody">
                        <div class="cli-line text-muted">// Welcome to CyberCore virtual shell v4.1</div>
                        <div class="cli-line text-muted">// Type 'help' to list operational commands.</div>
                        <br>
                    </div>
                    <form class="cli-input-form" onsubmit="handleCLICommand(event)">
                        <span class="cli-prompt">cybercore$</span>
                        <input type="text" id="cliInput" autocomplete="off" placeholder="type command here..." autofocus>
                    </form>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Pricing Infrastructure Slider Calculator -->
<section class="py-5 section-dark" id="calculator">
    <div class="container my-5">
        <div class="text-center mb-5">
            <h2 class="section-title font-orbitron reveal">INSTANCE ALLOCATION PLANNER</h2>
            <p class="text-muted reveal">Drag sliders to dynamically allocate system cores, compute units and check costs.</p>
        </div>
        
        <div class="row g-5">
            <!-- Left sliders -->
            <div class="col-lg-6 reveal-left">
                <div class="slider-panel">
                    <div class="slider-group mb-4">
                        <div class="d-flex justify-content-between mb-2">
                            <label>COMPUTE CPU CORES</label>
                            <span class="value-display text-cyan"><span id="val-cores">8</span> CORES</span>
                        </div>
                        <input type="range" class="cyber-slider" id="input-cores" min="2" max="64" value="8" oninput="updateCalculator()">
                    </div>
                    
                    <div class="slider-group mb-4">
                        <div class="d-flex justify-content-between mb-2">
                            <label>MEMORY (RAM)</label>
                            <span class="value-display text-purple"><span id="val-ram">32</span> GB</span>
                        </div>
                        <input type="range" class="cyber-slider" id="input-ram" min="4" max="256" value="32" oninput="updateCalculator()">
                    </div>
                    
                    <div class="slider-group mb-4">
                        <div class="d-flex justify-content-between mb-2">
                            <label>SSD BLOCK STORAGE</label>
                            <span class="value-display text-orange"><span id="val-storage">500</span> GB</span>
                        </div>
                        <input type="range" class="cyber-slider" id="input-storage" min="100" max="5000" step="100" value="500" oninput="updateCalculator()">
                    </div>
                </div>
            </div>
            
            <!-- Right cost panel -->
            <div class="col-lg-6 reveal-right">
                <div class="cost-summary-box text-center">
                    <div class="badge-custom mb-3">CYBER CLUSTER NODES</div>
                    <h3 class="font-orbitron mb-3">ESTIMATED COMPUTE PLAN</h3>
                    <div class="pricing-number mb-4 font-orbitron">
                        $<span id="pricing-value">49.00</span><span>/mo</span>
                    </div>
                    <div class="features-summary mb-4">
                        <div>⚡ Core Latency: <span id="feat-latency">&lt; 15ms</span></div>
                        <div>🌌 Sandbox Isolated: <span>Active</span></div>
                        <div>🔒 SLA Uptime Uptime Guarantee: <span>99.99%</span></div>
                    </div>
                    <button class="btn-cyan w-100" onclick="triggerDeployment()">PROCEED TO DEPLOY NODE</button>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Newsletter form -->
<section class="py-5 position-relative overflow-hidden text-center" id="newsletter">
    <div class="container my-5 reveal">
        <h2 class="section-title font-orbitron mb-3">JOIN THE CORE NODE MATRIX</h2>
        <p class="text-muted mb-4 mx-auto" style="max-width: 500px;">Get updates on new neural engine clusters and latency expansion diagnostics.</p>
        <form class="row justify-content-center g-3 align-items-center" onsubmit="submitNewsletter(event)">
            <div class="col-md-5">
                <input type="email" id="newsletterEmail" class="form-control cyber-input" placeholder="Enter cybercore address (email)" required>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn-cyan w-100 py-2">SUBSCRIBE</button>
            </div>
        </form>
    </div>
</section>

<!-- Footer -->
<footer class="py-4 text-center">
    <div class="container">
        <p class="m-0 text-muted font-orbitron" style="font-size: 13px;">&copy; 2026 CYBERCORE AI INC. ZERO TRUST IS ACTIVE. 🔒</p>
    </div>
</footer>

<!-- Toast Notifications Container -->
<div class="toast-container position-fixed bottom-0 end-0 p-3">
    <div id="cyberToast" class="toast align-items-center text-white bg-dark border-0" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
            <div class="toast-body" id="toastMessage">
                Subscribed successfully!
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    </div>
</div>

<!-- Bootstrap 5 JS Bundle CDN -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
    const csrfToken = "{{ csrf_token }}";

    // 1. Scroll Progress Indicator
    window.addEventListener("scroll", () => {
        const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = (winScroll / height) * 100;
        document.getElementById("scrollProgress").style.width = scrolled + "%";
    });

    // 2. Scroll Reveal / Scroll-Driven Animations using IntersectionObserver
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("active");
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll(".reveal, .reveal-left, .reveal-right").forEach(el => {
        revealObserver.observe(el);
    });

    // 3. Pricing Slider Calculator
    function updateCalculator() {
        const cores = parseInt(document.getElementById("input-cores").value);
        const ram = parseInt(document.getElementById("input-ram").value);
        const storage = parseInt(document.getElementById("input-storage").value);
        
        document.getElementById("val-cores").innerText = cores;
        document.getElementById("val-ram").innerText = ram;
        document.getElementById("val-storage").innerText = storage;
        
        // Dynamic formula
        const cost = (cores * 3.5) + (ram * 0.8) + (storage * 0.02);
        document.getElementById("pricing-value").innerText = cost.toFixed(2);
        
        // Dynamic latency
        const lat = Math.max(5, 25 - Math.round(cores * 0.3));
        document.getElementById("feat-latency").innerText = "< " + lat + "ms";
    }

    // Initialize calculator
    updateCalculator();

    // 4. Toast helper
    function showToast(msg) {
        document.getElementById("toastMessage").innerText = msg;
        const toastEl = document.getElementById("cyberToast");
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }

    function triggerDeployment() {
        const cores = document.getElementById("val-cores").innerText;
        const ram = document.getElementById("val-ram").innerText;
        const price = document.getElementById("pricing-value").innerText;
        showToast(`⚡ Deploying ${cores}-Core / ${ram}GB Node... Est Cost: $${price}/mo.`);
    }

    // 5. Live Telemetry polling
    function refreshTelemetry() {
        fetch("/api/telemetry")
            .then(res => res.json())
            .then(data => {
                // Update text
                document.getElementById("stat-cpu").innerText = data.cpu_load + "%";
                document.getElementById("stat-nodes").innerText = data.active_nodes;
                document.getElementById("stat-latency").innerText = data.latency + " ms";
                
                // Update bars
                document.getElementById("progress-cpu").style.width = data.cpu_load + "%";
                document.getElementById("progress-nodes").style.width = Math.min(100, Math.round(data.active_nodes / 2)) + "%";
                document.getElementById("progress-latency").style.width = Math.min(100, Math.round(data.latency * 3)) + "%";
                
                showToast("🔮 Cluster Telemetry Recalculated!");
            });
    }

    // Poll telemetry automatically every 6 seconds
    setInterval(refreshTelemetry, 6000);

    // 6. Interactive Retro CLI Terminal
    const cliBody = document.getElementById("cliBody");
    const cliInput = document.getElementById("cliInput");
    
    function writeTerminalLine(text, type = "") {
        const line = document.createElement("div");
        line.className = "cli-line " + type;
        line.innerText = text;
        cliBody.appendChild(line);
        cliBody.scrollTop = cliBody.scrollHeight;
    }
    
    function handleCLICommand(e) {
        e.preventDefault();
        const cmd = cliInput.value.trim();
        cliInput.value = "";
        
        if (!cmd) return;
        
        writeTerminalLine("cybercore$ " + cmd, "text-white");
        
        const params = new URLSearchParams();
        params.append("csrf_token", csrfToken);
        params.append("command", cmd);
        
        fetch("/api/terminal/command", {
            method: "POST",
            body: params,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.output) {
                // Output is array of strings or string
                if (Array.isArray(data.output)) {
                    data.output.forEach(line => writeTerminalLine(line));
                } else {
                    writeTerminalLine(data.output);
                }
            }
        });
    }

    // 7. Subscribe to Newsletter AJAX POST
    function submitNewsletter(e) {
        e.preventDefault();
        const email = document.getElementById("newsletterEmail").value.trim();
        if (!email) return;
        
        const params = new URLSearchParams();
        params.append("csrf_token", csrfToken);
        params.append("email", email);
        
        fetch("/api/newsletter/subscribe", {
            method: "POST",
            body: params,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "success") {
                showToast("✅ " + data.message);
                document.getElementById("newsletterEmail").value = "";
            } else {
                showToast("❌ " + data.message);
            }
        });
    }
</script>

</body>
</html>"""

tech_css = """/* =====================================================
   Viperwave/Cyberpunk Theme for CyberCore AI Portal
   ===================================================== */
:root {
    --bg-dark: #030712;
    --card-bg: rgba(17, 24, 39, 0.65);
    --border-color: rgba(124, 58, 237, 0.15);
    --neon-cyan: #00f0ff;
    --neon-purple: #a855f7;
    --neon-orange: #f97316;
    --neon-green: #22c55e;
    --text-white: #f3f4f6;
    --shadow-glow: 0 0 15px rgba(0, 240, 255, 0.15);
}

body {
    background-color: var(--bg-dark);
    color: var(--text-white);
    font-family: 'Outfit', sans-serif;
    overflow-x: hidden;
    line-height: 1.6;
}

/* TYPOGRAPHY */
.font-orbitron {
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 2px;
}

/* SCROLL PROGRESS BAR */
.scroll-progress {
    position: fixed;
    top: 0;
    left: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
    width: 0%;
    z-index: 2000;
}

/* STICKY GLASSMORPH NAVBAR */
.navbar {
    background: rgba(3, 7, 18, 0.8);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-color);
    padding: 15px 0;
}
.navbar-brand {
    font-weight: 800;
    color: #fff !important;
    font-size: 24px;
}
.navbar-brand span {
    color: var(--neon-cyan);
}
.nav-link {
    color: #9ca3af !important;
    font-size: 14px;
    font-weight: 600;
    margin-left: 10px;
    transition: color 0.2s;
}
.nav-link:hover {
    color: var(--neon-cyan) !important;
}
.btn-action-nav {
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
    color: #000 !important;
    padding: 6px 16px !important;
    border-radius: 6px;
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
    transition: transform 0.2s !important;
}
.btn-action-nav:hover {
    transform: translateY(-2px);
}

/* HERO SECTION */
.hero-section {
    padding: 140px 0 100px;
    border-bottom: 1px solid var(--border-color);
}
.hero-title {
    font-weight: 900;
    font-size: 56px;
    line-height: 1.2;
}
.hero-title span {
    background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-subtitle {
    font-size: 18px;
    color: #9ca3af;
    font-weight: 300;
}
.glow-sphere {
    position: absolute;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    filter: blur(100px);
    opacity: 0.15;
    z-index: 1;
}
.sphere-1 {
    top: -50px;
    left: -50px;
    background: var(--neon-cyan);
}
.sphere-2 {
    bottom: -50px;
    right: -50px;
    background: var(--neon-purple);
}
.hero-grid-bg {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: 
        linear-gradient(rgba(0, 240, 255, 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 240, 255, 0.02) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
}

/* BUTTONS */
.btn-cyan {
    background: var(--neon-cyan);
    color: #000;
    font-weight: 700;
    border: none;
    padding: 12px 28px;
    border-radius: 8px;
    box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
    transition: all 0.2s;
}
.btn-cyan:hover {
    background: #4df3ff;
    transform: translateY(-2px);
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
}
.btn-outline-cyber {
    background: transparent;
    border: 2px solid var(--neon-purple);
    color: var(--neon-purple);
    font-weight: 700;
    padding: 10px 28px;
    border-radius: 8px;
    transition: all 0.2s;
}
.btn-outline-cyber:hover {
    background: var(--neon-purple);
    color: #000;
    box-shadow: 0 0 15px rgba(168, 85, 247, 0.3);
}

.badge-custom {
    display: inline-block;
    background: rgba(124, 58, 237, 0.15);
    border: 1px solid var(--neon-purple);
    color: var(--neon-purple);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 1px;
}

/* FEATURES STYLES */
.feature-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    padding: 35px 25px;
    border-radius: 12px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    height: 100%;
}
.feature-card:hover {
    transform: translateY(-8px);
    border-color: var(--neon-cyan);
    box-shadow: var(--shadow-glow);
}
.feature-card .icon {
    font-size: 40px;
    margin-bottom: 20px;
}
.feature-card h3 {
    font-family: 'Orbitron', sans-serif;
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 12px;
}
.feature-card p {
    color: #9ca3af;
    font-size: 14px;
    margin: 0;
}

.section-title {
    font-weight: 800;
    font-size: 36px;
    margin-bottom: 15px;
}
.section-dark {
    background-color: #080a13;
    border-top: 1px solid var(--border-color);
    border-bottom: 1px solid var(--border-color);
}

/* TELEMETRY PORTAL */
.dashboard-panel {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    padding: 30px;
    border-radius: 16px;
}
.stat-box {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.03);
    padding: 20px;
    border-radius: 8px;
}
.stat-box .label {
    font-size: 10px;
    font-family: 'Orbitron', sans-serif;
    color: #9ca3af;
    letter-spacing: 1px;
    margin-bottom: 5px;
}
.stat-box .val {
    font-size: 28px;
    font-weight: 800;
    font-family: 'Orbitron', sans-serif;
    margin-bottom: 12px;
}
.text-cyan { color: var(--neon-cyan); }
.text-purple { color: var(--neon-purple); }
.text-orange { color: var(--neon-orange); }

.progress-cyber {
    background: #1f2937;
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
}

/* PULSING INDICATOR */
.status-dot {
    width: 10px;
    height: 10px;
    background: var(--neon-green);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--neon-green);
}
.pulsing {
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% { opacity: 0.5; }
    50% { opacity: 1; }
    100% { opacity: 0.5; }
}

/* VIRTUAL TERMINAL CLI */
.cli-console {
    background: #040509;
    border: 2px solid var(--neon-cyan);
    border-radius: 10px;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.1);
    overflow: hidden;
}
.cli-header {
    background: #111422;
    padding: 10px 15px;
    border-bottom: 2px solid var(--neon-cyan);
    display: flex;
    align-items: center;
    gap: 8px;
}
.cli-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}
.cli-dot.red { background: #ef4444; }
.cli-dot.yellow { background: #f59e0b; }
.cli-dot.green { background: #10b981; }
.cli-title {
    font-family: 'Courier Prime', monospace;
    font-size: 12px;
    color: #9ca3af;
    margin-left: 5px;
}
.cli-body {
    height: 250px;
    padding: 15px;
    overflow-y: auto;
    font-family: 'Courier Prime', monospace;
    font-size: 13px;
    color: var(--neon-green);
    text-shadow: 0 0 3px rgba(34, 197, 94, 0.3);
}
.cli-input-form {
    background: #070911;
    border-top: 1px solid rgba(0, 240, 255, 0.1);
    padding: 8px 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.cli-prompt {
    font-family: 'Courier Prime', monospace;
    color: var(--neon-cyan);
    font-size: 13px;
}
.cli-input-form input {
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-white);
    font-family: 'Courier Prime', monospace;
    font-size: 13px;
    flex-grow: 1;
}

/* SLIDERS CALCULATOR */
.slider-panel {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    padding: 30px;
    border-radius: 16px;
}
.cyber-slider {
    -webkit-appearance: none;
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #1f2937;
    outline: none;
}
.cyber-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--neon-cyan);
    box-shadow: 0 0 10px var(--neon-cyan);
    cursor: pointer;
}
.value-display {
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
}

.cost-summary-box {
    background: linear-gradient(135deg, rgba(26,12,50,0.7), rgba(9,15,36,0.7));
    border: 2px solid var(--neon-purple);
    padding: 40px 30px;
    border-radius: 16px;
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.2);
}
.pricing-number {
    font-size: 48px;
    font-weight: 900;
    color: #fff;
    text-shadow: 0 0 15px rgba(255, 255, 255, 0.2);
}
.pricing-number span {
    font-size: 16px;
    color: #9ca3af;
}

.features-summary {
    font-size: 14px;
    color: #9ca3af;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.features-summary span {
    color: #fff;
    font-weight: 600;
}

/* NEWSLETTER INPUT */
.cyber-input {
    background: rgba(0,0,0,0.3) !important;
    border: 1px solid var(--border-color) !important;
    color: #fff !important;
    font-family: inherit;
}
.cyber-input:focus {
    box-shadow: 0 0 10px var(--neon-purple) !important;
    border-color: var(--neon-purple) !important;
}

/* SCROLL REVEAL CLASSSES */
.reveal {
    opacity: 0;
    transform: translateY(40px);
    transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.reveal-left {
    opacity: 0;
    transform: translateX(-40px);
    transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.reveal-right {
    opacity: 0;
    transform: translateX(40px);
    transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.reveal.active, .reveal-left.active, .reveal-right.active {
    opacity: 1;
    transform: none;
}

footer {
    background: #02040a;
    border-top: 1px solid rgba(255,255,255,0.03);
}
"""

# -----------------------------------------------------------------------------
# GRAPH DICTIONARY DEFINITION
# -----------------------------------------------------------------------------
graph = {
    "nodes": [
        {
            "id": "node-42f0f91d",
            "type": "ServerNode",
            "x": -100,
            "y": 100,
            "config": {
                "ip": "127.0.0.1",
                "port": 8000
            }
        },
        {
            "id": "node-463dc491",
            "type": "HTTPRequestsNode",
            "x": 250,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-630a0f20",
            "type": "ActionLoggerNode",
            "x": 600,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-4899a088",
            "type": "RateLimitNode",
            "x": 950,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-789fa014",
            "type": "AntiBotNode",
            "x": 1300,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-5a10accc",
            "type": "CSRFNode",
            "x": 1650,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-url-home",
            "type": "URLNode",
            "x": 2000,
            "y": -200,
            "config": {
                "path": "/"
            }
        },
        {
            "id": "node-url-telemetry",
            "type": "URLNode",
            "x": 2000,
            "y": 100,
            "config": {
                "path": "/api/telemetry"
            }
        },
        {
            "id": "node-url-subscribe",
            "type": "URLNode",
            "x": 2000,
            "y": 400,
            "config": {
                "path": "/api/newsletter/subscribe"
            }
        },
        {
            "id": "node-url-terminal",
            "type": "URLNode",
            "x": 2000,
            "y": 700,
            "config": {
                "path": "/api/terminal/command"
            }
        },
        {
            "id": "node-logic-home",
            "type": "LogicNode",
            "x": 2400,
            "y": -200,
            "config": {
                "code": "from static.helpers import db\ndef home_logic(req):\n    # Initialize db tables\n    db.execute(\"\"\"\n    CREATE TABLE IF NOT EXISTS newsletter_subscribers (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        email TEXT UNIQUE NOT NULL,\n        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n    )\n    \"\"\")\n    return {\n        'csrf_token': req.context.get('csrf_token', '')\n    }"
            }
        },
        {
            "id": "node-logic-telemetry",
            "type": "JSNode",
            "x": 2400,
            "y": 100,
            "config": {
                "code": "function process_logic(request) {\n    const cpu_load = Math.floor(Math.random() * 70) + 15;\n    const active_nodes = Math.floor(Math.random() * 140) + 100;\n    const latency = Math.floor(Math.random() * 21) + 4;\n    return Response.json({\n        cpu_load: cpu_load,\n        active_nodes: active_nodes,\n        latency: latency\n    });\n}"
            }
        },
        {
            "id": "node-logic-subscribe",
            "type": "LogicNode",
            "x": 2400,
            "y": 400,
            "config": {
                "code": "from static.helpers import db\nfrom nodes.response import Response\ndef subscribe_logic(req):\n    email = req.get_param('email', '').strip().lower()\n    if not email or '@' not in email:\n        return Response.json({'status': 'error', 'message': 'Invalid email address.'})\n    try:\n        db.execute(\"INSERT INTO newsletter_subscribers (email) VALUES (?)\", (email,))\n        return Response.json({'status': 'success', 'message': 'Successfully connected to the Core Node Matrix!'})\n    except Exception:\n        return Response.json({'status': 'error', 'message': 'Email address already registered.'})"
            }
        },
        {
            "id": "node-logic-terminal",
            "type": "LogicNode",
            "x": 2400,
            "y": 700,
            "config": {
                "code": "import random\nfrom static.helpers import db\nfrom nodes.response import Response\ndef terminal_logic(req):\n    cmd = req.get_param('command', '').strip().lower()\n    parts = cmd.split()\n    base_cmd = parts[0] if parts else ''\n    \n    if base_cmd == 'help':\n        output = [\n            \"Operational Commands:\",\n            \"  help          - Display this assistance manual.\",\n            \"  status        - Print neural core operational telemetry.\",\n            \"  matrix        - Stream cognitive data blocks.\",\n            \"  subscribers   - List registered matrix nodes (total count).\",\n            \"  clear         - Clear virtual shell logs.\"\n        ]\n    elif base_cmd == 'status':\n        cpu = random.randint(12, 90)\n        nodes = random.randint(80, 260)\n        latency = random.randint(3, 30)\n        output = [\n            f\"CORE ENGINE STATUS:\",\n            f\"  • CPU Cluster Load : {cpu}%\",\n            f\"  • Active Node Clones: {nodes}\",\n            f\"  • Fiber Ping Latency: {latency} ms\",\n            f\"  • System Security   : ACTIVE (Zero Trust TLS 1.3)\"\n        ]\n    elif base_cmd == 'matrix':\n        lines = []\n        for _ in range(5):\n            block = \" \".join(f\"{random.randint(0,1)}{random.randint(0,1)}{random.randint(0,1)}{random.randint(0,1)}\" for _ in range(5))\n            lines.append(block)\n        output = [\n            \"Cognitive Matrix Stream Enabled:\",\n            *lines\n        ]\n    elif base_cmd == 'subscribers':\n        # Count subscribers in sqlite\n        res = db.fetchall(\"SELECT COUNT(*) as count FROM newsletter_subscribers\")\n        count = res[0]['count'] if res else 0\n        output = f\"Total Operational Matrix Nodes: {count} registered.\"\n    else:\n        output = f\"Command not found: '{base_cmd}'. Type 'help' for options.\"\n        \n    return Response.json({'output': output})"
            }
        },
        {
            "id": "node-render-home",
            "type": "RenderNode",
            "x": 2800,
            "y": -200,
            "config": {
                "filename": "tech.html",
                "html_code": tech_html
            }
        },
        {
            "id": "node-css-tech",
            "type": "CSSNode",
            "x": 3200,
            "y": -100,
            "config": {
                "css_filename": "tech.css",
                "css_code": tech_css
            }
        }
    ],
    "connections": [
        {"source": "node-42f0f91d", "target": "node-463dc491"},
        {"source": "node-463dc491", "target": "node-630a0f20"},
        {"source": "node-630a0f20", "target": "node-4899a088"},
        {"source": "node-4899a088", "target": "node-789fa014"},
        {"source": "node-789fa014", "target": "node-5a10accc"},
        
        {"source": "node-5a10accc", "target": "node-url-home"},
        {"source": "node-5a10accc", "target": "node-url-telemetry"},
        {"source": "node-5a10accc", "target": "node-url-subscribe"},
        {"source": "node-5a10accc", "target": "node-url-terminal"},
        
        {"source": "node-url-home", "target": "node-logic-home"},
        {"source": "node-url-telemetry", "target": "node-logic-telemetry"},
        {"source": "node-url-subscribe", "target": "node-logic-subscribe"},
        {"source": "node-url-terminal", "target": "node-logic-terminal"},
        
        {"source": "node-logic-home", "target": "node-render-home"},
        {"source": "node-render-home", "target": "node-css-tech"}
    ]
}

# -----------------------------------------------------------------------------
# SAVE AND DIRECT COMPILATION RUNNER
# -----------------------------------------------------------------------------
# 1. Write graph to node_editor/graph.json
graph_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "node_editor", "graph.json")
with open(graph_path, "w", encoding="utf-8") as f:
    json.dump(graph, f, indent=4)
print(f"✅ Saved graph.json to {graph_path}")

# 2. Run compiler directly
from node_editor.node_backend import EditorHandler
handler = EditorHandler.__new__(EditorHandler)
handler.compile_graph(graph)
print("✅ SUCCESS: Compiled graph into main.py and generated all files!")
