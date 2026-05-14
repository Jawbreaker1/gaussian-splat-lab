#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected_root="/Users/johanengwall/github_repos/gaussian-splat-lab"
main_project_root="/Users/johanengwall/github_repos/blender-ai-poc"

fail() {
  echo "phase0_validation=failed"
  echo "reason=$1"
  exit 1
}

echo "phase0_validation=start"
echo "repo_root=${repo_root}"

[[ "${repo_root}" == "${expected_root}" ]] || fail "repo is not checked out at expected sibling path"
[[ "${repo_root}" != "${main_project_root}" ]] || fail "repo root points at main Blender/3D project"
[[ -d "${repo_root}/.git" ]] || fail "missing local git repository"
[[ -d "${main_project_root}/.git" ]] || fail "main project path missing; expected sibling checkout"

required_files=(
  "README.md"
  "AGENTS.md"
  ".gitignore"
  "docs/phases.md"
  "docs/stage-0.md"
  "scripts/smoke-mac.sh"
  "scripts/smoke-rtx-worker.ps1"
  "scripts/validate-phase-0-rtx-worker.ps1"
  "data/manifests/.gitkeep"
)

for file in "${required_files[@]}"; do
  [[ -f "${repo_root}/${file}" ]] || fail "missing required file: ${file}"
done

ignored_paths=(
  "data/videos/example.mp4"
  "data/frames/frame001.png"
  "data/sfm/database.db"
  "data/checkpoints/model.ckpt"
  "data/splats/demo.ply"
  "artifacts/demo.bin"
  "outputs/out.txt"
  "logs/run.log"
)

for path in "${ignored_paths[@]}"; do
  git -C "${repo_root}" check-ignore -q "${path}" || fail "expected path is not ignored: ${path}"
done

tracked_heavy_patterns='^(data/(videos|frames|sfm|checkpoints|splats)/|artifacts/|outputs/|logs/)'
if git -C "${repo_root}" ls-files | grep -E "${tracked_heavy_patterns}" >/dev/null; then
  fail "heavy artifact path is tracked by git"
fi

if find "${repo_root}/scripts" -type f \
  \( -name '*.sh' -o -name '*.ps1' -o -name '*.py' -o -name '*.js' -o -name '*.ts' \) \
  ! -name 'validate-phase-0.sh' \
  -print0 \
  | xargs -0 grep --line-number \
    "/Users/johanengwall/github_repos/blender-ai-poc\\|blender-ai-poc" \
    >/tmp/phase0-main-project-runtime-refs.txt; then
  cat /tmp/phase0-main-project-runtime-refs.txt
  fail "runtime script references main project"
fi

"${repo_root}/scripts/smoke-mac.sh"

echo "phase0_validation=local_passed"
echo "rtx_worker_validation=manual_pending"
echo "next_required_command_on_windows=.\\scripts\\validate-phase-0-rtx-worker.ps1"
