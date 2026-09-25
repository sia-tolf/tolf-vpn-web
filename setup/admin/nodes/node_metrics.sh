#!/bin/sh
# Read-only resource snapshot for one VPN entry node.
set -eu
export LC_ALL=C

[ "$#" -eq 1 ] || exit 1
node=$1
host=$(cat /proc/sys/kernel/hostname)
case "$node:$host" in
    riga:EDISLV|moscow:OpenWrt) ;;
    *) exit 1 ;;
esac

cpu_sample() {
    awk '/^cpu / {
        total=0
        for (i=2; i<=9 && i<=NF; i++) total+=$i
        printf "%.0f %.0f\n", total, $5+$6
        exit
    }' /proc/stat
}

set -- $(cpu_sample)
total1=$1
idle1=$2
sleep 1
set -- $(cpu_sample)
total2=$1
idle2=$2

elapsed=$((total2 - total1))
idle=$((idle2 - idle1))
[ "$elapsed" -gt 0 ] || exit 1
cpu=$(((100 * (elapsed - idle) + elapsed / 2) / elapsed))

set -- $(awk '
    /^MemTotal:/ { total=$2 }
    /^MemAvailable:/ { available=$2 }
    END {
        if (total <= 0 || available < 0 || available > total) exit 1
        printf "%.0f %.0f\n", total*1024, (total-available)*1024
    }' /proc/meminfo)
memory_total=$1
memory_used=$2

set -- $(df -k / | awk '
    NR==2 {
        if ($2 <= 0 || $3 < 0 || $3 > $2) exit 1
        printf "%.0f %.0f\n", $2*1024, $3*1024
        found=1
    }
    END { if (!found) exit 1 }')
disk_total=$1
disk_used=$2

observed=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '{"version":"1.0.0","node":"%s","observedAt":"%s","cpuPercent":%s,"cpuTotalTicks":%s,"cpuIdleTicks":%s,"memoryTotalBytes":%s,"memoryUsedBytes":%s,"diskTotalBytes":%s,"diskUsedBytes":%s}\n' \
    "$node" "$observed" "$cpu" "$total2" "$idle2" "$memory_total" "$memory_used" "$disk_total" "$disk_used"
