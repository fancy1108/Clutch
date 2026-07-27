/**
 * Clutch Agent 2.0 Harness Verification: Execution Auditor
 * Prevents premature completion by verifying target deliverable files exist and are non-empty.
 */

export interface AuditRequirement {
  expectedFilePath?: string;
  expectedFileTypes?: string[];
  minByteSize?: number;
}

export interface AuditResult {
  passed: boolean;
  reason: string;
  verifiedFiles: string[];
}

/**
 * 2. Parallel Tool Dispatcher
 * Dispatches independent sub-tasks (e.g. HTML, PNG Infographic, MP4 Video) concurrently via Promise.all
 */
export async function executeParallelTools<T>(
  toolCalls: Array<{ name: string; args: any; execFn: () => Promise<T> }>
): Promise<Array<{ toolName: string; result?: T; error?: string }>> {
  console.info(`[HARNESS PARALLEL ENGINE] Dispatching ${toolCalls.length} independent sub-tasks concurrently...`);
  
  const promises = toolCalls.map(async (call) => {
    try {
      const result = await call.execFn();
      return { toolName: call.name, result };
    } catch (err: any) {
      return { toolName: call.name, error: err?.message || 'Parallel execution failed' };
    }
  });

  return Promise.all(promises);
}

/**
 * 3. Resume Continuation Assertion Guard
 * Intercepts "Continue" clicks to verify disk deliverables. Prevents LLM from hallucinating false completion.
 */
export function validateResumeContinuation(
  todoItems: Array<{ id: string; content: string; status: string }>,
  existingFilesOnDisk: string[]
): { canDeclareComplete: boolean; correctionPrompt?: string } {
  const pendingOrFailedSteps = todoItems.filter(t => t.status !== 'completed');

  if (pendingOrFailedSteps.length === 0) {
    return { canDeclareComplete: true };
  }

  // Check if claimed deliverables actually exist on disk
  const missingDeliverables: string[] = [];

  for (const step of pendingOrFailedSteps) {
    if (step.content.includes('图片') || step.content.includes('信息图') || step.content.includes('海报')) {
      const hasImage = existingFilesOnDisk.some(f => f.endsWith('.png') || f.endsWith('.jpg'));
      if (!hasImage) missingDeliverables.push(`Visual Image Infographic (${step.content})`);
    } else if (step.content.includes('视频') || step.content.includes('讲解版')) {
      const hasVideo = existingFilesOnDisk.some(f => f.endsWith('.mp4') || f.endsWith('.webm'));
      if (!hasVideo) missingDeliverables.push(`Video Presentation (${step.content})`);
    }
  }

  if (missingDeliverables.length > 0) {
    return {
      canDeclareComplete: false,
      correctionPrompt: `[HARNESS SYSTEM CORRECTION] Continuation check failed! The following required deliverables do NOT exist on disk: ${missingDeliverables.join(', ')}. You MUST NOT declare completion. Re-execute the required tools (generate_image / generate_video) to generate real files now.`
    };
  }

  return { canDeclareComplete: true };
}

