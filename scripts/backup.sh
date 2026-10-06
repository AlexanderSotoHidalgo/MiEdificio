#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
backup_root=${1:-"$repository_root/backups"}
case "$backup_root" in
  "$repository_root"/*) ;;
  *) echo "The backup destination must be inside $repository_root" >&2; exit 1 ;;
esac
mkdir -p "$backup_root"
stamp=$(date +%Y%m%d-%H%M%S)
db_container=$(docker compose ps -q db)
backend_container=$(docker compose ps -q backend)
test -n "$db_container" && test -n "$backend_container" || { echo "db and backend must be running" >&2; exit 1; }

docker exec "$db_container" pg_dump -U "${POSTGRES_USER:-miedificio}" -d "${POSTGRES_DB:-miedificio}" -Fc -f /tmp/miedificio.dump
docker cp "$db_container:/tmp/miedificio.dump" "$backup_root/database-$stamp.dump"
docker exec "$db_container" rm -f /tmp/miedificio.dump
docker exec "$backend_container" tar -czf /tmp/miedificio-receipts.tar.gz -C /data/uploads .
docker cp "$backend_container:/tmp/miedificio-receipts.tar.gz" "$backup_root/receipts-$stamp.tar.gz"
docker exec "$backend_container" rm -f /tmp/miedificio-receipts.tar.gz
echo "Backup completed in $backup_root"
