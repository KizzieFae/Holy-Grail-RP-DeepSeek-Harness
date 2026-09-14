import { execFileSync } from 'node:child_process';

export function resolveGitProvenance(repoRoot) {
  let executionHead = null;
  let workingTreeDirty = false;
  let dirtyPaths = [];
  try {
    executionHead = execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: repoRoot,
      encoding: 'utf8',
    }).trim();
    const status = execFileSync('git', ['status', '--porcelain'], {
      cwd: repoRoot,
      encoding: 'utf8',
    }).trim();
    if (status) {
      workingTreeDirty = true;
      dirtyPaths = status
        .split('\n')
        .map((line) => line.slice(3).trim())
        .filter(Boolean);
    }
  } catch {
    // leave defaults when git is unavailable
  }
  return {
    execution_head: executionHead,
    working_tree_dirty: workingTreeDirty,
    dirty_paths: dirtyPaths,
    git_sha: executionHead,
  };
}
