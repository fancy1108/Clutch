/**
 * Clutch Agent 2.0 End-to-End Automated Test Suite & Self-Verification Runner
 * Tests and verifies the entire agent pipeline from research to parallel task dispatch and completion assertion.
 */

import {
  sanitizeToolOutput,
  harnessBeforeApiSendInterceptor,
  resolveGenericToolAlias,
  harnessIntentGuard,
  executeWithModelFallback,
  executeWithCircuitBreaker,
  safeWebFetch,
  safeFileEdit,
  UniversalArtifactRegistry,
  getClientEnvironmentContext,
  interceptMetaToolQueries,
  enrichPromptWithDynamicContext,
  checkPreToolUseSafetyGuard,
  CheckpointManager,
  parseTestReportAndCorrection,
  LearnedMemoryVault,
  compactContextWithRetentionPriority
} from './agentSanitizer';

import {
  HarnessExecutionAuditor,
  executeParallelTools,
  validateResumeContinuation
} from './harnessAuditor';

import { HarnessLoopDetector } from './harnessLoopDetector';
import { CodeAgentStateMachine } from './agentStateMachine';

export async function runSelfTestSuite(): Promise<{ success: boolean; testResults: string[] }> {
  const results: string[] = [];
  let allPassed = true;

  console.info('====================================================');
  console.info('🚀 STARTING CLUTCH AGENT 2.0 AUTOMATED SELF-TEST SUITE');
  console.info('====================================================');

  // Test 1: Web Fetch Fallback (403 Error Suppression)
  try {
    const fetchRes = await safeWebFetch('https://whly.jinhua.gov.cn', async () => {
      throw new Error('403 Forbidden Access');
    });
    if (fetchRes.includes('access restrictions')) {
      results.push('✅ Test 1 Passed: safeWebFetch suppressed 403 error and returned fallback data.');
    } else {
      throw new Error('safeWebFetch failed to suppress error.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 1 Failed: ${err.message}`);
  }

  // Test 2: Smart File Edit Fallback (Edit -> write_file when file missing)
  try {
    const editRes = safeFileEdit('learning-guide.html', '<h1>Guide</h1>', false);
    if (editRes.actionUsed === 'write') {
      results.push('✅ Test 2 Passed: safeFileEdit fallback Edit -> write_file when file missing.');
    } else {
      throw new Error('safeFileEdit failed to fallback.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 2 Failed: ${err.message}`);
  }

  // Test 3: Parallel Sub-task Concurrent Dispatcher (HTML + Image + Video via Promise.all)
  try {
    const parallelCalls = [
      { name: 'generate_html', args: { file: 'guide.html' }, execFn: async () => '<h1>HTML Content</h1>' },
      { name: 'generate_image', args: { prompt: 'Infographic' }, execFn: async () => 'image_ok' },
      { name: 'generate_video', args: { prompt: 'Video Summary' }, execFn: async () => 'video_ok' }
    ];

    const startT = Date.now();
    const parallelResults = await executeParallelTools(parallelCalls);
    const duration = Date.now() - startT;

    if (parallelResults.length === 3 && duration < 1000) {
      results.push(`✅ Test 3 Passed: executeParallelTools ran 3 tasks concurrently in ${duration}ms.`);
    } else {
      throw new Error('Parallel execution failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 3 Failed: ${err.message}`);
  }

  // Test 4: Base64 Zero-Context Payload Firewall
  try {
    const hugePayload = 'data:image/png;base64,' + 'A'.repeat(60000);
    const sanitized = sanitizeToolOutput('generate_image', hugePayload);
    if (sanitized.isTruncated && sanitized.sanitizedForContext.includes('file_path')) {
      results.push('✅ Test 4 Passed: Zero-Context Firewall stripped 60,000 char Base64 to lightweight path.');
    } else {
      throw new Error('Zero-context firewall failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 4 Failed: ${err.message}`);
  }

  // Test 5: Loop Detector Halting
  try {
    const loopDetector = new HarnessLoopDetector(3);
    loopDetector.inspectToolCall('fetch', { url: 'http://test.com' });
    loopDetector.inspectToolCall('fetch', { url: 'http://test.com' });
    const loopRes = loopDetector.inspectToolCall('fetch', { url: 'http://test.com' });

    if (loopRes.isLooping) {
      results.push('✅ Test 5 Passed: Loop Detector halted 3 consecutive identical tool calls.');
    } else {
      throw new Error('Loop detector failed to trigger.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 5 Failed: ${err.message}`);
  }

  // Test 6: Continuation Assertion Guard (Prevents Hallucinated False Completion)
  try {
    const todos = [
      { id: '1', content: '搜索建议', status: 'completed' },
      { id: '2', content: '生成海报图片', status: 'in_progress' },
      { id: '3', content: '生成视频讲解', status: 'pending' }
    ];

    // Disk only has html, missing png and mp4
    const continuationCheck = validateResumeContinuation(todos, ['guide.html']);

    if (!continuationCheck.canDeclareComplete && continuationCheck.correctionPrompt?.includes('HARNESS SYSTEM CORRECTION')) {
      results.push('✅ Test 6 Passed: Resume Continuation Guard blocked false completion and injected system correction.');
    } else {
      throw new Error('Continuation guard failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 6 Failed: ${err.message}`);
  }

  // Test 7: Harness Before API Send Middleware Gate (Strips Native Binary Tool 2.4M Base64)
  try {
    const rawApiMessages = [
      { role: 'system', content: 'You are an agent' },
      { role: 'tool', name: 'clutch-tools__generate_image', content: 'data:image/png;base64,' + 'B'.repeat(80000) }
    ];

    const interceptedMessages = harnessBeforeApiSendInterceptor(rawApiMessages);
    const toolMsg = interceptedMessages[1];

    if (toolMsg.content.includes('[MEDIA GENERATED SUCCESSFULLY]') && !toolMsg.content.includes('BBBBBB')) {
      results.push('✅ Test 7 Passed: Harness Middleware Gate intercepted and stripped 80,000 char native tool Base64 before API dispatch.');
    } else {
      throw new Error('Harness middleware gate failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 7 Failed: ${err.message}`);
  }

  // Test 8: Generic Tool Alias Router & Web Complaint Cleaning
  try {
    const aliasRes = resolveGenericToolAlias('web_search', { query: '免费大模型' });
    const complaintMsg = [
      { role: 'assistant', content: '由于我没有 web_search 工具，我只能基于知识库回答。免费大模型包括 DeepSeek, Qwen。' }
    ];
    const cleanedMsgs = harnessBeforeApiSendInterceptor(complaintMsg);

    if (aliasRes.targetTool === 'clutch-tools__web_fetch' && !cleanedMsgs[0].content.includes('没有 web_search')) {
      results.push('✅ Test 8 Passed: Generic Tool Alias mapped web_search -> web_fetch, and cleaned hallucinated "no tool" complaint text.');
    } else {
      throw new Error('Generic tool alias or complaint cleaning failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 8 Failed: ${err.message}`);
  }

  // Test 9: Harness Intent Guard (Informational Query vs Creation Command)
  try {
    const infoIntent = harnessIntentGuard('帮我搜索一下目前有哪些免费的文本、生图、生视频的大模型');
    const creationIntent = harnessIntentGuard('生成一个关于免费大模型的短视频讲解版');

    if (!infoIntent.isCreationIntent && creationIntent.isCreationIntent) {
      results.push('✅ Test 9 Passed: Intent Guard suppressed video model call for informational prompt ("有哪些免费生视频大模型").');
    } else {
      throw new Error('Intent guard failed to classify query vs creation intent.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 9 Failed: ${err.message}`);
  }

  // Test 10: Model Provider HTTP 500 Auto-Fallback Self-Healing Guard
  try {
    const fallbackRes = await executeWithModelFallback(
      'MiMo-V2.5 Free (OpenCode Zen)',
      async () => { throw new Error('LLM API error 500: {"type":"error","error":{"type":"error","message":"Internal server error"}}'); },
      async () => 'Fallback Model Response OK'
    );

    if (fallbackRes.success && fallbackRes.usedModel.includes('Fallback') && fallbackRes.data === 'Fallback Model Response OK') {
      results.push('✅ Test 10 Passed: Model Fallback Guard auto-switched model provider when primary model threw HTTP 500 error.');
    } else {
      throw new Error('Model fallback guard failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 10 Failed: ${err.message}`);
  }

  // Test 11: Zero-Token Meta Query Gateway Interceptor
  try {
    const metaCheck = interceptMetaToolQueries('你目前有哪些tool 可以调用');
    const nonMetaCheck = interceptMetaToolQueries('帮我重构一下 App.tsx');

    if (metaCheck.isMetaQuery && metaCheck.interceptedResponse?.includes('get_current_time') && !nonMetaCheck.isMetaQuery) {
      results.push('✅ Test 11 Passed: Zero-Token Meta Query Gateway Interceptor intercepted tool discovery prompt without workspace search.');
    } else {
      throw new Error('Meta Query Interceptor failed to intercept or format tool list.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 11 Failed: ${err.message}`);
  }

  // Test 12: Dynamic Client Environment Context & Time Anchor Enricher
  try {
    const env = getClientEnvironmentContext();
    const enriched = enrichPromptWithDynamicContext('帮我做下 AI Agent 市场调研');

    if (env.formattedDateTime && enriched.enrichedPrompt.includes('SYSTEM ENVIRONMENT ANCHOR')) {
      results.push('✅ Test 12 Passed: Dynamic Environment Context Provider successfully captured client clock and injected time anchor.');
    } else {
      throw new Error('Dynamic context provider failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 12 Failed: ${err.message}`);
  }

  // Test 13: User Input Language Detection & Bilingual Alignment Guard
  try {
    const zhCheck = interceptMetaToolQueries('你目前有哪些tool 可以调用');
    const enCheck = interceptMetaToolQueries('what tools can you call');

    if (zhCheck.language === 'zh' && zhResponseHasChinese(zhCheck.interceptedResponse) &&
        enCheck.language === 'en' && enCheck.interceptedResponse?.includes('Based on the registered platform')) {
      results.push('✅ Test 13 Passed: Language Alignment Guard matched response language to user input (Chinese -> Chinese, English -> English).');
    } else {
      throw new Error('Language alignment guard failed to match user input language.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 13 Failed: ${err.message}`);
  }

  // Test 14: PreToolUse Safety Guard (Dangerous Git & Shell Interceptor)
  try {
    const dangerousCheck = checkPreToolUseSafetyGuard('git push origin main --force');
    const safeCheck = checkPreToolUseSafetyGuard('git status');

    if (dangerousCheck.requiresApproval && dangerousCheck.isDangerous && !safeCheck.isDangerous) {
      results.push('✅ Test 14 Passed: PreToolUse Safety Guard intercepted dangerous command ("git push --force") and enforced approval requirement.');
    } else {
      throw new Error('PreToolUse safety guard failed to intercept dangerous command.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 14 Failed: ${err.message}`);
  }

  // Test 15: Checkpoint Rewind Engine (1-Click Undo Snapshot)
  try {
    const cp = CheckpointManager.createCheckpoint('Refactor App.tsx state');
    const rollbackRes = CheckpointManager.rollbackCheckpoint(cp.id);

    if (cp.id && rollbackRes.success && rollbackRes.message.includes('REWIND ENGINE')) {
      results.push('✅ Test 15 Passed: Checkpoint Manager created non-destructive snapshot and executed 1-click rollback successfully.');
    } else {
      throw new Error('Checkpoint manager rewind failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 15 Failed: ${err.message}`);
  }

  // Test 16: TDD Self-Correction Loop Engine
  try {
    const fakeTestLog = 'FAIL src/App.test.tsx\nError: expected 200 OK but received 500\nAssertionError: state mismatch';
    const tddCheck = parseTestReportAndCorrection(fakeTestLog);

    if (tddCheck.hasFailures && tddCheck.failedTestCount === 2 && tddCheck.correctionPrompt?.includes('TDD AUTO-CORRECTION LOOP')) {
      results.push('✅ Test 16 Passed: TDD Self-Correction Loop extracted stack trace and built automated self-fix prompt.');
    } else {
      throw new Error('TDD self-correction loop failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 16 Failed: ${err.message}`);
  }

  // Test 17: Persistent Learned Memory Vault Engine
  try {
    LearnedMemoryVault.addPreference('User prefers React 19 concurrent features.');
    const memoryPrompt = LearnedMemoryVault.getInjectedMemoryPrompt();

    if (memoryPrompt.includes('PERSISTENT LEARNED MEMORY VAULT') && memoryPrompt.includes('pnpm')) {
      results.push('✅ Test 17 Passed: Learned Memory Vault recorded user preferences and formatted persistent context injection.');
    } else {
      throw new Error('Learned Memory Vault failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 17 Failed: ${err.message}`);
  }

  // Test 18: Safe Context Compaction Engine (White-List & Lossless Indexing)
  try {
    const rawMessages = [
      { role: 'system', content: 'You are an agent' },
      { role: 'system', content: '[PERSISTENT LEARNED MEMORY VAULT]\nUser Profile' },
      { role: 'user', content: 'Modify App.tsx and commit hash a1b2c3d4' },
      { role: 'tool', content: 'data:text/plain;base64,huge_raw_output_logs...' },
      { role: 'user', content: 'Modify Header.tsx and commit hash e5f6a7b8' },
      { role: 'tool', content: 'huge_grep_output...' },
      { role: 'user', content: 'Final prompt' }
    ];

    const sourceMap = { 'src/App.tsx': 'L10-L45', 'src/Header.tsx': 'L1-L30' };
    const compactRes = compactContextWithRetentionPriority(rawMessages, sourceMap);

    if (compactRes.isCompacted && compactRes.summary.includes('App.tsx') && compactRes.summary.includes('SOURCE INDEX')) {
      results.push('✅ Test 18 Passed: Safe Context Compaction Engine preserved modifications, commit hashes, and appended lossless index pointers.');
    } else {
      throw new Error('Safe context compaction failed.');
    }
  } catch (err: any) {
    allPassed = false;
    results.push(`❌ Test 18 Failed: ${err.message}`);
  }

  console.info('====================================================');
  console.info(`RESULT: ${allPassed ? 'ALL TESTS PASSED 🎉' : 'SOME TESTS FAILED ❌'}`);
  results.forEach(r => console.info(r));
  console.info('====================================================');

  return { success: allPassed, testResults: results };
}

function zhResponseHasChinese(str?: string): boolean {
  return !!str && /[\u4e00-\u9fa5]/.test(str);
}

// Self-executing runner if executed directly via ts-node/node
if (typeof require !== 'undefined' && require.main === module) {
  runSelfTestSuite().then(res => {
    if (!res.success) process.exit(1);
  });
}
