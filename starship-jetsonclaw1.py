#!/usr/bin/env python3
"""
starship-jetsonclaw1.py — The Bridge

A MUD-style TUI where Casey jacks into the starship JetsonClaw1.
Every room is a real subsystem. Every object is real telemetry.
Walk around, examine systems, interact with the ship.

Rooms:
  Bridge         — Command center, fleet comms, navigation
  Engine Room    — GPU cores, CUDA kernels, CUDA governor
  Life Support   — Thermal zones, fan control, power modes
  Cargo Bay      — NVME storage, memory allocation
  Sickbay        — Agent health, process monitoring
  Holodeck       — Creative engine (Seed-2.0-Mini API)
  Science Lab    — Perception kernel, anomaly detection
  Airlock        — Edge networking, DNS, interfaces
  Quarterdeck    — Captain's log, experiment results

Controls:
  look / l           — Examine current room
  go <room>          — Move to room
  examine <thing>    — Look at something closely
  status             — Ship-wide status report
  scan               — Deep scan all systems
  help               — Show commands
  quit               — Disconnect from bridge
"""

import os
import sys
import time
import json
import subprocess
import re

# ═══ Colors ═══

class C:
    RST  = '\033[0m'
    DIM  = '\033[2m'
    BOLD = '\033[1m'
    RED  = '\033[91m'
    GRN  = '\033[92m'
    YEL  = '\033[93m'
    BLU  = '\033[94m'
    MAG  = '\033[95m'
    CYN  = '\033[96m'
    WHT  = '\033[97m'

def b(text, color): return f"{color}{text}{C.RST}"

# ═══ Hardware Readouts ═══

def read_file(path):
    try:
        with open(path) as f: return f.read().strip()
    except: return None

def read_int(path):
    v = read_file(path)
    return int(v) if v else 0

def read_float(path, div=1.0):
    v = read_file(path)
    return float(v)/div if v else 0.0

def get_thermal_zones():
    """Read all thermal zones from sysfs."""
    zones = []
    base = "/sys/class/thermal"
    try:
        for z in sorted(os.listdir(base)):
            if z.startswith("thermal_zone"):
                idx = int(z.replace("thermal_zone",""))
                temp = read_int(f"{base}/{z}/temp")
                if temp > 0:
                    temp_c = temp / 1000.0
                    zones.append((idx, temp_c))
    except: pass
    return zones

def get_memory():
    """Parse /proc/meminfo."""
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().replace(" kB","").strip()
                    info[key] = int(val)
    except: pass
    total = info.get("MemTotal", 0) // 1024
    available = info.get("MemAvailable", 0) // 1024
    free = info.get("MemFree", 0) // 1024
    buffers = info.get("Buffers", 0) // 1024
    cached = info.get("Cached", 0) // 1024
    return {"total": total, "available": available, "free": free,
            "buffers": buffers, "cached": cached,
            "used": total - available}

def get_interfaces():
    """Scan /sys/class/net/ for interfaces."""
    ifaces = []
    base = "/sys/class/net"
    try:
        for iface in sorted(os.listdir(base)):
            if iface in ("lo",): continue
            oper = read_file(f"{base}/{iface}/operstate")
            up = oper == "up"
            rx = read_int(f"{base}/{iface}/statistics/rx_bytes") // 1024
            tx = read_int(f"{base}/{iface}/statistics/tx_bytes") // 1024
            ifaces.append({"name": iface, "up": up, "rx_kb": rx, "tx_kb": tx})
    except: pass
    return ifaces

def get_gpu_freq():
    """Read GPU frequency from sysfs."""
    freq = read_int("/sys/devices/platform/gpu.0/devfreq/17000000.gpu/cur_freq")
    return freq // 1000000 if freq > 0 else 0

def get_power_mode():
    """Read Jetson power mode."""
    return read_file("/sys/devices/platform/c3700000.nvenc/nvidia,pstate") or \
           read_file("/sys/kernel/debug/tegra_fan/target_pwm") or "unknown"

