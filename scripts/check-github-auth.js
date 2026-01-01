#!/usr/bin/env node
/**
 * Check GitHub Packages authentication
 */

const { execSync } = require('child_process');

console.log('========================================');
console.log('GitHub Packages Authentication Check');
console.log('========================================\n');

// Check if GITHUB_TOKEN is set
const token = process.env.GITHUB_TOKEN;

if (!token) {
  console.error('❌ ERROR: GITHUB_TOKEN environment variable is not set!\n');
  console.log('Please set your GitHub Personal Access Token:');
  console.log('  Windows CMD:    set GITHUB_TOKEN=your_token_here');
  console.log('  Windows PowerShell: $env:GITHUB_TOKEN="your_token_here"');
  console.log('  Linux/Mac:      export GITHUB_TOKEN=your_token_here\n');
  console.log('Get a token at: https://github.com/settings/tokens');
  console.log('Required scopes: write:packages, read:packages, repo (if private)\n');
  process.exit(1);
}

console.log('✅ GITHUB_TOKEN is set');
console.log(`   Token length: ${token.length} characters\n`);

// Test authentication
try {
  console.log('Testing authentication...');
  const username = execSync('npm whoami --registry=https://npm.pkg.github.com', {
    encoding: 'utf-8',
    stdio: 'pipe'
  }).trim();
  
  console.log(`✅ Authenticated as: ${username}\n`);
  
  // Verify scope matches
  const packageJson = require('../package.json');
  const scope = packageJson.name.split('/')[0];
  const expectedScope = `@${username}`;
  
  if (scope !== expectedScope) {
    console.warn(`⚠️  WARNING: Package scope ${scope} doesn't match username @${username}`);
    console.warn(`   Package name: ${packageJson.name}`);
    console.warn(`   Expected: ${expectedScope}/faix-chatbot\n`);
  } else {
    console.log(`✅ Package scope matches username\n`);
  }
  
  console.log('========================================');
  console.log('✅ Authentication check passed!');
  console.log('You can now publish with: npm run publish:github');
  console.log('========================================\n');
  
} catch (error) {
  console.error('❌ Authentication failed!\n');
  console.error('Possible issues:');
  console.error('1. Token is invalid or expired');
  console.error('2. Token missing required scopes (write:packages, read:packages)');
  console.error('3. Token doesn\'t have access to the repository');
  console.error('\nGet a new token at: https://github.com/settings/tokens');
  console.error('Required scopes: write:packages, read:packages, repo (if private)\n');
  process.exit(1);
}

