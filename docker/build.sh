#!/usr/bin/env bash
# Build how:<ref-safe> image from a git ref (tag/commit). Key never enters the image.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="${1:?usage: build.sh <git-ref> [image-tag]}"
SAFE_TAG="${2:-how-$(echo "$REF" | tr '/:' '--' | tr -cd 'A-Za-z0-9._-' | cut -c1-60)}"
STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

git -C "$ROOT" cat-file -e "${REF}:how" 2>/dev/null || {
  echo "error: ${REF}:how not found" >&2
  exit 1
}
git -C "$ROOT" show "${REF}:how" > "$STAGE/how"
chmod +x "$STAGE/how"
cp "$ROOT/docker/Dockerfile" "$STAGE/Dockerfile"

echo "Building $SAFE_TAG from ref $REF ..."
docker build -t "$SAFE_TAG" "$STAGE"
echo "OK $SAFE_TAG"
echo "$SAFE_TAG"
