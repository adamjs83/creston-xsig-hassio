#!/usr/bin/env bash
# Build a release snapshot from the dev repo and commit it to a clone of the
# public repo as a single "Release vX.Y.Z" commit + tag.
#
# Usage: .github/publish/publish-public.sh <tag> <public-clone-dir>
#   - Run from the dev repo root, with <tag> checked out.
#   - <public-clone-dir> is an existing clone of the public repo (may be empty).
#   - Does not push; the caller pushes branch + tag.
set -euo pipefail

TAG="${1:?tag required (e.g. v1.25.4)}"
PUBLIC_DIR="${2:?public clone dir required}"
DEV_DIR="$(git rev-parse --show-toplevel)"
VERSION="${TAG#v}"
MANIFEST="custom_components/crestron/manifest.json"

# 1. Tag must match manifest version.
MANIFEST_VERSION="$(jq -r .version "${DEV_DIR}/${MANIFEST}")"
if [ "${VERSION}" != "${MANIFEST_VERSION}" ]; then
  echo "ERROR: tag ${TAG} does not match ${MANIFEST} version ${MANIFEST_VERSION}" >&2
  exit 1
fi

# 2. Tag must not already exist on public.
if git -C "${PUBLIC_DIR}" rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  echo "ERROR: tag ${TAG} already exists in public repo" >&2
  exit 1
fi

# 3. Export allowlisted, git-tracked paths only (no caches, no untracked files).
SNAPSHOT="$(mktemp -d)"
trap 'rm -rf "${SNAPSHOT}"' EXIT
mapfile -t PATHS < <(grep -vE '^\s*(#|$)' "${DEV_DIR}/.publish-include")
git -C "${DEV_DIR}" archive --format=tar HEAD -- "${PATHS[@]}" | tar -x -C "${SNAPSHOT}"

# 4. Strip dev-only blocks from markdown.
find "${SNAPSHOT}" -name '*.md' -print0 \
  | xargs -0 sed -i '/<!-- dev-only:start -->/,/<!-- dev-only:end -->/d'

# 5. Replace public tree with snapshot and commit.
cd "${PUBLIC_DIR}"
git checkout -q -B main
git rm -rq --ignore-unmatch -- . 
cp -a "${SNAPSHOT}/." .
git add -A

NOTES="$(awk -v v="${VERSION}" '
  $0 ~ "^## \\[" v "\\]" {f=1; next}
  /^## \[/ {f=0}
  f' "${DEV_DIR}/CHANGELOG.md")"

git commit -q -m "Release ${TAG}" -m "${NOTES:-Release ${TAG}}"
git tag -a "${TAG}" -m "Release ${TAG}"
echo "Committed and tagged ${TAG} in ${PUBLIC_DIR}"
