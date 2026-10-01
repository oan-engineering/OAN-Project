#!/usr/bin/env bash
# MinIO presigns browser-facing URLs and S3 SigV4 signs the Host header, so the
# endpoint has to be an address BOTH the containers and the Windows browser can
# reach. `minio` is docker-internal only; host.docker.internal is a Docker
# Desktop feature and this is plain Docker Engine under WSL. The WSL VM's eth0
# address satisfies both — but WSL reassigns it on reboot, so re-run this then
# `docker compose up -d staff-api partner-api`.
set -euo pipefail
cd "$(dirname "$0")/.."
ip=$(ip -4 addr show eth0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 || true)
[ -n "$ip" ] || ip=$(ip -4 addr show | awk '/inet 192\.|inet 172\.|inet 10\./ {print $2}' | head -n1 | cut -d/ -f1 || true)
[ -n "$ip" ] || ip="localhost"
sed -i -E "s|^(REGISTRY_(CORE|STAFF_PORTAL_API|PARTNER_API)_MINIO_ENDPOINT)=.*|\1=${ip}:9000|" local/env/local.env
# The staff portal's CSP must allow that same origin, or the browser blocks
# every record photo (img-src defaults to 'self').
if grep -q '^MINIO_PUBLIC_ORIGIN=' .env 2>/dev/null; then
  sed -i -E "s|^MINIO_PUBLIC_ORIGIN=.*|MINIO_PUBLIC_ORIGIN=http://${ip}:9000|" .env
else
  printf '\nMINIO_PUBLIC_ORIGIN=http://%s:9000\n' "$ip" >> .env
fi
echo "MinIO public endpoint set to ${ip}:9000 (env + CSP origin)"
