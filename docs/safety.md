# PortPilot Safety & Security Model

## 1. Safety Philosophy

Terminating processes and managing network ports are security-sensitive operations. A poorly designed CLI can accidentally terminate the user's desktop environment, kill the system init daemon, trigger database file corruption, or be vulnerable to shell injection.

PortPilot enforces a defense-in-depth safety policy designed to prevent catastrophic accidents.

---

## 2. Core Safety Rules

### 2.1 Refusal of Critical Processes
PortPilot will unconditionally refuse to terminate:
- **PID 1 (`init` / `systemd`)**: Terminating PID 1 crashes the Linux kernel immediately (kernel panic).
- **PID 0**: Reserved by the kernel.
- **PortPilot Itself (`os.getpid()`)**: Prevents self-termination deadlocks.
- **Parent Process (`os.getppid()`)**: Prevents killing the developer's interactive shell or terminal multiplexer (tmux/screen).

### 2.2 PID Reuse Race Condition Mitigation
On Linux systems under high load, PIDs are cycled and reused rapidly. If a target process terminates and a different process is assigned that PID before a signal is dispatched, a naive tool might terminate the wrong process.

**PortPilot Mitigation**:
- When inspecting a process, PortPilot records the process creation timestamp (`create_time`).
- Immediately before dispatching `SIGTERM` or `SIGKILL`, PortPilot queries the target process via `psutil` and verifies `create_time` has not deviated (`abs(live - recorded) <= 0.1s`).
- If a discrepancy is detected, the operation is aborted immediately with a `CriticalProcessError`.

### 2.3 Protection of Systemd Managed Services
Modern Linux systems manage persistent background services via `systemd`. Directly sending `SIGTERM` to a process managed by systemd:
1. Often causes systemd to instantly restart the daemon (e.g. `Restart=always`).
2. Leaves the systemd unit state marked as failed or degraded.

**PortPilot Behavior**:
- Detects systemd unit associations via `/proc/<pid>/cgroup` (e.g. `/system.slice/postgresql.service`).
- Displays a prominent warning advising the developer to use:
  ```bash
  sudo systemctl stop <service_name>.service
  ```

### 2.4 Stateful Database & Server Warnings
Terminating database servers (`postgres`, `mysqld`, `mongod`, `redis-server`) abruptly can lead to uncommitted transactions, write-ahead log rollbacks, or lockfile persistence.

**PortPilot Behavior**:
- Detects database binary patterns.
- Displays an explicit warning indicating potential data inconsistency if terminated forcefully.

### 2.5 Two-Stage Termination Workflow
1. **Interactive Confirmation**: Destructive actions always require explicit `[y/N]` confirmation with the default set to **No** (cancellation).
2. **Graceful `SIGTERM` First**: PortPilot always sends `SIGTERM` first, allowing the process to release file locks, close sockets, and persist state.
3. **Grace Period**: Waits up to a configurable duration (default: 5.0 seconds).
4. **Post-Termination Port Verification**: Confirms whether the port was actually freed in the kernel.
5. **SIGKILL Escalation**: Only offered as a distinct, second-tier prompt if `SIGTERM` times out.

### 2.6 Subprocess & Injection Safety
- **No `shell=True`**: All subprocess calls (`ss`, `docker compose`) strictly use argument arrays (`list[str]`), completely eliminating shell injection vulnerabilities.
- **No Automatic Privilege Escalation**: PortPilot never runs `sudo` or escalates permissions silently. It clearly explains when elevated permissions are necessary.

### 2.7 Log Redaction
The logging system uses a `SensitiveDataFilter` to automatically mask credentials, tokens, API keys, and passwords before writing to console or disk.
