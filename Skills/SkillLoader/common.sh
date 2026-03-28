#!/usr/bin/env bash

resolve_target_dir() {
  local tool="$1"
  local repo_root="$2"
  case "$tool" in
    codex) printf "%s\n" "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    claude) printf "%s\n" "${CLAUDE_HOME:-$HOME/.claude}/skills" ;;
    cursor) printf "%s\n" "${CURSOR_HOME:-$HOME/.cursor}/skills" ;;
    antigravity) printf "%s\n" "${ANTIGRAVITY_HOME:-$HOME/.antigravity}/skills" ;;
    openclaw) printf "%s\n" "$repo_root/skills" ;;
    *)
      printf "Unsupported tool: %s\n" "$tool" >&2
      return 1
      ;;
  esac
}

deploy_skills() {
  local source_dir="$1"
  local target_dir="$2"
  local mode="$3"
  local dry_run="$4"
  local namespace_prefix="${NAMESPACE_PREFIX:-demodashboards}"

  if [ ! -d "$source_dir" ]; then
    printf "Source Skills folder not found: %s\n" "$source_dir" >&2
    return 1
  fi

  if [ "$dry_run" -eq 1 ]; then
    printf "[dry-run] mkdir -p %s\n" "$target_dir"
  else
    mkdir -p "$target_dir"
  fi

  local found=0
  while IFS= read -r marker; do
    found=1
    local skill_dir rel safe_name target_path
    skill_dir="$(dirname "$marker")"
    rel="${skill_dir#"$source_dir"/}"
    safe_name="$(echo "$rel" | tr '[:upper:]' '[:lower:]' | tr '/ _' '---' | tr -cd 'a-z0-9-')"
    safe_name="${namespace_prefix}-${safe_name}"
    target_path="$target_dir/$safe_name"

    if [ "$dry_run" -eq 1 ]; then
      printf "[dry-run] %s %s -> %s\n" "$mode" "$skill_dir" "$target_path"
      continue
    fi

    if [ -L "$target_path" ] || [ -e "$target_path" ]; then
      rm -rf "$target_path"
    fi

    if [ "$mode" = "symlink" ]; then
      ln -s "$skill_dir" "$target_path"
    else
      cp -R "$skill_dir" "$target_path"
    fi
    printf "Deployed: %s\n" "$rel"
  done < <(find "$source_dir" -type f \( -name "SKILL.md" -o -name "Skill.md" \) | sort)

  if [ "$found" -eq 0 ]; then
    printf "No skill markers found under %s (expected SKILL.md or Skill.md).\n" "$source_dir" >&2
    return 1
  fi
}

run_loader_for_tool() {
  local tool="$1"
  local repo_root="$2"
  local source_dir="$3"
  local mode="$4"
  local dry_run="$5"

  local target_dir
  target_dir="$(resolve_target_dir "$tool" "$repo_root")"
  printf "Target [%s]: %s\n" "$tool" "$target_dir"
  deploy_skills "$source_dir" "$target_dir" "$mode" "$dry_run"
}
