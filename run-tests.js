import { runSelfTestSuite } from './src/testRunner.ts';

async function main() {
  const result = await runSelfTestSuite();
  console.log('\n--- FINAL TEST SUITE REPORT ---');
  console.log('Overall Status:', result.success ? 'PASSED ✅' : 'FAILED ❌');
  result.testResults.forEach(r => console.log(r));
  if (!result.success) process.exit(1);
}

main();
