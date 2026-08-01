import { useCallback, useEffect, useState } from 'react';
import {
  absoluteWorkspacePath,
  isHtmlWorkspacePath,
  openPathInSystem,
} from '../services/openInSystem';
import { pickWorkspaceFolder } from '../services/pickWorkspaceFolder';
import { workspaceMediaUrl } from '../services/sidecarUrl';
import { isImageWorkspacePath, isLargePreviewContent } from '../services/workspacePathLinks';
import {
  activateWorkspace,
  addWorkspace,
  createRepositoryGroup,
  deleteRepositoryGroup,
  fetchRepositoryGroups,
  fetchWorkspaceFile,
  fetchWorkspaceGit,
  fetchWorkspaceTree,
  fetchWorkspaces,
  removeWorkspace,
  resolveWorkspaceFile,
  updateRepositoryGroup,
  type FileTreeNode,
  type RepositoryGroup,
  type WorkspaceInfo,
} from '../services/workspaceApi';

export type AppPromptModalState = {
  isOpen: boolean;
  title: string;
  message?: string;
  hasInput?: boolean;
  placeholder?: string;
  defaultValue?: string;
  onConfirm: (value: string) => void;
};

type UseAppWorkspaceOptions = {
  t: (key: string) => string;
  setPromptModal: (modal: AppPromptModalState | null) => void;
  refreshSessions: () => Promise<void>;
};

