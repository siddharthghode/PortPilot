# PortPilot CLI Usage Guide

## Table of Contents
1. [Global Options](#global-options)
2. [Command: check](#command-check)
3. [Command: services](#command-services)
4. [Command: inspect](#command-inspect)
5. [Command: stop](#command-stop)
6. [Command: preflight](#command-preflight)
7. [Command: compose](#command-compose)
8. [Configuration Files](#configuration-files)
9. [Exit Codes](#exit-codes)

---

## 1. Global Options

Global options can be supplied before or after any subcommand:

| Option | Description |
|---|---|
| `--json` | Emit pure JSON output without decorative terminal formatting. |
| `--no-color` | Disable ANSI terminal colors (also enabled if `NO_COLOR=1` is set). |
| `-v`, `--verbose` | Output informational log messages to stderr. |
| `--debug` | Output detailed debugging information (caller, line numbers, timestamp). |
| `--log-file PATH` | Append structured logs to a designated log file path. |
| `--config PATH` | Load custom configuration from a specific TOML or JSON file. |
| `--version` | Display application version and exit. |

---

## 2. Command: `check`

Scan local ports to determine occupancy and identify listening processes.

### Usage
```bash
# Scan default development ports (defined in config or defaults)
portpilot check

# Scan specific ports
portpilot check --ports 5432,6379,8000

# Scan a range of ports
portpilot check --range 3000-3010

# Scan all known development services
portpilot check --services

# Inspect UDP sockets
portpilot check --protocol udp --ports 53,5353

# Export results to JSON
portpilot check --ports 5432,8000 --json
```

### Example Terminal Output
```
STATUS   PORT    PROTO  SERVICE          PID      PROCESS            ADDRESS         
-----------------------------------------------------------------------------------
[PASS]   5432    TCP    PostgreSQL       -        -                  -               
[FAIL]   6379    TCP    Redis            1420     redis-server       127.0.0.1:6379  
[PASS]   8000    TCP    Django, FastAPI  -        -                  -               
-----------------------------------------------------------------------------------
Found 1 occupied port out of 3 checked.
```

---

## 3. Command: `services`

Display predefined and custom service port conventions.

```bash
# Human-readable table
portpilot services

# Machine-readable JSON output
portpilot services --json
```

---

## 4. Command: `inspect`

Inspect detailed process metadata for a single port.

### Usage
```bash
portpilot inspect 5432
portpilot inspect 53 --protocol udp
portpilot inspect 8000 --json
```

### Example Output
```
PORT INSPECTION: 5432/TCP
============================================================
  Port:          5432
  Protocol:      TCP
  Status:        OCCUPIED
  Local Address: 127.0.0.1:5432
  Known Service: PostgreSQL (convention)

OCCUPYING PROCESSES:
  [1] PID 1420:
      Process Name:     postgres
      Status:           sleeping
      Parent PID (PPID):1
      User:             postgres
      Executable:       /usr/bin/postgres
      Command Line:     /usr/bin/postgres -D /var/lib/postgres/data
      Start Time:       2026-11-06 09:15:22 UTC
      Systemd Service:  YES (postgresql.service)
      Docker Managed:   No
```

---

## 5. Command: `stop`

Safely terminate processes listening on an occupied port with strict validation guards.

### Usage
```bash
# Interactive mode: displays process details and asks for explicit confirmation
portpilot stop 5432

# Target a specific PID if multiple processes share a socket
portpilot stop 8000 --pid 9876

# Dry-run: view what would happen without sending any signals
portpilot stop 5432 --dry-run

# Custom grace period before timeout (seconds)
portpilot stop 5432 --timeout 10.0

# Non-interactive confirmation
portpilot stop 5432 --yes

# Force kill with SIGKILL (bypassing SIGTERM)
portpilot stop 5432 --sigkill
```

---

## 6. Command: `preflight`

Inspect Docker Compose host-port mappings before running containers.

### Usage
```bash
# Auto-detect docker-compose.yml or compose.yaml in current directory
portpilot preflight

# Explicit compose file
portpilot preflight -f docker/compose.prod.yml

# JSON format
portpilot preflight --json
```

### Example Output
```
PORTPILOT DOCKER PREFLIGHT
Compose file: /home/archsid/git/project/docker-compose.yml
====================================================================
SERVICE          HOST PORT    PROTOCOL   STATUS       DETAILS
--------------------------------------------------------------------
db               5432         TCP        [FAIL]       PID 1420 (postgres)
redis            6379         TCP        [PASS]       Ready to bind
web              8080         TCP        [PASS]       Ready to bind
--------------------------------------------------------------------
1 conflict detected! Container startup will fail without resolution.
```

---

## 7. Command: `compose`

Wrapper for Docker Compose that runs preflight checks before invoking `up`.

### Usage
```bash
# Runs preflight first; executes 'docker compose up -d' only if ports are free
portpilot compose up -d

# Explicit compose file
portpilot compose -f compose.dev.yml up

# Override and force execution despite conflicts
portpilot compose up --force

# Pass-through commands (down, logs, ps) without preflight overhead
portpilot compose down
portpilot compose ps
```

---

## 8. Configuration Files

PortPilot searches for configuration in the following order:
1. `--config PATH` CLI option
2. `PORTPILOT_CONFIG` environment variable
3. `~/.config/portpilot/config.toml` (or `~/.config/portpilot/config.json`)
4. `~/.portpilot.toml` (or `~/.portpilot.json`)
5. `/etc/portpilot/config.toml` (or `/etc/portpilot/config.json`)

### Example TOML Configuration (`~/.config/portpilot/config.toml`)
```toml
# Default ports scanned by 'portpilot check'
default_ports = [80, 443, 3000, 3306, 5000, 5432, 6379, 8000]

# Default grace period for SIGTERM (seconds)
termination_timeout = 5.0

# Colored output
color = true

# Default protocol (tcp or udp)
default_protocol = "tcp"

# Custom service conventions
[[services]]
name = "InternalAuthServer"
port = 9099
protocol = "tcp"
category = "auth"
description = "Internal authentication service"
```

---

## 9. Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success / All ports available / Successful termination / Clean preflight. |
| `1` | Error occurred / Preflight conflict detected / Permission denied. |
| `2` | Occupied port(s) found during `portpilot check`. |
| `130` | Interrupted by user (`Ctrl+C`). |
