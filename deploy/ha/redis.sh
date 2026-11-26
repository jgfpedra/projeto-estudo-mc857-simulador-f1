#!/bin/sh
set -eu
config=/data/redis-ha.conf
if [ ! -s "$config" ]; then
    cat > "$config" <<'CONF'
bind 0.0.0.0
port 6379
protected-mode no
dir /data
appendonly yes
min-replicas-to-write 1
min-replicas-max-lag 5
CONF
    if [ -n "${INITIAL_REPLICA_OF:-}" ]; then
        printf 'replicaof %s 6379\n' "$INITIAL_REPLICA_OF" >> "$config"
    fi
fi
exec redis-server "$config"
