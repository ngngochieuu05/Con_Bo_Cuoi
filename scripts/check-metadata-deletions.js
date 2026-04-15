#!/usr/bin/env node
/**
 * check-metadata-deletions.js
 *
 * CI gate: verifies that every file deleted or renamed under claude/ in this PR
 * has a corresponding entry in claude/metadata.json deletions[] array.
 *
 * Usage: node scripts/check-metadata-deletions.js
 * Exit 0 = all accounted for (or no claude/ deletions in diff)
 * Exit 1 = missing entries found
 */

'use strict';

const { execSync } = require('child_process');
const { readFileSync } = require('fs');
const path = require('path');

// Resolve repo root relative to this script's location
const repoRoot = path.resolve(__dirname, '..');

// Allowed base ref values (prevent shell injection via GITHUB_BASE_REF)
const ALLOWED_BASES = new Set(['dev', 'main']);

/**
 * Determine the diff baseline branch from CI environment or default to dev.
 */
function getBaseRef() {
  const envRef = process.env.GITHUB_BASE_REF;
  if (envRef && ALLOWED_BASES.has(envRef)) return envRef;
  return 'dev';
}

/**
 * Returns paths deleted or renamed under claude/ in diff against the base branch.
 * Both sides of a rename (old path) are checked.
 */
function getDeletedClaudePaths() {
  const baseRef = getBaseRef();
  let diff;
  try {
    diff = execSync(`git diff --name-status origin/${baseRef}`, {
      cwd: repoRoot,
      encoding: 'utf8',
    });
  } catch (err) {
    console.error(`[X] Could not run git diff against origin/${baseRef}: ${err.message}`);
    // Fail-closed: if we can't determine the diff, reject rather than silently pass
    process.exit(1);
  }

  const deleted = new Set();

  for (const line of diff.split('\n')) {
    if (!line.trim()) continue;

    const parts = line.split('\t');
    const status = parts[0];

    if (status === 'D') {
      const filePath = parts[1];
      if (filePath && filePath.startsWith('claude/')) {
        deleted.add(filePath.slice('claude/'.length));
      }
    } else if (status.startsWith('R')) {
      const oldPath = parts[1];
      if (oldPath && oldPath.startsWith('claude/')) {
        deleted.add(oldPath.slice('claude/'.length));
      }
    }
  }

  return deleted;
}

/**
 * Check if a file path matches a deletion entry.
 * Supports exact match and glob patterns ending with /** (directory wildcard).
 */
function matchesDeletion(filePath, entry) {
  if (entry === filePath) return true;
  // Support "dir/**" glob — matches any file under that directory
  if (entry.endsWith('/**')) {
    const prefix = entry.slice(0, -2); // strip "**", keep trailing slash
    return filePath.startsWith(prefix);
  }
  return false;
}

/**
 * Reads claude/metadata.json and returns the deletions array (normalized).
 */
function getRegisteredDeletions() {
  const metaPath = path.join(repoRoot, 'claude', 'metadata.json');
  let meta;
  try {
    meta = JSON.parse(readFileSync(metaPath, 'utf8'));
  } catch (err) {
    console.error('[X] Failed to read claude/metadata.json:', err.message);
    process.exit(1);
  }

  const entries = Array.isArray(meta.deletions) ? meta.deletions : [];
  // Normalize: strip leading "claude/" if present
  return entries.map((e) => (e.startsWith('claude/') ? e.slice('claude/'.length) : e));
}

function main() {
  const deleted = getDeletedClaudePaths();

  if (deleted.size === 0) {
    console.log('[OK] No deleted/renamed files under claude/ — nothing to check.');
    process.exit(0);
  }

  const deletionEntries = getRegisteredDeletions();
  const missing = [];

  for (const filePath of deleted) {
    const matched = deletionEntries.some((entry) => matchesDeletion(filePath, entry));
    if (!matched) {
      missing.push(filePath);
    }
  }

  if (missing.length === 0) {
    console.log(`[OK] All ${deleted.size} deleted/renamed claude/ path(s) are registered in metadata.json.`);
    process.exit(0);
  }

  console.error('[X] metadata-deletions check FAILED');
  console.error('');
  console.error('The following deleted/renamed paths are missing from claude/metadata.json deletions[]:');
  for (const p of missing) {
    console.error(`  - ${p}`);
  }
  console.error('');
  console.error('Fix: add each missing path to the deletions[] array in claude/metadata.json');
  process.exit(1);
}

main();
