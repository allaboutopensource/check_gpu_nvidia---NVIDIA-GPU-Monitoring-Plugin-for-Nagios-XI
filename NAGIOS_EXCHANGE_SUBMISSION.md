# Nagios Exchange Submission Details

## Project Title
**check_gpu_nvidia - NVIDIA GPU Monitoring Plugin for Nagios/Icinga/NCPA**

## Short Description (max 255 chars)
Nagios-compatible plugin monitoring NVIDIA GPU metrics (memory, temperature, power, utilization, fan) via nvidia-smi with perfdata, thresholds, JSON output, and NCPA/NRPE support.

## Long Description
check_gpu_nvidia is a production-ready Nagios/Icinga/NCPA monitoring plugin for NVIDIA GPUs. It collects comprehensive metrics via nvidia-smi including: VRAM usage (total/used/free/percentage), GPU temperature, power draw/limit/percentage, GPU utilization, memory utilization, fan speed, driver version, and GPU model name.

**Key Features:**
- Nagios standard exit codes (0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN)
- Perfdata output for graphing (PNP4Nagios, Graphite, InfluxDB, Grafana)
- Configurable warning/critical thresholds per metric
- JSON output (--json) for API integration and automation
- Multi-GPU support with per-GPU perfdata
- NCPA local execution (recommended) - no SSH keys needed
- NRPE support for traditional deployments
- SSH remote execution for ad-hoc checks
- Handles unsupported metrics gracefully ([N/A], [Not Supported])

**Execution Modes:**
1. **NCPA (Recommended)**: Plugin runs locally on GPU host via NCPA agent. Nagios server queries via check_ncpa. Secure token-based auth, no SSH keys.
2. **NRPE**: Traditional NRPE daemon with command definition.
3. **SSH**: Direct SSH execution for manual/ad-hoc checks.

**Metrics Monitored:**
- Memory: total, used, free, usage percentage
- Temperature: Celsius with thresholds
- Power: draw (W), limit (W), usage percentage
- Utilization: GPU compute %, memory %
- Fan speed: percentage (where supported)
- Static info: driver version, GPU model name

**Threshold Defaults:** Memory 80/95%, Temp 80/90°C, Power 85/95%, Util 90/98% (all configurable)

## Category
Hardware Monitoring > GPU

## Tags
nvidia, gpu, graphics, cuda, nvidia-smi, ncpa, nrpe, perfdata, json, temperature, power, memory, utilization

## Requirements
- Python 3.6+
- NVIDIA drivers with nvidia-smi
- NCPA agent (for NCPA mode) or NRPE daemon (for NRPE mode)

## Installation
1. Copy check_gpu_nvidia.py to /usr/local/nagios/libexec/
2. chmod +x check_gpu_nvidia.py
3. Configure NCPA/NRPE to execute the plugin
4. Add service check in Nagios/Icinga

## Compatibility
- Nagios Core 4.x, Nagios XI
- Icinga 2, Icinga Web 2
- NCPA 2.x, 3.x
- NRPE 3.x, 4.x
- Tested on: Ubuntu 20.04/22.04/24.04, RHEL/CentOS 7/8/9, Rocky/AlmaLinux 8/9
- GPUs: A100, H100, V100, T4, L4, RTX 3090/4090, Quadro series

## License
MIT License