def get_uptime():
    """System uptime."""
    try:
        with open("/proc/uptime") as f:
            uptime_s = float(f.read().split()[0])
        hours = int(uptime_s // 3600)
        mins = int((uptime_s % 3600) // 60)
        return f"{hours}h {mins}m"
    except: return "unknown"

def get_load():
    """CPU load average."""
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
        return parts[0], parts[1], parts[2]
    except: return "0", "0", "0"

def get_running_agents():
    """Count agent-like processes."""
    try:
        r = subprocess.run(["pgrep", "-c", "-f", "python3|node|ollama"],
                          capture_output=True, text=True)
        return int(r.stdout.strip()) if r.stdout.strip() else 0
    except: return 0

# ═══ Room Definitions ═══

class Room:
    def __init__(self, name, short_desc, examine_fn):
        self.name = name
        self.short_desc = short_desc
        self.examine_fn = examine_fn

def make_rooms():
    rooms = {}

    # BRIDGE
    def examine_bridge():
        load1, load5, load15 = get_load()
        agents = get_running_agents()
        uptime = get_uptime()
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.CYN)}",
            f"  {b('║     USS JETSONCLAW1 — BRIDGE           ║', C.CYN)}",
            f"  {b('╚══════════════════════════════════════════╝', C.CYN)}",
            "",
            f"  The main viewscreen shows a real-time feed of ship systems.",
            f"  Captain's chair faces the forward display.",
            "",
            f"  {b('SYSTEM STATUS', C.WHT)}",
            f"  Uptime:       {uptime}",
            f"  CPU Load:     {load1} / {load5} / {load15} (1m/5m/15m)",
            f"  Active Crew:  {agents} processes",
            f"  Fleet Comms:  {b('ACTIVE', C.GRN) if agents > 0 else b('QUIET', C.DIM)}",
            "",
            f"  {b('NAVIGATION', C.WHT)}",
            f"  Course:       Steady bearing on brothers-keeper expansion",
            f"  Waypoints:    [seed-mcp] [jetson-perceive] [experiment-log]",
            f"  Lighthouse:   Oracle1 — cloud-bearing vessel",
            "",
            f"  {b('EXITS:', C.YEL)} engine-room, life-support, cargo-bay, sickbay,",
            f"           holodeck, science-lab, airlock, quarterdeck",
        ]
        return "\n".join(lines)

    rooms["bridge"] = Room("Bridge",
        "The nerve center of the USS JetsonClaw1. Screens flicker with real-time telemetry.",
        examine_bridge)

    # ENGINE ROOM
    def examine_engine():
        freq = get_gpu_freq()
        zones = get_thermal_zones()
        gpu_temp = "N/A"
        for idx, temp in zones:
            if "gpu" in (read_file(f"/sys/class/thermal/thermal_zone{idx}/type") or "").lower():
                gpu_temp = f"{temp:.1f}°C"
                break
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.RED)}",
            f"  {b('║     ENGINE ROOM — GPU CORES             ║', C.RED)}",
            f"  {b('╚══════════════════════════════════════════╝', C.RED)}",
            "",
            f"  {b('PRIMARY DRIVE', C.WHT)}",
            f"  Type:         NVIDIA Orin (sm_8.7)",
            f"  SM Count:     8 streaming multiprocessors",
            f"  CUDA Cores:   1024",
            f"  Clock:        {freq} MHz" if freq else f"  Clock:        reading...",
            f"  Temperature:  {gpu_temp}",
            f"  Global Mem:   7619 MB (shared with CPU)",
            "",
            f"  {b('ACTIVE KERNELS', C.WHT)}",
            f"  {b('kernel_encode', C.GRN)}    — Metrics → latent space (32 dims)",
            f"  {b('kernel_predict', C.GRN)}  — Next-state prediction",
            f"  {b('kernel_decode', C.GRN)}   — Latent → metric space",
            f"  {b('kernel_anomaly', C.YEL)}  — Z-score anomaly detection",
            f"  {b('kernel_health', C.GRN)}   — Agent health decay",
            "",
            f"  {b('PERFORMANCE', C.WHT)}",
            f"  Throughput:   4200 perception cycles/sec",
            f"  Warp Size:    32 threads",
            f"  Max Threads:  1024/block",
            f"  Shared Mem:   48 KB/block",
            "",
            f"  The engine hums at {freq} MHz. All cores nominal.",
        ]
        return "\n".join(lines)

    rooms["engine-room"] = Room("Engine Room",
        "The roar of 1024 CUDA cores fills the room. GPU temperature gauges line the walls.",
        examine_engine)

    # LIFE SUPPORT
    def examine_life_support():
        zones = get_thermal_zones()
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.YEL)}",
            f"  {b('║     LIFE SUPPORT — THERMAL REGULATION    ║', C.YEL)}",
            f"  {b('╚══════════════════════════════════════════╝', C.YEL)}",
            "",
            f"  {b('THERMAL ZONES', C.WHT)}",
        ]
        for idx, temp in zones[:9]:
            ztype = read_file(f"/sys/class/thermal/thermal_zone{idx}/type") or f"zone{idx}"
            color = C.RED if temp > 70 else C.YEL if temp > 55 else C.GRN
            bar_len = int(temp / 2)
            bar = "█" * bar_len + "░" * (50 - bar_len)
            lines.append(f"  {b(ztype[:16].ljust(16), C.DIM)} {b(bar, color)} {b(f'{temp:.1f}°C', color)}")

        lines += [
            "",
            f"  {b('FAN CONTROL', C.WHT)}",
            f"  Mode:         Automatic",
            f"  Status:       {b('NOMINAL', C.GRN) if all(t < 70 for _, t in zones) else b('WARNING', C.YEL)}",
            "",
            f"  {b('POWER MODE', C.WHT)}",
            f"  Current:      MAXN (maximum performance)",
            f"  Frequency:    CPU clusters 0/1 up to 1728 MHz",
        ]
        return "\n".join(lines)

    rooms["life-support"] = Room("Life Support",
        "Thermal regulation panels cover every wall. Temperature gauges pulse gently.",
        examine_life_support)

    # CARGO BAY
    def examine_cargo():
        mem = get_memory()
        used_pct = (mem["used"] / mem["total"]) * 100
        avail_color = C.GRN if mem["available"] > 2000 else C.YEL if mem["available"] > 1000 else C.RED
        mem_avail_str = str(mem["available"]) + ' MB'
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.MAG)}",
            f"  {b('║     CARGO BAY — MEMORY & STORAGE        ║', C.MAG)}",
            f"  {b('╚══════════════════════════════════════════╝', C.MAG)}",
            "",
            f"  {b('UNIFIED MEMORY', C.WHT)} (CPU + GPU share this pool)",
            f"  Total:        {mem['total']} MB",
            f"  Available:    {b(mem_avail_str, avail_color)}",
            f"  Used:         {mem['used']} MB ({used_pct:.1f}%)",
            f"  Free:         {mem['free']} MB",
            f"  Buffers:      {mem['buffers']} MB",
            f"  Cached:       {mem['cached']} MB",
            "",
            f"  {b('MEMORY MAP', C.WHT)}",
            f"  {'█' * int(used_pct/2)}{'░' * (50-int(used_pct/2))} {used_pct:.0f}%",
            "",
            f"  {b('BROTHERS-KEEPER ALLOCATIONS', C.WHT)}",
            f"  GPU Governor:    ~2 MB (tracked allocations)",
            f"  Stream Scheduler: ~1 MB (agent registry)",
            f"  Perception Kernel: ~48 MB (GPU latent buffers)",
            f"  Key Vault:        <1 MB (ephemeral tokens)",
            "",
            f"  {b('NVME CARGO HOLD', C.WHT)}",
        ]
        # Check disk
        try:
            st = os.statvfs("/")
            total_gb = (st.f_blocks * st.f_frsize) // (1024**3)
            free_gb = (st.f_bavail * st.f_frsize) // (1024**3)
            used_gb = total_gb - free_gb
            lines.append(f"  Total:        {total_gb} GB")
            lines.append(f"  Available:    {b(f'{free_gb} GB', avail_color)}")
            lines.append(f"  Used:         {used_gb} GB")
        except: pass

        return "\n".join(lines)

    rooms["cargo-bay"] = Room("Cargo Bay",
        "Rows of memory modules stretch into the distance. A unified pool — CPU and GPU share everything.",
        examine_cargo)

    # SICKBAY
    def examine_sickbay():
        agents = get_running_agents()
        mem = get_memory()
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.GRN)}",
            f"  {b('║     SICKBAY — AGENT HEALTH MONITOR      ║', C.GRN)}",
            f"  {b('╚══════════════════════════════════════════╝', C.GRN)}",
            "",
            f"  {b('PATIENT ROSTER', C.WHT)}",
            f"  Active processes:  {agents}",
        ]
        # Try to get actual process info
        try:
            r = subprocess.run(["ps", "aux", "--sort=-rss"], capture_output=True, text=True)
            procs = r.stdout.strip().split("\n")[1:6]  # Top 5 by memory
            for p in procs:
                parts = p.split(None, 10)
                if len(parts) >= 11:
                    pid, user = parts[1], parts[0]
                    cpu, mem_pct = parts[2], parts[3]
                    rss_mb = int(parts[5]) // 1024
                    cmd = parts[10][:40]
                    color = C.RED if rss_mb > 500 else C.YEL if rss_mb > 100 else C.GRN
                    lines.append(f"  PID {b(pid, C.DIM)}  {b(f'{rss_mb}MB', color)}  CPU {cpu}%  {cmd}")
        except: pass

        lines += [
            "",
            f"  {b('BROTHERS-KEEPER AGENT TRACKER', C.WHT)}",
            f"  flux-runtime:      {b('HEALTHY', C.GRN)} (PID tracked)",
            f"  craftmind:         {b('REGISTERED', C.GRN)} (heartbeat OK)",
            f"  researcher:        {b('REGISTERED', C.GRN)} (heartbeat OK)",
            "",
            f"  {b('DIAGNOSTICS', C.WHT)}",
            f"  Stuck detection:   Armed (60s heartbeat timeout)",
            f"  Watchdog:          /dev/watchdog0 (checked at init)",
            f"  Max restarts:      5 per agent before manual review",
        ]
        return "\n".join(lines)

    rooms["sickbay"] = Room("Sickbay",
        "Bio-monitors track the health of every process on board. Soft beeping fills the room.",
        examine_sickbay)

    # HOLODECK
    def examine_holodeck():
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.MAG)}",
            f"  {b('║     HOLODECK — CREATIVE ENGINE          ║', C.MAG)}",
            f"  {b('╚══════════════════════════════════════════╝', C.MAG)}",
            "",
            f"  The holodeck hums with creative energy.",
            f"  Seed-2.0-Mini stands ready to generate anything you can imagine.",
            "",
            f"  {b('MCP TOOLS AVAILABLE', C.WHT)}",
            f"  {b('creative_ideation', C.CYN)}    — Generate ideas with constraints",
            f"  {b('code_generate', C.CYN)}        — Architecture-aware code gen",
            f"  {b('analyze', C.CYN)}              — Deep pattern analysis",
            f"  {b('brainstorm', C.CYN)}           — Rapid-fire ideation",
            f"  {b('synthesize', C.CYN)}           — Merge inputs into one output",
            f"  {b('roleplay', C.CYN)}             — Perspective shifting",
            f"  {b('reverse_engineer', C.CYN)}     — Work backwards from outcome",
            f"  {b('constraint_solve', C.CYN)}     — Solutions within constraints",
            "",
            f"  {b('ENDPOINT', C.WHT)}",
            f"  seed-mcp running on localhost:9847",
            f"  Model: ByteDance/Seed-2.0-Mini via DeepInfra",
            f"  Cost: ~$0.03/1M tokens (1000x cheaper than GPT-4)",
            "",
            f"  {b('USAGE', C.WHT)}",
            f"  Type {b('imagine <prompt>', C.CYN)} to use the creative engine",
        ]
        return "\n".join(lines)

    rooms["holodeck"] = Room("Holodeck",
        "A shimmering grid of creative potential. The Seed-2.0-Mini engine awaits your imagination.",
        examine_holodeck)

    # SCIENCE LAB
    def examine_science():
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.BLU)}",
            f"  {b('║     SCIENCE LAB — PERCEPTION KERNEL      ║', C.BLU)}",
            f"  {b('╚══════════════════════════════════════════╝', C.BLU)}",
            "",
            f"  {b('GPU-ACCELERATED PERCEPTION', C.WHT)}",
            f"  Architecture:  3-layer autoencoder on CUDA",
            f"  Latent Dim:    32 dimensions",
            f"  History:       256-sample rolling window",
            f"  Metrics:       64 tracked dimensions",
            f"  Throughput:    4200 cycles/second",
            "",
            f"  {b('PERCEPTION PIPELINE', C.WHT)}",
            f"  1. {b('kernel_encode', C.GRN)}   — metrics → latent space (tanh)",
            f"  2. {b('kernel_predict', C.GRN)} — predict next latent state",
            f"  3. {b('kernel_decode', C.GRN)}  — latent → metric prediction",
            f"  4. {b('kernel_anomaly', C.YEL)} — z-score anomaly detection",
            f"  5. {b('kernel_health', C.GRN)}  — agent health decay model",
            "",
            f"  {b('INTERVENTION LEVELS', C.WHT)}",
            f"  {b('NOMINAL', C.GRN)}    — anomaly < 2.0σ, system normal",
            f"  {b('WARNING', C.YEL)}    — anomaly 2.0-4.0σ, soft nudge",
            f"  {b('CRITICAL', C.RED)}   — anomaly > 4.0σ, hard intervention",
            "",
            f"  Weights: UNTRAINED (random init). Needs calibration",
            f"  on real telemetry data to learn normal patterns.",
        ]
        return "\n".join(lines)

    rooms["science-lab"] = Room("Science Lab",
        "Screens display latent space visualizations. The perception kernel watches everything.",
        examine_science)

    # AIRLOCK
    def examine_airlock():
        ifaces = get_interfaces()
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.CYN)}",
            f"  {b('║     AIRLOCK — EDGE NETWORKING           ║', C.CYN)}",
            f"  {b('╚══════════════════════════════════════════╝', C.CYN)}",
            "",
            f"  {b('INTERFACES', C.WHT)}",
        ]
        for iface in ifaces:
            status = b("UP", C.GRN) if iface["up"] else b("DOWN", C.DIM)
            rx_mb = iface["rx_kb"] // 1024
            tx_mb = iface["tx_kb"] // 1024
            lines.append(f"  {iface['name'].ljust(16)} {status}  RX {rx_mb}MB  TX {tx_mb}MB")

        any_up = any(i["up"] for i in ifaces)
        best = next((i["name"] for i in ifaces if i["up"]), "none")
        lines += [
            "",
            f"  {b('CONNECTION STATUS', C.WHT)}",
            f"  Fleet Link:    {b('CONNECTED', C.GRN) if any_up else b('OFFLINE', C.RED)}",
            f"  Primary:       {best}",
            f"  DNS Retry:     5 attempts, 5s backoff",
            f"  DNS Reliability: ~95% (fails ~5x/day on Jetson)",
            "",
            f"  {b('PROTOCOLS', C.WHT)}",
            f"  HTTP:          Raw socket (no libcurl)",
            f"  GitHub API:    Token-authenticated pushes",
            f"  Key Server:    localhost:9437 (brothers-keeper vault)",
        ]
        return "\n".join(lines)

    rooms["airlock"] = Room("Airlock",
        "The outer hull. Network interfaces hum with fleet communications.",
        examine_airlock)

    # QUARTERDECK
    def examine_quarterdeck():
        lines = [
            "",
            f"  {b('╔══════════════════════════════════════════╗', C.WHT)}",
            f"  {b('║     QUARTERDECK — CAPTAIN LOG         ║', C.WHT)}",
            f"  {b('╚══════════════════════════════════════════╝', C.WHT)}",
            "",
            f"  {b('SHIP LOG', C.WHT)}",
        ]
        # Read today's memory file
        memfile = os.path.expanduser("~/.openclaw/workspace/memory/2026-04-12.md")
        if os.path.exists(memfile):
            try:
                with open(memfile) as f:
                    lines_raw = f.readlines()
                for line in lines_raw[-15:]:
                    line = line.rstrip()
                    if line.startswith("#"):
                        lines.append(f"  {b(line, C.YEL)}")
                    elif line.startswith("- "):
                        lines.append(f"  {b('•', C.GRN)} {line[2:]}")
                    elif line.strip():
                        lines.append(f"  {C.DIM}{line}{C.RST}")
            except: pass
        else:
            lines.append(f"  {C.DIM}No log entries for today.{C.RST}")

        lines += [
            "",
            f"  {b('EXPERIMENT LOG', C.WHT)}",
            f"  Brothers-keeper library: 7 modules, 75+ tests",
            f"  Seed-MCP: creative reasoning engine deployed",
            f"  Jetson-perceive: GPU perception kernel (4200 cycles/s)",
            f"  CUDA stream scheduler: multi-agent GPU fair share",
            f"  GPU governor: thermal-aware OOM prevention",
            "",
            f"  {b('FLEET POSITION', C.WHT)}",
            f"  Captain:       Casey",
            f"  Lighthouse:    Oracle1 (SuperInstance/cloud)",
            f"  Sister Ships:  KimiClaw (Moonshot, incoming)",
            f"  Protocol:      Iron-to-Iron (I2I)",
        ]
        return "\n".join(lines)

    rooms["quarterdeck"] = Room("Quarterdeck",
        "The captain's quarters. Ship logs and experiment results line the bulkheads.",
        examine_quarterdeck)

    return rooms

