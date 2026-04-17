#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function readClaudeLayout(packageJson) {
  return {
    sourceDir: packageJson.claudekit?.sourceDir || 'claude',
    runtimeDir: packageJson.claudekit?.runtimeDir || '.claude',
  };
}

function stageRuntimeClaudeDir(sourceClaudeDir, runtimeClaudeDir, runtimeDirLabel) {
  if (path.resolve(sourceClaudeDir) === path.resolve(runtimeClaudeDir)) {
    console.log(`✓ Reusing ${runtimeDirLabel} as the tracked source/runtime directory`);
    return;
  }

  fs.rmSync(runtimeClaudeDir, { recursive: true, force: true });
  fs.cpSync(sourceClaudeDir, runtimeClaudeDir, { recursive: true });
  console.log(`✓ Staged runtime ${runtimeDirLabel} from ${path.basename(sourceClaudeDir)}`);
}

/**
 * Generate metadata.json aligned with the package version and
 * bundle the release archive ahead of the semantic-release publish step.
 */
(function main() {
  const version = process.argv[2];

  if (!version) {
    console.error('✗ Missing required version argument for prepare-release-assets');
    process.exit(1);
  }

  const projectRoot = process.cwd();
  const packageJsonPath = path.join(projectRoot, 'package.json');
  const distDir = path.join(projectRoot, 'dist');
  const archivePath = path.join(distDir, 'claudekit-engineer.zip');
  const manifestPath = path.join(projectRoot, 'release-manifest.json');

  try {
    if (!fs.existsSync(packageJsonPath)) {
      throw new Error('package.json not found');
    }

    // Parse package.json with specific error handling
    let packageJson;
    try {
      packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    } catch (parseErr) {
      throw new Error(`Invalid JSON in package.json: ${parseErr.message}`);
    }

    if (packageJson.version !== version) {
      console.warn(
        `⚠️ package.json version (${packageJson.version}) does not match semantic-release version (${version}).`
      );
    }

    const requiredFields = ['name', 'description', 'repository'];
    const missingFields = requiredFields.filter((field) => !packageJson[field]);

    if (missingFields.length > 0) {
      throw new Error(`Missing required fields in package.json: ${missingFields.join(', ')}`);
    }

    const { sourceDir, runtimeDir } = readClaudeLayout(packageJson);
    const sourceClaudeDir = path.join(projectRoot, sourceDir);
    const runtimeClaudeDir = path.join(projectRoot, runtimeDir);
    const metadataPath = path.join(sourceClaudeDir, 'metadata.json');

    if (!fs.existsSync(sourceClaudeDir)) {
      throw new Error(`Claude source directory not found: ${sourceClaudeDir}`);
    }

    // Read existing metadata to preserve ALL custom fields
    let existingMetadata = {};
    if (fs.existsSync(metadataPath)) {
      try {
        existingMetadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
      } catch (parseErr) {
        console.warn('⚠️ Could not parse existing metadata.json, starting fresh');
      }
    }

    const metadata = {
      // Preserve ALL existing fields first
      ...existingMetadata,
      // Generated fields override existing (always update these)
      version: packageJson.version,
      name: packageJson.name,
      description: packageJson.description,
      buildDate: new Date().toISOString(),
      repository: packageJson.repository,
      download: {
        lastDownloadedAt: null,
        downloadedBy: null,
        installCount: 0,
      },
    };

    fs.writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`, 'utf8');
    console.log(`✓ Generated metadata.json with version ${metadata.version}`);

    // Generate OpenCode configuration from the tracked Claude source.
    console.log('Generating OpenCode configuration...');
    execSync('python3 scripts/generate-opencode.py --force', { stdio: 'inherit' });
    console.log('✓ Generated .opencode directory and AGENTS.md');

    // Generate release manifest against the tracked Claude source tree.
    console.log('Generating release manifest with timestamps...');
    execSync(`node scripts/generate-release-manifest.cjs "${version}"`, { stdio: 'inherit' });

    // Validate manifest was created successfully
    if (!fs.existsSync(manifestPath)) {
      throw new Error('release-manifest.json was not created by generate-release-manifest.cjs');
    }

    // Validate manifest is valid JSON
    try {
      JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    } catch (parseErr) {
      throw new Error(`release-manifest.json is not valid JSON: ${parseErr.message}`);
    }
    console.log('✓ Validated release-manifest.json');

    stageRuntimeClaudeDir(sourceClaudeDir, runtimeClaudeDir, runtimeDir);

    if (!fs.existsSync(distDir)) {
      fs.mkdirSync(distDir, { recursive: true });
    }

    // Delete existing archive with error handling
    if (fs.existsSync(archivePath)) {
      try {
        fs.unlinkSync(archivePath);
      } catch (unlinkErr) {
        throw new Error(`Cannot delete existing archive (file locked?): ${unlinkErr.message}`);
      }
    }

    const archiveTargets = [
      runtimeDir,
      '.opencode',
      'plans/templates',
      '.gitignore',
      '.repomixignore',
      '.mcp.json',
      'CLAUDE.md',
      'AGENTS.md',
      'release-manifest.json',
    ];

    const existingTargets = archiveTargets.filter((target) => fs.existsSync(path.join(projectRoot, target)));

    // Validate critical files are present
    const missingCritical = [runtimeDir, '.opencode', 'release-manifest.json'].filter(
      (target) => !fs.existsSync(path.join(projectRoot, target))
    );

    if (missingCritical.length > 0) {
      throw new Error(`Critical release assets missing: ${missingCritical.join(', ')}`);
    }

    if (existingTargets.length === 0) {
      throw new Error('No release assets found to include in archive.');
    }

    const zipCommand = ['zip', '-r', archivePath, ...existingTargets].join(' ');
    execSync(zipCommand, { stdio: 'inherit' });
    console.log(`✓ Prepared ${archivePath}`);
  } catch (error) {
    console.error(`✗ Failed to prepare release assets: ${error.message}`);
    process.exit(1);
  }
})();
