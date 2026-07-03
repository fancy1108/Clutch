import { invoke, isTauri } from '@tauri-apps/api/core';
import { homeDir } from '@tauri-apps/api/path';
import { open } from '@tauri-apps/plugin-dialog';

export class WorkspacePickerError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WorkspacePickerError';
  }
}

export async function pickWorkspaceFolder(
  title = 'Select project folder',
  defaultPath?: string,
  options?: { showHidden?: boolean },
): Promise<string | null> {
  if (!isTauri()) {
    throw new WorkspacePickerError(
      'Folder picker only works in the Clutch desktop app. Open Clutch from Applications, not the browser.',
    );
  }

  const e2eSandbox = await invoke<string | null>('clutch_e2e_sandbox');
  if (e2eSandbox) {
    return e2eSandbox;
  }

  let initialPath = defaultPath;
  if (!initialPath) {
    try {
      initialPath = await homeDir();
    } catch {
      initialPath = undefined;
    }
  }

  try {
    const hostOs = await invoke<string>('clutch_host_os');
    if (hostOs === 'macos' && options?.showHidden !== false) {
      return await invoke<string | null>('clutch_pick_directory', {
        title,
        defaultPath: initialPath,
        showHidden: true,
      });
    }

    const selected = await open({
      directory: true,
      multiple: false,
      title,
      defaultPath: initialPath,
    });
    if (selected === null || Array.isArray(selected)) {
      return null;
    }
    return selected;
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new WorkspacePickerError(`Could not open folder picker: ${detail}`);
  }
}
