#!/usr/bin/env node
/**
 * Cross-platform script to create GitHub releases
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function exec(command, options = {}) {
  try {
    return execSync(command, { encoding: 'utf-8', stdio: 'pipe', ...options });
  } catch (error) {
    throw new Error(`Command failed: ${command}\n${error.message}`);
  }
}

function getCurrentVersion() {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf-8'));
  return packageJson.version;
}

function updateVersion(newVersion) {
  const packageJsonPath = 'package.json';
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
  packageJson.version = newVersion;
  fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + '\n');
  log(`✓ Updated package.json to version ${newVersion}`, 'green');
}

function validateVersion(version) {
  const semverRegex = /^(\d+)\.(\d+)\.(\d+)(-([a-zA-Z0-9-]+))?$/;
  return semverRegex.test(version);
}

function main() {
  log('========================================', 'green');
  log('GitHub Release Creator', 'green');
  log('========================================\n', 'green');

  // Check if gh CLI is installed
  try {
    exec('gh --version');
  } catch (error) {
    log('Error: GitHub CLI (gh) is not installed.', 'red');
    log('Install it from: https://cli.github.com/', 'yellow');
    process.exit(1);
  }

  // Check if authenticated
  try {
    exec('gh auth status');
  } catch (error) {
    log('Not authenticated. Please run: gh auth login', 'yellow');
    process.exit(1);
  }

  const currentVersion = getCurrentVersion();
  log(`Current version: ${currentVersion}\n`, 'blue');

  // Get new version from command line or prompt
  const args = process.argv.slice(2);
  let newVersion = args[0];

  if (!newVersion) {
    // In a real scenario, you'd use readline for input
    // For now, we'll require it as an argument
    log('Usage: npm run release <version>', 'yellow');
    log('Example: npm run release 1.0.1', 'yellow');
    process.exit(1);
  }

  // Validate version
  if (!validateVersion(newVersion)) {
    log(`Error: Invalid version format: ${newVersion}`, 'red');
    log('Use semantic versioning (e.g., 1.0.0)', 'yellow');
    process.exit(1);
  }

  // Update package.json
  log('\nUpdating package.json...', 'yellow');
  updateVersion(newVersion);

  // Build package
  log('Building package...', 'yellow');
  try {
    exec('npm run build', { stdio: 'inherit' });
    log('✓ Build successful', 'green');
  } catch (error) {
    log('✗ Build failed', 'red');
    process.exit(1);
  }

  // Get release notes
  let releaseNotes = args[1] || `Release v${newVersion}`;
  
  // Try to get from CHANGELOG.md
  try {
    const changelog = fs.readFileSync('CHANGELOG.md', 'utf-8');
    const versionMatch = changelog.match(new RegExp(`## \\[${newVersion}\\][^]*?## \\[`, 'm'));
    if (versionMatch) {
      releaseNotes = versionMatch[0].replace(/## \[.*?\]/g, '').trim();
    }
  } catch (error) {
    // CHANGELOG.md doesn't exist or can't be read
  }

  // Get current branch
  let currentBranch;
  try {
    currentBranch = exec('git rev-parse --abbrev-ref HEAD', { encoding: 'utf-8' }).trim();
  } catch (error) {
    currentBranch = 'main';
  }

  // Create git tag
  log('\nCreating git tag...', 'yellow');
  try {
    exec(`git add package.json`);
    try {
      exec(`git commit -m "chore: bump version to ${newVersion}"`, { stdio: 'ignore' });
    } catch (error) {
      log('No changes to commit', 'yellow');
    }
    
    // Check if tag already exists locally
    try {
      exec(`git rev-parse v${newVersion}`, { stdio: 'ignore' });
      log(`Tag v${newVersion} already exists locally`, 'yellow');
      // Delete local tag if it exists
      try {
        exec(`git tag -d v${newVersion}`, { stdio: 'ignore' });
        log('Deleted existing local tag', 'yellow');
      } catch (e) {
        // Tag might not exist locally
      }
    } catch (e) {
      // Tag doesn't exist, which is fine
    }
    
    // Create tag
    exec(`git tag -a v${newVersion} -m "Release v${newVersion}"`);
    log(`✓ Created tag v${newVersion}`, 'green');
    
    // Ask if user wants to push tag
    const readline = require('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    rl.question('Push tag to GitHub? (y/n): ', (answer) => {
      if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
        try {
          exec(`git push origin v${newVersion}`, { stdio: 'inherit' });
          exec(`git push origin ${currentBranch}`, { stdio: 'inherit' });
          log('✓ Pushed tag and commits', 'green');
        } catch (error) {
          log(`Warning: Failed to push: ${error.message}`, 'yellow');
        }
      } else {
        log('Skipping push. You can push manually later.', 'yellow');
      }
      rl.close();
      
      // Create release
      createRelease(newVersion, releaseNotes, currentBranch);
    });
  } catch (error) {
    log(`Error creating tag: ${error.message}`, 'red');
    process.exit(1);
  }
}

function createRelease(newVersion, releaseNotes, currentBranch) {
  log('\nCreating GitHub release...', 'yellow');
  try {
    // Check if tag exists remotely
    try {
      exec(`git ls-remote --tags origin v${newVersion}`, { stdio: 'ignore' });
      // Tag exists remotely, use it
      exec(`gh release create v${newVersion} --title "Release v${newVersion}" --notes "${releaseNotes}"`, {
        stdio: 'inherit'
      });
    } catch (error) {
      // Tag doesn't exist remotely, create release with --target flag
      exec(`gh release create v${newVersion} --title "Release v${newVersion}" --notes "${releaseNotes}" --target "${currentBranch}"`, {
        stdio: 'inherit'
      });
    }
    log('✓ Release created successfully!', 'green');
  } catch (error) {
    log(`✗ Failed to create release: ${error.message}`, 'red');
    log('\nTroubleshooting:', 'yellow');
    log('1. Make sure tag is pushed: git push origin v' + newVersion, 'yellow');
    log('2. Or delete local tag and recreate: git tag -d v' + newVersion, 'yellow');
    process.exit(1);
  }

  log('\n========================================', 'green');
  log('Release created successfully!', 'green');
  log('========================================\n', 'green');
  log(`Release: https://github.com/shanle1117/workshop2/releases/tag/v${newVersion}`, 'blue');
  log('\nThe package will be automatically published to GitHub Packages.', 'green');
}

if (require.main === module) {
  main();
}

module.exports = { main };