export function useAppWorkspace({
  t,
  setPromptModal,
  refreshSessions,
}: UseAppWorkspaceOptions) {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [repositoryGroups, setRepositoryGroups] = useState<RepositoryGroup[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [workspaceFiles, setWorkspaceFiles] = useState<FileTreeNode[]>([]);
  const [workspacePickError, setWorkspacePickError] = useState<string | null>(null);
  const [workspaceGit, setWorkspaceGit] = useState<{ branch: string | null; branches: string[] }>({
    branch: null,
    branches: [],
  });

  const [previewFile, setPreviewFile] = useState<{
    name: string;
    content: string;
    plain?: boolean;
    mediaSrc?: string;
  } | null>(null);
  const [previewToast, setPreviewToast] = useState<string | null>(null);

  const refreshWorkspaceGit = useCallback(async () => {
    try {
      const info = await fetchWorkspaceGit();
      setWorkspaceGit({ branch: info.branch, branches: info.branches });
    } catch {
      setWorkspaceGit({ branch: null, branches: [] });
    }
  }, []);

  const refreshWorkspaceFiles = useCallback(async () => {
    try {
      const nodes = await fetchWorkspaceTree();
      setWorkspaceFiles(nodes);
    } catch {
      setWorkspaceFiles([]);
    }
  }, []);

  useEffect(() => {
    void fetchWorkspaces()
      .then(async (listed) => {
        setWorkspaces(listed.workspaces);
        setActiveWorkspaceId(listed.active_id);
        const active = listed.workspaces.find((item) => item.id === listed.active_id) ?? null;
        setWorkspace(active);
        if (active) {
          await refreshWorkspaceFiles();
          await refreshWorkspaceGit();
        }
      })
      .catch(() => {});
    void fetchRepositoryGroups()
      .then((listed) => setRepositoryGroups(listed.groups))
      .catch(() => {});
  }, [refreshWorkspaceFiles, refreshWorkspaceGit]);

  const handlePickWorkspace = useCallback(async () => {
    setWorkspacePickError(null);
    try {
      const path = await pickWorkspaceFolder(t('Select project folder'));
      if (!path) return;
      const info = await addWorkspace(path);
      const listed = await fetchWorkspaces();
      setWorkspaces(listed.workspaces);
      setActiveWorkspaceId(listed.active_id);
      setWorkspace(info);
      await refreshWorkspaceFiles();
      await refreshWorkspaceGit();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Workspace authorize failed';
      setWorkspacePickError(message);
      console.error('[Clutch] workspace authorize failed:', error);
    }
  }, [t, refreshWorkspaceFiles, refreshWorkspaceGit]);

  const handleSelectWorkspace = useCallback(async (workspaceId: string) => {
    try {
      const info = await activateWorkspace(workspaceId);
      setActiveWorkspaceId(workspaceId);
      setWorkspace(info);
      await refreshWorkspaceFiles();
      await refreshWorkspaceGit();
    } catch (error) {
      console.error('[Clutch] workspace switch failed:', error);
    }
  }, [refreshWorkspaceFiles, refreshWorkspaceGit]);

  const handleCreateRepositoryGroup = useCallback(() => {
    setPromptModal({
      isOpen: true,
      title: t('New project group'),
      placeholder: t('Enter group name...'),
      hasInput: true,
      defaultValue: '',
      onConfirm: async (name) => {
        setPromptModal(null);
        if (!name.trim()) return;
        try {
          const group = await createRepositoryGroup(name.trim());
          setRepositoryGroups((current) => [...current, group]);
        } catch (error) {
          console.error('[Clutch] create repository group failed:', error);
        }
      },
    });
  }, [setPromptModal, t]);

  const handleToggleRepositoryGroup = useCallback(async (groupId: string, collapsed: boolean) => {
    try {
      const updated = await updateRepositoryGroup(groupId, { collapsed });
      setRepositoryGroups((current) =>
        current.map((group) => (group.id === groupId ? updated : group)),
      );
    } catch (error) {
      console.error('[Clutch] update repository group failed:', error);
    }
  }, []);

  const handleDeleteRepositoryGroup = useCallback((groupId: string) => {
    setPromptModal({
      isOpen: true,
      title: t('Delete Group'),
      message: t('Are you sure you want to delete this group?'),
      hasInput: false,
      onConfirm: async () => {
        setPromptModal(null);
        try {
          await deleteRepositoryGroup(groupId);
          const listed = await fetchRepositoryGroups();
          setRepositoryGroups(listed.groups);
        } catch (error) {
          console.error('[Clutch] delete repository group failed:', error);
        }
      },
    });
  }, [setPromptModal, t]);

  const handleRenameRepositoryGroup = useCallback((groupId: string) => {
    const currentGroup = repositoryGroups.find((g) => g.id === groupId);
    if (!currentGroup) return;

    setPromptModal({
      isOpen: true,
      title: t('Rename Group'),
      placeholder: t('Enter new group name...'),
      defaultValue: currentGroup.name,
      hasInput: true,
      onConfirm: async (newName) => {
        setPromptModal(null);
        if (!newName.trim()) return;
        try {
          const updated = await updateRepositoryGroup(groupId, { name: newName.trim() });
          setRepositoryGroups((current) =>
            current.map((g) => (g.id === groupId ? updated : g)),
          );
        } catch (error) {
          console.error('[Clutch] rename repository group failed:', error);
        }
      },
    });
  }, [repositoryGroups, setPromptModal, t]);

  const handleMoveWorkspaceToGroup = useCallback(async (workspaceId: string, targetGroupId: string) => {
    const applyMove = (groups: RepositoryGroup[]) =>
      groups.map((group) => {
        const hasId = group.workspace_ids.includes(workspaceId);
        const isTarget = targetGroupId !== '__default__' && group.id === targetGroupId;

        if (isTarget && !hasId) {
          return { ...group, workspace_ids: [...group.workspace_ids, workspaceId] };
        }
        if (!isTarget && hasId) {
          return { ...group, workspace_ids: group.workspace_ids.filter((id) => id !== workspaceId) };
        }
        return group;
      });

    setRepositoryGroups(applyMove);

    try {
      for (const group of repositoryGroups) {
        const hasId = group.workspace_ids.includes(workspaceId);
        const isTarget = targetGroupId !== '__default__' && group.id === targetGroupId;

        if (isTarget && !hasId) {
          const newIds = [...group.workspace_ids, workspaceId];
          await updateRepositoryGroup(group.id, { workspace_ids: newIds });
        } else if (!isTarget && hasId) {
          const newIds = group.workspace_ids.filter((id) => id !== workspaceId);
          await updateRepositoryGroup(group.id, { workspace_ids: newIds });
        }
      }

      const listed = await fetchRepositoryGroups();
      setRepositoryGroups(listed.groups);
    } catch (error) {
      console.error('[Clutch] move workspace to group failed:', error);
      const listed = await fetchRepositoryGroups();
      setRepositoryGroups(listed.groups);
    }
  }, [repositoryGroups]);

  const handleOpenWorkspaceFile = useCallback(async (path: string) => {
    try {
      const resolved = await resolveWorkspaceFile(path);
      if (!resolved.ok) {
        setPreviewToast(
          resolved.reason === 'ambiguous'
            ? `Multiple files named “${path}” — open from Files instead.`
            : `File not found: ${path}`,
        );
        window.setTimeout(() => setPreviewToast(null), 3200);
        return;
      }
      if (isHtmlWorkspacePath(resolved.path)) {
        const abs = absoluteWorkspacePath(workspace?.workspace_path, resolved.path);
        if (!abs) {
          setPreviewToast(`Could not resolve path: ${resolved.path}`);
          window.setTimeout(() => setPreviewToast(null), 3200);
          return;
        }
        setPreviewFile(null);
        await openPathInSystem(abs);
        const leaf = resolved.path.split(/[/\\]/).pop() || resolved.path;
        setPreviewToast(`Opened in browser: ${leaf}`);
        window.setTimeout(() => setPreviewToast(null), 2800);
        return;
      }
      if (isImageWorkspacePath(resolved.path)) {
        const mediaSrc = await workspaceMediaUrl(resolved.path);
        setPreviewFile({
          name: resolved.path,
          content: '',
          mediaSrc,
        });
        return;
      }
      const content = await fetchWorkspaceFile(resolved.path);
      setPreviewFile({
        name: resolved.path,
        content,
        plain: isLargePreviewContent(content),
      });
    } catch (error) {
      console.error('[Clutch] read file failed:', error);
      setPreviewToast(`Could not open: ${path}`);
      window.setTimeout(() => setPreviewToast(null), 3200);
    }
  }, [workspace?.workspace_path]);

  const handlePreviewSnippet = useCallback((name: string, content: string) => {
    setPreviewFile({
      name,
      content,
      plain: isLargePreviewContent(content),
    });
  }, []);

  const handleDeleteWorkspace = useCallback((workspaceId: string) => {
    setPromptModal({
      isOpen: true,
      title: t('Delete project'),
      message: t('Are you sure you want to remove this project from the list?'),
      hasInput: false,
      onConfirm: async () => {
        setPromptModal(null);
        try {
          await removeWorkspace(workspaceId);
          const listed = await fetchWorkspaces();
          setWorkspaces(listed.workspaces);
          setActiveWorkspaceId(listed.active_id);
          const active = listed.workspaces.find((item) => item.id === listed.active_id) ?? null;
          setWorkspace(active);
          if (active) {
            await refreshWorkspaceFiles();
            await refreshWorkspaceGit();
          } else {
            setWorkspaceFiles([]);
            setWorkspaceGit({ branch: null, branches: [] });
          }
          const groupsListed = await fetchRepositoryGroups();
          setRepositoryGroups(groupsListed.groups);

          await refreshSessions();
        } catch (error) {
          console.error('[Clutch] remove workspace failed:', error);
        }
      },
    });
  }, [
    refreshSessions,
    refreshWorkspaceFiles,
    refreshWorkspaceGit,
    setPromptModal,
    t,
  ]);

  return {
    workspaces,
    repositoryGroups,
    activeWorkspaceId,
    workspace,
    workspaceFiles,
    workspacePickError,
    setWorkspacePickError,
    workspaceGit,
    previewFile,
    setPreviewFile,
    previewToast,
    refreshWorkspaceFiles,
    refreshWorkspaceGit,
    handlePickWorkspace,
    handleSelectWorkspace,
    handleCreateRepositoryGroup,
    handleToggleRepositoryGroup,
    handleDeleteRepositoryGroup,
    handleRenameRepositoryGroup,
    handleMoveWorkspaceToGroup,
    handleOpenWorkspaceFile,
    handlePreviewSnippet,
    handleDeleteWorkspace,
  };
}