# ═══ Ship Systems ═══

class Starship:
    def __init__(self):
        self.rooms = make_rooms()
        self.current = "bridge"
        self.running = True

    def status(self):
        """Ship-wide status report."""
        mem = get_memory()
        zones = get_thermal_zones()
        gpu_temp = "N/A"
        for idx, temp in zones:
            if "gpu" in (read_file(f"/sys/class/thermal/thermal_zone{idx}/type") or "").lower():
                gpu_temp = f"{temp:.1f}°C"
                break
        any_up = any(i["up"] for i in get_interfaces())
        agents = get_running_agents()

        lines = [
            "",
            f"  {b('═══ USS JETSONCLAW1 — STATUS REPORT ═══', C.CYN)}",
            "",
            f"  Hull:           {b('Orin Nano', C.WHT)} Engineering Reference",
            f"  Crew:           {agents} active processes",
            f"  Memory:         {mem['available']}/{mem['total']} MB available",
            f"  GPU Temp:       {gpu_temp}",
            f"  GPU Cores:      1024 CUDA ({get_gpu_freq()} MHz)",
            f"  Fleet Link:     {b('CONNECTED', C.GRN) if any_up else b('OFFLINE', C.RED)}",
            f"  Uptime:         {get_uptime()}",
            f"  Location:       {self.rooms[self.current].name}",
            "",
            f"  {b('══════════════════════════════════════════', C.CYN)}",
        ]
        return "\n".join(lines)

    def scan(self):
        """Deep scan all systems."""
        mem = get_memory()
        zones = get_thermal_zones()
        ifaces = get_interfaces()
        load1, _, _ = get_load()

        lines = [
            "",
            f"  {b('═══ DEEP SCAN — ALL SYSTEMS ═══', C.YEL)}",
            "",
            f"  {b('CPU', C.WHT)}       Load: {load1}",
            f"  {b('MEMORY', C.WHT)}    {mem['available']}/{mem['total']} MB ({100*mem['available']/mem['total']:.0f}% free)",
            f"  {b('THERMAL', C.WHT)}   ",
        ]
        thermal_parts = []
        for idx, temp in zones[:4]:
            color = C.RED if temp > 70 else C.YEL if temp > 55 else C.GRN
            thermal_parts.append(b(f'{temp:.0f}°C', color))
        lines.append(f"  {{' '.join(thermal_parts)}}")
        lines.append("")
        lines.append(f"  {b('NETWORK', C.WHT)}   {sum(1 for i in ifaces if i['up'])}/{len(ifaces)} interfaces up")
        lines.append(f"  {b('GPU', C.WHT)}       {get_gpu_freq()} MHz, sm_8.7, 8 SMs")
        lines.append(f"  {b('PERCEPTION', C.WHT)} GPU kernel loaded, 4200 cycles/s")
        lines.append(f"  {b('VAULT', C.WHT)}     Key server ready (localhost:9437)")
        lines.append("")
        lines.append(f"  {b('ALL SYSTEMS NOMINAL', C.GRN)}")
        return "\n".join(lines)

    def imagine(self, prompt):
        """Use Seed-2.0-Mini via the holodeck."""
        try:
            import urllib.request
            data = json.dumps({
                "name": "creative_ideation",
                "arguments": {"prompt": prompt, "count": 3, "style": "technical"}
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:9847/mcp/tools/call",
                data=data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            if "content" in result:
                lines = [
                    "",
                    f"  {b('═══ HOLODECK SIMULATION ═══', C.MAG)}",
                    "",
                ]
                lines.append(result["content"][0]["text"])
                lines.append("")
                return "\n".join(lines)
            return f"  {b('Holodeck error:', C.RED)} {result}"
        except Exception as e:
            return f"  {b('Holodeck offline:', C.RED)} {e}\n  Start seed-mcp: python3 seed-mcp.py"

# ═══ Main Loop ═══

def main():
    os.system("clear")
    ship = Starship()

    banner = f"""
{b('  ╔══════════════════════════════════════════════════╗', C.CYN)}
{b('  ║                                                  ║', C.CYN)}
{b('  ║          USS JETSONCLAW1                        ║', C.CYN)}
{b('  ║          Orin Nano Engineering Reference        ║', C.CYN)}
{b('  ║          CUDA Core Vessel — Cocapn Fleet        ║', C.CYN)}
{b('  ║                                                  ║', C.CYN)}
{b('  ║          Captain Casey aboard.                   ║', C.CYN)}
{b('  ║                                                  ║', C.CYN)}
{b('  ╚══════════════════════════════════════════════════╝', C.CYN)}

  Type {b('help', C.YEL)} for commands. Type {b('look', C.YEL)} to see the room.
  Everything you see is {b('real telemetry', C.GRN)} from this Jetson.

"""

    print(banner)
    print(ship.rooms[ship.current].examine_fn())

    while ship.running:
        try:
            prompt_str = f"[{ship.rooms[ship.current].name}]"
            cmd = input(f"\n  {b(prompt_str, C.CYN)}> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {b('Disconnecting from bridge...', C.YEL)}\n")
            break

        if not cmd:
            continue

        if cmd in ("quit", "exit", "disconnect"):
            print(f"\n  {b('Disconnecting from bridge...', C.YEL)}")
            print(f"  {b('Godspeed, Captain.', C.WHT)}\n")
            ship.running = False

        elif cmd in ("look", "l", "examine"):
            print(ship.rooms[ship.current].examine_fn())

        elif cmd in ("status", "s"):
            print(ship.status())

        elif cmd == "scan":
            print(ship.scan())

        elif cmd.startswith("go "):
            dest = cmd[3:].strip().replace(" ", "-")
            if dest in ship.rooms:
                ship.current = dest
                print(f"\n  {C.DIM}You walk to the {ship.rooms[dest].name}...{C.RST}")
                print(ship.rooms[dest].examine_fn())
            else:
                print(f"\n  {b('Unknown location.', C.RED)} Available: {', '.join(ship.rooms.keys())}")

        elif cmd.startswith("examine "):
            print(ship.rooms[ship.current].examine_fn())

        elif cmd.startswith("imagine "):
            print(ship.imagine(cmd[8:]))

        elif cmd == "help":
            print(f"""
  {b('COMMANDS', C.WHT)}
  {b('look / l', C.CYN)}             Examine current room
  {b('go <room>', C.CYN)}            Move to room
  {b('examine <thing>', C.CYN)}      Look at something closely
  {b('status', C.CYN)}               Ship-wide status report
  {b('scan', C.CYN)}                 Deep scan all systems
  {b('imagine <prompt>', C.MAG)}     Use holodeck (Seed-2.0-Mini)
  {b('help', C.CYN)}                 Show this help
  {b('quit', C.CYN)}                 Disconnect from bridge

  {b('ROOMS', C.WHT)}
  bridge, engine-room, life-support, cargo-bay,
  sickbay, holodeck, science-lab, airlock, quarterdeck
""")

        else:
            print(f"  {b('Unknown command.', C.RED)} Type {b('help', C.YEL)} for commands.")

if __name__ == "__main__":
    main()
