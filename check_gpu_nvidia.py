#!/usr/bin/env python3
"""
Nagios-compatible GPU monitoring plugin using nvidia-smi.
Supports local and remote (SSH) monitoring.
"""

import argparse
import subprocess
import sys
import json
import re
from dataclasses import dataclass
from typing import Optional, List
from enum import IntEnum


class NagiosStatus(IntEnum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


@dataclass
class GPUInfo:
    index: int
    name: str
    driver_version: str
    memory_total: int  # MiB
    memory_used: int   # MiB
    memory_free: int   # MiB
    temperature: Optional[int]  # Celsius
    power_draw: Optional[float]  # Watts
    power_limit: Optional[float]  # Watts
    utilization_gpu: Optional[int]  # Percent
    utilization_memory: Optional[int]  # Percent
    fan_speed: Optional[int]  # Percent

    @property
    def memory_usage_percent(self) -> float:
        return (self.memory_used / self.memory_total * 100) if self.memory_total > 0 else 0

    @property
    def power_usage_percent(self) -> Optional[float]:
        if self.power_limit and self.power_limit > 0 and self.power_draw is not None:
            return (self.power_draw / self.power_limit * 100)
        return None


def parse_nvidia_smi_output(output: str) -> List[GPUInfo]:
    """Parse nvidia-smi --query-gpu output (CSV format)."""
    gpus = []
    lines = output.strip().split('\n')
    
    # Skip header line if present (when not using noheader)
    start_idx = 1 if lines and 'index' in lines[0].lower() else 0
    
    for i, line in enumerate(lines[start_idx:], start_idx):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 10:
            continue
            
        try:
            gpu = GPUInfo(
                index=int(parts[0]),
                name=parts[1],
                driver_version=parts[2],
                memory_total=int(parts[3].replace(' MiB', '')),
                memory_used=int(parts[4].replace(' MiB', '')),
                memory_free=int(parts[5].replace(' MiB', '')),
                temperature=int(parts[6]) if parts[6] not in ('[Not Supported]', '[N/A]') else None,
                power_draw=float(parts[7].replace(' W', '')) if parts[7] not in ('[Not Supported]', '[N/A]') else None,
                power_limit=float(parts[8].replace(' W', '')) if parts[8] not in ('[Not Supported]', '[N/A]') else None,
                utilization_gpu=int(parts[9].replace(' %', '')) if parts[9] not in ('[Not Supported]', '[N/A]') else None,
                utilization_memory=int(parts[10].replace(' %', '')) if parts[10] not in ('[Not Supported]', '[N/A]') else None,
                fan_speed=int(parts[11].replace(' %', '')) if len(parts) > 11 and parts[11] not in ('[Not Supported]', '[N/A]') else None,
            )
            gpus.append(gpu)
        except (ValueError, IndexError) as e:
            print(f"Warning: Failed to parse GPU line {i}: {line}", file=sys.stderr)
            
    return gpus


def run_nvidia_smi(timeout: int = 30) -> str:
    """Run nvidia-smi locally."""
    query = (
        "index,name,driver_version,memory.total,memory.used,memory.free,"
        "temperature.gpu,power.draw,power.limit,utilization.gpu,utilization.memory,fan.speed"
    )
    cmd = ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"nvidia-smi failed: {result.stderr}")
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"nvidia-smi timed out after {timeout}s")
    except FileNotFoundError:
        raise RuntimeError("nvidia-smi not found. Is NVIDIA driver installed?")


