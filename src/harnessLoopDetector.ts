/**
 * Clutch Agent 2.0 Harness Constraints: Loop Detector
 * Detects infinite tool call loops (e.g. calling failed fetch 3 times) and halts execution.
 */

export interface ToolCallRecord {
  toolName: string;
  argsHash: string;
  timestamp: number;
}

export class HarnessLoopDetector {
  private history: ToolCallRecord[] = [];
  private maxAllowedRepeats: number;

  constructor(maxAllowedRepeats = 3) {
    this.maxAllowedRepeats = maxAllowedRepeats;
  }

  /**
   * Check if calling toolName with args exceeds loop limits
   */
  public inspectToolCall(toolName: string, args: any): { isLooping: boolean; message?: string } {
    const argsHash = typeof args === 'string' ? args : JSON.stringify(args);
    const now = Date.now();

    this.history.push({ toolName, argsHash, timestamp: now });

    // Look for identical consecutive calls
    const recent = this.history.slice(-this.maxAllowedRepeats);
    if (recent.length >= this.maxAllowedRepeats) {
      const allIdentical = recent.every(r => r.toolName === toolName && r.argsHash === argsHash);
      if (allIdentical) {
        return {
          isLooping: true,
          message: `[HARNESS LOOP DETECTOR TRIGGERED] Tool '${toolName}' invoked ${this.maxAllowedRepeats} times with identical arguments. Halting execution to prevent infinite loop.`
        };
      }
    }

    return { isLooping: false };
  }

  public reset() {
    this.history = [];
  }
}
