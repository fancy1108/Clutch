import { pickWorkspaceFolder, WorkspacePickerError } from './pickWorkspaceFolder';

export { WorkspacePickerError };

export async function pickSkillsDirectory(): Promise<string | null> {
  return pickWorkspaceFolder('Select skills directory');
}
