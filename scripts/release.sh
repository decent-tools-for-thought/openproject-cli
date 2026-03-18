#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s <version>\n' "$0" >&2
  printf 'Example: %s 0.1.0\n' "$0" >&2
  exit 1
fi

version="$1"
tag="v${version}"
pkgname="openproject-cli"
asset="${pkgname}-${version}.tar.gz"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! command -v gh >/dev/null 2>&1; then
  printf 'gh CLI is required.\n' >&2
  exit 1
fi

if ! command -v makepkg >/dev/null 2>&1; then
  printf 'makepkg is required.\n' >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  printf 'Working tree must be clean before release.\n' >&2
  exit 1
fi

if ! git rev-parse "$tag" >/dev/null 2>&1; then
  git tag "$tag"
fi

if ! git ls-remote --tags origin "refs/tags/$tag" | grep -q "$tag"; then
  git push origin "$tag"
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

if ! gh release view "$tag" >/dev/null 2>&1; then
  gh release create "$tag" --title "$tag" --notes "Release $tag" --verify-tag
fi

repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
gh api \
  -H "Accept: application/vnd.github+json" \
  "/repos/$repo/tarball/$tag" \
  > "$tmpdir/$asset"

if ! gh release view "$tag" --json assets --jq ".assets[].name" | grep -qx "$asset"; then
  gh release upload "$tag" "$tmpdir/$asset"
fi

sha256="$(sha256sum "$tmpdir/$asset" | awk '{print $1}')"

pkgbuild="packaging/arch/PKGBUILD"
srcinfo="packaging/arch/.SRCINFO"

sed -i "s/^pkgver=.*/pkgver=${version}/" "$pkgbuild"
sed -i "s/^pkgrel=.*/pkgrel=1/" "$pkgbuild"
sed -i "s/^sha256sums=.*/sha256sums=('${sha256}')/" "$pkgbuild"

(
  cd packaging/arch
  makepkg --printsrcinfo > .SRCINFO
)

git add "$pkgbuild" "$srcinfo"
git commit -m "chore(arch): update package metadata for ${tag}"

printf '\nRelease %s created.\n' "$tag"
printf 'Asset: %s\n' "$asset"
printf 'SHA256: %s\n' "$sha256"
printf 'Committed updated Arch metadata locally. Push when ready.\n'
