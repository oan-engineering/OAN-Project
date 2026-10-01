#!/usr/bin/env bash
# Build the four Crop Sown Registry images and push them to a container registry.
#
# The images are thin extensions of the openg2p-registry base images pinned by
# ARG RP_VERSION in each Dockerfile. Three of them pip-install the extension
# package; db-seed only copies seed content, so it takes no build arg.
#
# The build context is ALWAYS the repository root — every Dockerfile copies from
# cropsown-extension/ — which is why this script cd's there regardless of where
# it is invoked from.
#
# Usage:
#   ./scripts/build-and-push.sh <namespace> <tag> [image ...]
#   NS=rediet03 TAG=0.1.0 ./scripts/build-and-push.sh
#
#   ./scripts/build-and-push.sh rediet03 0.1.0            # all four
#   ./scripts/build-and-push.sh rediet03 0.1.0 db-seed    # just one
#   PUSH=false ./scripts/build-and-push.sh rediet03 dev   # build only
#   LATEST=true ./scripts/build-and-push.sh rediet03 0.1.0
#
# Env:
#   NS                namespace, e.g. a Docker Hub account
#   TAG               image tag
#   PUSH              set false to build without pushing (default true)
#   LATEST            set true to also tag and push :latest (default false)
#   PLATFORM          e.g. linux/amd64 to cross-build (uses buildx)
#   PIP_TRUSTED_HOST  passed to the three pip-installing images; needed on
#                     networks that intercept TLS
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

NS="${1:-${NS:-}}"
TAG="${2:-${TAG:-}}"
shift 2 2>/dev/null || true
IMAGES=("$@")
[ ${#IMAGES[@]} -eq 0 ] && IMAGES=(staff-api partner-api celery db-seed)

PUSH="${PUSH:-true}"
LATEST="${LATEST:-false}"
PLATFORM="${PLATFORM:-}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-}"

if [ -z "$NS" ] || [ -z "$TAG" ]; then
  echo "usage: $0 <namespace> <tag> [image ...]" >&2
  echo "   or: NS=<namespace> TAG=<tag> $0" >&2
  exit 2
fi

die()  { echo "ERROR: $*" >&2; exit 1; }
note() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# Fail before building rather than after, when a name is wrong.
for img in "${IMAGES[@]}"; do
  [ -f "docker/$img/Dockerfile" ] || die "no Dockerfile at docker/$img/Dockerfile"
done

if [ "$PUSH" = "true" ]; then
  docker info 2>/dev/null | grep -q "Username:" \
    || echo "note: no docker login detected — push will fail if the namespace is private"
fi

BUILD=(docker build)
if [ -n "$PLATFORM" ]; then
  BUILD=(docker buildx build --platform "$PLATFORM" --load)
fi

built=()
for img in "${IMAGES[@]}"; do
  ref="$NS/cropsown-$img:$TAG"
  note "build $ref"

  args=()
  # db-seed has no pip install and declares no such ARG; passing it warns.
  if [ "$img" != "db-seed" ] && [ -n "$PIP_TRUSTED_HOST" ]; then
    args+=(--build-arg "PIP_TRUSTED_HOST=$PIP_TRUSTED_HOST")
  fi

  "${BUILD[@]}" -f "docker/$img/Dockerfile" "${args[@]}" -t "$ref" . \
    || die "build failed: $img"
  built+=("$ref")

  if [ "$LATEST" = "true" ]; then
    docker tag "$ref" "$NS/cropsown-$img:latest"
  fi
done

if [ "$PUSH" != "true" ]; then
  note "built ${#built[@]} image(s); PUSH=false, nothing pushed"
  printf '  %s\n' "${built[@]}"
  exit 0
fi

for img in "${IMAGES[@]}"; do
  ref="$NS/cropsown-$img:$TAG"
  note "push $ref"
  docker push "$ref" || die "push failed: $ref"
  if [ "$LATEST" = "true" ]; then
    docker push "$NS/cropsown-$img:latest" || die "push failed: $NS/cropsown-$img:latest"
  fi
done

# Read back from the registry, not the local cache, so this proves the push.
note "verify"
fail=0
for img in "${IMAGES[@]}"; do
  ref="$NS/cropsown-$img:$TAG"
  if docker manifest inspect "$ref" >/dev/null 2>&1; then
    echo "  ok       $ref"
  else
    echo "  MISSING  $ref"; fail=1
  fi
done
[ "$fail" -eq 0 ] || die "one or more images are not in the registry"

note "done — ${#IMAGES[@]} image(s) published to $NS"