def evaluate_thresholds(gpus: List[GPUInfo], warn_mem: int, crit_mem: int,
                        warn_temp: int, crit_temp: int,
                        warn_power: int, crit_power: int,
                        warn_util: int, crit_util: int) -> tuple[NagiosStatus, List[str]]:
    """Evaluate all GPUs against thresholds. Returns (worst_status, messages)."""
    worst_status = NagiosStatus.OK
    messages = []
    
    for gpu in gpus:
        gpu_msgs = []
        gpu_status = NagiosStatus.OK
        
        # Memory usage
        mem_pct = gpu.memory_usage_percent
        if mem_pct >= crit_mem:
            gpu_status = max(gpu_status, NagiosStatus.CRITICAL)
            gpu_msgs.append(f"GPU {gpu.index} memory CRITICAL: {mem_pct:.1f}% ({gpu.memory_used}/{gpu.memory_total} MiB)")
        elif mem_pct >= warn_mem:
            gpu_status = max(gpu_status, NagiosStatus.WARNING)
            gpu_msgs.append(f"GPU {gpu.index} memory WARNING: {mem_pct:.1f}% ({gpu.memory_used}/{gpu.memory_total} MiB)")
        else:
            gpu_msgs.append(f"GPU {gpu.index} memory OK: {mem_pct:.1f}% ({gpu.memory_used}/{gpu.memory_total} MiB)")
        
        # Temperature
        if gpu.temperature is not None:
            if gpu.temperature >= crit_temp:
                gpu_status = max(gpu_status, NagiosStatus.CRITICAL)
                gpu_msgs.append(f"GPU {gpu.index} temp CRITICAL: {gpu.temperature}°C")
            elif gpu.temperature >= warn_temp:
                gpu_status = max(gpu_status, NagiosStatus.WARNING)
                gpu_msgs.append(f"GPU {gpu.index} temp WARNING: {gpu.temperature}°C")
            else:
                gpu_msgs.append(f"GPU {gpu.index} temp OK: {gpu.temperature}°C")
        
        # Power usage
        if gpu.power_usage_percent is not None:
            power_pct = gpu.power_usage_percent
            if power_pct >= crit_power:
                gpu_status = max(gpu_status, NagiosStatus.CRITICAL)
                gpu_msgs.append(f"GPU {gpu.index} power CRITICAL: {power_pct:.1f}% ({gpu.power_draw:.1f}/{gpu.power_limit:.1f} W)")
            elif power_pct >= warn_power:
                gpu_status = max(gpu_status, NagiosStatus.WARNING)
                gpu_msgs.append(f"GPU {gpu.index} power WARNING: {power_pct:.1f}% ({gpu.power_draw:.1f}/{gpu.power_limit:.1f} W)")
            else:
                gpu_msgs.append(f"GPU {gpu.index} power OK: {power_pct:.1f}% ({gpu.power_draw:.1f}/{gpu.power_limit:.1f} W)")
        
        # GPU utilization
        if gpu.utilization_gpu is not None:
            if gpu.utilization_gpu >= crit_util:
                gpu_status = max(gpu_status, NagiosStatus.CRITICAL)
                gpu_msgs.append(f"GPU {gpu.index} utilization CRITICAL: {gpu.utilization_gpu}%")
            elif gpu.utilization_gpu >= warn_util:
                gpu_status = max(gpu_status, NagiosStatus.WARNING)
                gpu_msgs.append(f"GPU {gpu.index} utilization WARNING: {gpu.utilization_gpu}%")
            else:
                gpu_msgs.append(f"GPU {gpu.index} utilization OK: {gpu.utilization_gpu}%")
        
        worst_status = max(worst_status, gpu_status)
        messages.extend(gpu_msgs)
    
    return worst_status, messages


