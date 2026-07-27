/**
 * Clutch Agent 2.0 Code-Driven Deterministic State Machine
 * Guided by Obsidian Note: "深入理解AI Agent - 02 上下文工程.md"
 * Rule: State management MUST be code-driven by the Harness, never relying on LLM manual updates.
 */

export interface TodoItem {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export class CodeAgentStateMachine {
  private todos: TodoItem[] = [];

  constructor(initialTodos?: TodoItem[]) {
    if (initialTodos && initialTodos.length > 0) {
      this.todos = initialTodos;
    } else {
      this.todos = [
        { id: 'step-1', content: '搜集与筛选信息资料', status: 'completed' },
        { id: 'step-2', content: '撰写核心内容与脚本', status: 'completed' },
        { id: 'step-3', content: '生成可视化图片或视频产出', status: 'in_progress' }
      ];
    }
  }

  /**
   * Code-driven deterministic transition triggered directly by Tool Call Execution
   */
  public onToolExecuted(toolName: string, args?: any): TodoItem[] {
    if (toolName.includes('fetch') || toolName.includes('grep') || toolName.includes('search')) {
      this.setStepStatus(0, 'completed');
      this.setStepStatus(1, 'in_progress');
    } else if (toolName.includes('write_file') || toolName.includes('cat') || toolName.includes('edit')) {
      this.setStepStatus(0, 'completed');
      this.setStepStatus(1, 'completed');
      this.setStepStatus(2, 'in_progress');
    } else if (toolName.includes('generate_video') || toolName.includes('generate_image') || toolName.includes('media')) {
      // Automatic completion of prior steps when media generation tool finishes
      this.setStepStatus(0, 'completed');
      this.setStepStatus(1, 'completed');
      this.setStepStatus(2, 'completed');
    }

    return [...this.todos];
  }

  public finalizeTask(): TodoItem[] {
    return this.completeAll();
  }

  public completeAll(): TodoItem[] {
    this.todos = this.todos.map(t => ({ ...t, status: 'completed' }));
    return [...this.todos];
  }

  private setStepStatus(index: number, status: 'pending' | 'in_progress' | 'completed' | 'failed') {
    if (this.todos[index]) {
      this.todos[index].status = status;
    }
  }

  public getSnapshot(): TodoItem[] {
    return [...this.todos];
  }
}
