#!/bin/sh
set -eu
config=/data/sentinel.conf
if [ ! -s "$config" ]; then
  cat > "$config" <<EOF
port 26379
bind 0.0.0.0
protected-mode no
sentinel resolve-hostnames yes
sentinel announce-hostnames yes
sentinel announce-ip ${SENTINEL_HOSTNAME}
sentinel monitor mymaster 172.29.163.11 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 15000
sentinel parallel-syncs mymaster 1
EOF
fi
exec redis-sentinel "$config"