def build_perfdata(gpus: List[GPUInfo]) -> str:
    """Build Nagios perfdata string."""
    perfdata_parts = []
    for gpu in gpus:
        prefix = f"gpu{gpu.index}"
        perfdata_parts.append(f"{prefix}_mem_used={gpu.memory_used}MiB;;;0;{gpu.memory_total}")
        perfdata_parts.append(f"{prefix}_mem_pct={gpu.memory_usage_percent:.1f}%;;;0;100")
        if gpu.temperature is not None:
            perfdata_parts.append(f"{prefix}_temp={gpu.temperature}°C;;;0;")
        if gpu.power_draw is not None:
            perfdata_parts.append(f"{prefix}_power={gpu.power_draw:.1f}W;;;0;{gpu.power_limit or ''}")
        if gpu.power_usage_percent is not None:
            perfdata_parts.append(f"{prefix}_power_pct={gpu.power_usage_percent:.1f}%;;;0;100")
        if gpu.utilization_gpu is not None:
            perfdata_parts.append(f"{prefix}_util={gpu.utilization_gpu}%;;;0;100")
        if gpu.utilization_memory is not None:
            perfdata_parts.append(f"{prefix}_mem_util={gpu.utilization_memory}%;;;0;100")
        if gpu.fan_speed is not None:
            perfdata_parts.append(f"{prefix}_fan={gpu.fan_speed}%;;;0;100")
    return " ".join(perfdata_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to monitor NVIDIA GPU stats via nvidia-smi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local check with defaults (NCPA executes this on monitored host)
  %(prog)s
  
  # Custom thresholds
  %(prog)s --warn-mem 80 --crit-mem 95 --warn-temp 80 --crit-temp 90
  
  # Output JSON for programmatic use
  %(prog)s --json
  
NCPA Configuration (on GPU host):
  # In ncpa.cfg [plugins] section:
  check_gpu = /usr/local/nagios/libexec/check_gpu_nvidia.py --warn-mem 80 --crit-mem 95

Nagios Server (check_ncpa):
  check_ncpa -H <gpu-host> -t <token> -M check_gpu
        """
    )
    
    # Connection options (kept for backward compat but ignored for NCPA local execution)
    parser.add_argument("-H", "--hostname", help="(Deprecated) Remote hostname - use NCPA local execution instead")
    parser.add_argument("-u", "--ssh-user", help="(Deprecated) SSH username")
    parser.add_argument("-i", "--ssh-key", help="(Deprecated) SSH private key path")
    parser.add_argument("-t", "--timeout", type=int, default=30, help="Command timeout (default: 30s)")
    
    # Threshold options (percentages)
    parser.add_argument("--warn-mem", type=int, default=80, help="Warning threshold for memory usage %% (default: 80)")
    parser.add_argument("--crit-mem", type=int, default=95, help="Critical threshold for memory usage %% (default: 95)")
    parser.add_argument("--warn-temp", type=int, default=80, help="Warning threshold for temperature °C (default: 80)")
    parser.add_argument("--crit-temp", type=int, default=90, help="Critical threshold for temperature °C (default: 90)")
    parser.add_argument("--warn-power", type=int, default=85, help="Warning threshold for power usage %% (default: 85)")
    parser.add_argument("--crit-power", type=int, default=95, help="Critical threshold for power usage %% (default: 95)")
    parser.add_argument("--warn-util", type=int, default=90, help="Warning threshold for GPU utilization %% (default: 90)")
    parser.add_argument("--crit-util", type=int, default=98, help="Critical threshold for GPU utilization %% (default: 98)")
    
    # Output options
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Nagios format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    try:
        # Run nvidia-smi locally (NCPA executes this on the monitored host)
        output = run_nvidia_smi(timeout=args.timeout)
        
        # Parse GPU info
        gpus = parse_nvidia_smi_output(output)
        
        if not gpus:
            print("UNKNOWN: No GPUs found or failed to parse nvidia-smi output")
            sys.exit(NagiosStatus.UNKNOWN)
        
        if args.json:
            # JSON output for programmatic use
            result = {
                "host": "localhost",
                "driver_version": gpus[0].driver_version if gpus else "unknown",
                "gpu_count": len(gpus),
                "gpus": [
                    {
                        "index": g.index,
                        "name": g.name,
                        "driver_version": g.driver_version,
                        "memory_total_mib": g.memory_total,
                        "memory_used_mib": g.memory_used,
                        "memory_free_mib": g.memory_free,
                        "memory_usage_percent": round(g.memory_usage_percent, 1),
                        "temperature_c": g.temperature,
                        "power_draw_w": g.power_draw,
                        "power_limit_w": g.power_limit,
                        "power_usage_percent": round(g.power_usage_percent, 1) if g.power_usage_percent else None,
                        "utilization_gpu_percent": g.utilization_gpu,
                        "utilization_memory_percent": g.utilization_memory,
                        "fan_speed_percent": g.fan_speed,
                    }
                    for g in gpus
                ]
            }
            print(json.dumps(result, indent=2))
            sys.exit(NagiosStatus.OK)
        
        # Evaluate thresholds
        status, messages = evaluate_thresholds(
            gpus, args.warn_mem, args.crit_mem,
            args.warn_temp, args.crit_temp,
            args.warn_power, args.crit_power,
            args.warn_util, args.crit_util
        )
        
        # Build output
        status_str = status.name
        summary = f"GPU {status_str} - localhost: {len(gpus)} GPU(s) | {build_perfdata(gpus)}"
        
        print(summary)
        if args.verbose or status != NagiosStatus.OK:
            for msg in messages:
                print(f"  {msg}")
        
        sys.exit(status)
        
    except RuntimeError as e:
        print(f"UNKNOWN: {e}")
        sys.exit(NagiosStatus.UNKNOWN)
    except Exception as e:
        print(f"UNKNOWN: Unexpected error: {e}")
        sys.exit(NagiosStatus.UNKNOWN)


if __name__ == "__main__":
    main()