import { isTauri } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

export class WorkspacePickerError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WorkspacePickerError';
  }
}

export async function pickWorkspaceFolder(title = 'Select project folder'): Promise<string | null> {
  if (!isTauri()) {
    throw new WorkspacePickerError(
      'Folder picker only works in the Clutch desktop app. Open Clutch from Applications, not the browser.',
    );
  }

  try {
    const selected = await open({
      directory: true,
      multiple: false,
      title,
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
