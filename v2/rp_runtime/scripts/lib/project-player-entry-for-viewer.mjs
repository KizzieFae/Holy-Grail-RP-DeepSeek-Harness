import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  defaultPythonExecutable,
  domainHostSpawnEnv,
} from '../../src/lib/runtime-config.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CLI_PATH = path.join(__dirname, 'project-player-entry-for-viewer.py');

/**
 * Project a persisted player user-turn history entry for a Character viewer.
 * Uses authoritative domain path: assemble_player_user_entry_for_viewer.
 */
export function projectPlayerEntryForViewer({
  entry,
  viewerCharacter,
  presentCharacters,
  perceptualSceneContext = null,
  playerCharacter = null,
  pythonExecutable = defaultPythonExecutable(),
} = {}) {
  const result = spawnSync(
    pythonExecutable,
    [CLI_PATH],
    {
      input: JSON.stringify({
        entry,
        viewer_character: viewerCharacter,
        present_characters: presentCharacters,
        perceptual_scene_context: perceptualSceneContext,
        player_character: playerCharacter,
      }),
      encoding: 'utf8',
      env: domainHostSpawnEnv(),
    },
  );
  if (result.status !== 0) {
    throw new Error(
      `project-player-entry-for-viewer failed (${result.status}): ${result.stderr || result.stdout}`,
    );
  }
  return JSON.parse(result.stdout);
}
