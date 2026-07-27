/**
 * Clutch Agent 2.0 Generic Multi-Agent Router & Context Distiller
 * Filters intermediate sub-agent tool logs and routes only distilled deliverables to main session.
 */

export interface AgentMessagePayload {
  sourceAgent: string;
  targetAgent: string;
  isInternalStep?: boolean;
  content: string;
  deliverablePath?: string;
}

export class GenericAgentRouter {
  private messageLog: AgentMessagePayload[] = [];

  /**
   * Route a message between agents, distilling internal tool logs
   */
  public routeMessage(payload: AgentMessagePayload): { shouldDeliverToMainSession: boolean; cleanContent: string } {
    this.messageLog.push(payload);

    // Filter out internal intermediate step logs from cluttering main session context
    if (payload.isInternalStep && !payload.deliverablePath) {
      return {
        shouldDeliverToMainSession: false,
        cleanContent: `[INTERNAL_STEP_DISTILLED] ${payload.sourceAgent} executed background tool task.`
      };
    }

    // Deliverable or user-facing response gets routed directly
    return {
      shouldDeliverToMainSession: true,
      cleanContent: payload.content
    };
  }

  public getRoutedLog(): AgentMessagePayload[] {
    return [...this.messageLog];
  }
}
