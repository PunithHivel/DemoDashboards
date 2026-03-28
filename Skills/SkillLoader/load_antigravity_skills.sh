#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${SKILLS_SOURCE:-$REPO_ROOT/Skills}"
MODE="${MODE:-symlink}"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

source "$SCRIPT_DIR/common.sh"
run_loader_for_tool "antigravity" "$REPO_ROOT" "$SOURCE_DIR" "$MODE" "$DRY_RUN"
