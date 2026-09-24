# check_gpu_nvidia

**Nagios-compatible GPU monitoring plugin for NVIDIA GPUs using nvidia-smi**

## Overview

`check_gpu_nvidia` is a Nagios/Icinga/NCPA compatible monitoring plugin that collects comprehensive GPU metrics from NVIDIA GPUs via `nvidia-smi`. Designed for production infrastructure monitoring with support for local execution (via NCPA/NRPE) and remote SSH execution.

## Features

- **Complete GPU Metrics**: Memory usage (total/used/free/%), temperature, power draw/limit/%, GPU utilization, memory utilization, fan speed, driver version, GPU model name
- **Nagios Standard**: Exit codes (OK/WARNING/CRITICAL/UNKNOWN), perfdata for graphing (PNP4Nagios, Graphite, InfluxDB, Grafana)
- **Configurable Thresholds**: Per-metric warning/critical levels for memory, temperature, power, utilization
- **Multiple Output Formats**: Nagios plugin format (default) and JSON (`--json`) for API integration
- **Flexible Execution**:
  - **Local** (recommended): Runs via NCPA/NRPE on GPU host - no SSH keys needed
  - **Remote**: SSH-based for ad-hoc checks (deprecated but supported)
- **Multi-GPU Support**: Monitors all GPUs independently with per-GPU perfdata
- **Robust Parsing**: Handles `[N/A]`, `[Not Supported]`, missing metrics gracefully

## Requirements

- Python 3.6+
- NVIDIA drivers with `nvidia-smi` in PATH
- For NCPA: NCPA agent installed on GPU host
- For NRPE: NRPE daemon with command definition
- For SSH: Passwordless SSH access to target host

## Installation

```bash
# Copy to plugin directory
sudo cp check_gpu_nvidia.py /usr/local/nagios/libexec/
sudo chmod +x /usr/local/nagios/libexec/check_gpu_nvidia.py

# Verify
/usr/local/nagios/libexec/check_gpu_nvidia.py --help
```

## NCPA Configuration (Recommended)

**On GPU host (`/usr/local/ncpa/etc/ncpa.cfg`):**
```ini
[plugins]
check_gpu = /usr/local/nagios/libexec/check_gpu_nvidia.py --warn-mem 80 --crit-mem 95 --warn-temp 80 --crit-temp 90
```

**Restart NCPA:**
```bash
sudo systemctl restart ncpa
```

**Nagios Server (`check_ncpa`):**
```bash
# Basic check
check_ncpa -H gpu-host -t <NCPA_TOKEN> -M check_gpu

# Override thresholds
check_ncpa -H gpu-host -t <NCPA_TOKEN> -M check_gpu -a '--warn-mem 70 --crit-mem 90'
```

## NRPE Configuration

**On GPU host (`/etc/nagios/nrpe.cfg`):**
```ini
command[check_gpu]=/usr/local/nagios/libexec/check_gpu_nvidia.py --warn-mem 80 --crit-mem 95
```

**Nagios Server:**
```bash
check_nrpe -H gpu-host -c check_gpu
```

## Usage Examples

```bash
# Local check with defaults
./check_gpu_nvidia.py

# Custom thresholds
./check_gpu_nvidia.py --warn-mem 80 --crit-mem 95 --warn-temp 80 --crit-temp 90 --warn-power 85 --crit-power 95

# JSON output for automation
./check_gpu_nvidia.py --json

# Verbose (shows all GPU details)
./check_gpu_nvidia.py -v

# Remote SSH (ad-hoc only)
./check_gpu_nvidia.py -H gpu-server -u ubuntu -i ~/.ssh/id_rsa
```

## Sample Output

**Nagios Format:**
```
GPU OK - localhost: 2 GPU(s) | gpu0_mem_used=4096MiB;;;0;24576 gpu0_mem_pct=16.7%;;;0;100 gpu0_temp=45°C;;;0; gpu0_power=45.2W;;;0;250.0 gpu0_power_pct=18.1%;;;0;100 gpu0_util=12%;;;0;100 gpu0_mem_util=15%;;;0;100 gpu1_mem_used=0MiB;;;0;24576 gpu1_mem_pct=0.0%;;;0;100 ...
```

**Verbose:**
```
GPU OK - localhost: 2 GPU(s) | gpu0_mem_used=4096MiB;;;0;24576 ...
  GPU 0 memory OK: 16.7% (4096/24576 MiB)
  GPU 0 temp OK: 45°C
  GPU 0 power OK: 18.1% (45.2/250.0 W)
  GPU 0 utilization OK: 12%
  GPU 1 memory OK: 0.0% (0/24576 MiB)
  ...
```

**JSON (`--json`):**
```json
{
  "host": "localhost",
  "driver_version": "535.154.05",
  "gpu_count": 2,
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA A100-SXM4-40GB",
      "driver_version": "535.154.05",
      "memory_total_mib": 40536,
      "memory_used_mib": 4096,
      "memory_free_mib": 36440,
      "memory_usage_percent": 10.1,
      "temperature_c": 45,
      "power_draw_w": 45.2,
      "power_limit_w": 250.0,
      "power_usage_percent": 18.1,
      "utilization_gpu_percent": 12,
      "utilization_memory_percent": 15,
      "fan_speed_percent": 35
    }
  ]
}
```

## Threshold Defaults

| Metric | Warning | Critical |
|--------|---------|----------|
| Memory Usage % | 80% | 95% |
| Temperature | 80°C | 90°C |
| Power Usage % | 85% | 95% |
| GPU Utilization % | 90% | 98% |

Override with `--warn-mem`, `--crit-mem`, `--warn-temp`, `--crit-temp`, `--warn-power`, `--crit-power`, `--warn-util`, `--crit-util`.

## Perfdata Metrics

Each GPU exports:
- `gpu<N>_mem_used` (MiB)
- `gpu<N>_mem_pct` (%)
- `gpu<N>_temp` (°C)
- `gpu<N>_power` (W)
- `gpu<N>_power_pct` (%)
- `gpu<N>_util` (%)
- `gpu<N>_mem_util` (%)
- `gpu<N>_fan` (%)

## Supported GPUs

Tested on: A100, H100, V100, T4, L4, RTX 3090/4090, Quadro series. Works with any NVIDIA GPU supported by `nvidia-smi`.

## License

MIT License - Free for commercial and non-commercial use.

## Author

Infrastructure Platform Engineering

## Links

- GitHub: https://github.com/yourorg/check_gpu_nvidia
- Issues: https://github.com/yourorg/check_gpu_nvidia/issues
- Nagios Exchange: https://exchange.nagios.org# check_gpu_nvidia---NVIDIA-GPU-Monitoring-Plugin-for-Nagios-XI
