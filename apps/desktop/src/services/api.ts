import { ChatMessage, UncommittedFile, RunStatus } from '../types';
import { initialChatMessages, initialTerminalLogs, uncommittedFiles } from '../mockData';

export { connectSidecarWebSocket, sendSidecarTestMessage } from './clutchState';

export const submitChatMessage = async (
  text: string, 
  currentFlowName: string,
  runStatus: string
): Promise<ChatMessage> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      let reply: ChatMessage;
      
      if (text.toLowerCase().includes('help') || text.toLowerCase().includes('status')) {
        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Orchestrator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
          time: timeNow,
          text: `Dynamic analysis scan initialized. Current pipeline status is set to: [${runStatus.toUpperCase()}]. Please use the right panel parameters to check specific state files.`
        };
      } else if (text.toLowerCase().includes('test') || text.toLowerCase().includes('verify')) {
        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Evaluator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
          time: timeNow,
          text: `Validation suite triggered automatically! Checking contrast conformance scores. Current reports are logged into terminal.`
        };
      } else {
        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Builder',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: timeNow,
          text: `Understood! I will analyze guidelines for task "${text}" immediately and incorporate instructions inside video-core modules.`,
          executionTime: '0.8s iteration'
        };
      }      
      resolve(reply);
    }, 1000);
  });
};

export const loadFlowState = async (
  flow: string
): Promise<{ 
  messages: ChatMessage[], 
  status: RunStatus, 
  logs: string[], 
  uncommitted: UncommittedFile[] 
}> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (flow === 'Missing bug fix in AI a...') {
        resolve({
          messages: [
            {
              id: 'bug-1',
              agent: 'Orchestrator',
              avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
              time: '12:10 PM',
              text: 'Initiated issue scan in target repository branch main: looking block parsing crashes in src/main.tsx.'
            },
            {
              id: 'bug-2',
              agent: 'Builder',
              avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
              time: '12:12 PM',
              text: 'Determined missing React import definition or JSX mismatch parameters. Resolving...',
            }
          ],
          status: 'passed',
          logs: [],
          uncommitted: []
        });
      } else if (flow === 'Video Production' || flow === 'Vibe coding workspac...') {
        resolve({
          messages: initialChatMessages,
          status: 'failed',
          logs: initialTerminalLogs,
          uncommitted: uncommittedFiles
        });
      } else {
        resolve({
          messages: [
            {
              id: 'gen-1',
              agent: 'Orchestrator',
              avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
              time: '2:15 PM',
              text: `Ready stream established. No active validation failures recorded inside ${flow}.`
            }
          ],
          status: 'passed',
          logs: [],
          uncommitted: []
        });
      }
    }, 500);
  });
};

export const approveNode = async (): Promise<{ messages: ChatMessage[], logs: string[] }> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        messages: [
          {
            id: `manual-approve-${Date.now()}`,
            agent: 'Supervisor',
            avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
            time: 'Just now',
            text: '⚠️ Manual Intervention Action: APPROVED. Bypassed validation hurdles, forced override approved. Proceeding to compilation success.'
          }
        ],
        logs: [
          `[SUPERVISOR] Manual override executed: APPROVED BY SUPERVISOR. Bypassing all current Evaluator gate violations.`,
          `[EVALUATOR] Overriding active failure block... Bypassed.`,
          `[EVALUATOR] SUCCESS: Compliance status set to PASSED manually.`
        ]
      });
    }, 500);
  });
};

export const rejectNode = async (): Promise<{ messages: ChatMessage[], logs: string[] }> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        messages: [
          {
            id: `manual-reject-${Date.now()}`,
            agent: 'Supervisor',
            avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
            time: 'Just now',
            text: '❌ Manual Intervention Action: REJECTED. Supervisor rejected the compiler artifact. Submitting error code metrics to automatic repair.'
          }
        ],
        logs: [
          `[SUPERVISOR] Manual override executed: REJECTED BY SUPERVISOR. Returning code to builder sandbox.`,
          `[ORCHESTRATOR] Received supervisor rejection report. Re-verifying index file state.`
        ]
      });
    }, 500);
  });
};

export const retryNodeWithInstructions = async (instructions: string): Promise<{ messages: ChatMessage[], logs: string[] }> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        messages: [
          {
            id: `manual-instruct-${Date.now()}`,
            agent: 'Supervisor',
            avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
            time: 'Just now',
            text: `✍️ Manual Intervention Override: Retrying execution workflow with instruction checklist: "${instructions}"`
          },
          {
            id: `repair-success-manual-${Date.now()}`,
            agent: 'Builder',
            avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
            time: 'Just now',
            text: `Compliance checks successfully passed! Applied instruction directive: "${instructions}". Standard validation linter ignored successfully.`,
            codeHighlight: {
              file: 'docs/verify.md & src/video-core/processor.ts',
              lineCount: 3
            }
          }
        ],
        logs: [
          `[SUPERVISOR] Manual instruction submitted: "${instructions}"`,
          `[ORCHESTRATOR] Translating instruction guidelines into active overrides...`,
          `[BUILDER] Re-compiling code artifacts with manual command rule: "${instructions}"`,
          `[BUILDER] Successfully generated hotpatch: "${instructions}". Bypassing original compiler restrictions.`,
          `[EVALUATOR] Spawning compliance test runner ...`,
          `[EVALUATOR] PASS: All overridden test routines completed successfully.`
        ]
      });
    }, 500);
  });
};

export const reassignToBuilder = async (): Promise<{ messages: ChatMessage[], logs: string[] }> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        messages: [
          {
            id: `repair-success-${Date.now()}`,
            agent: 'Builder',
            avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
            time: 'Just now',
            text: 'Missing type definitions added to `src/video-core/processor.ts`. Evaluator successfully passed regression checks.',
            codeHighlight: {
              file: 'src/video-core/processor.ts',
              lineCount: 2
            }
          }
        ],
        logs: [
          `[USER] Issued Re-assign to Builder command. Start Round 2 Repair.`,
          `[ORCHESTRATOR] Initializing hot patch subtask: Create missing verify.md`,
          `[BUILDER] Writing template checklist inside docs/verify.md...`,
          `[EVALUATOR] Re-testing updated module boundaries...`,
          `[EVALUATOR] Layout visually matches design reference.`,
          `[EVALUATOR] SUCCESS: Test suite PASSED.`
        ]
      });
    }, 500);
  });
};
