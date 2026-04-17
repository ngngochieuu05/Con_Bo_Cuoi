#!/usr/bin/env node
/**
 * check-skill-cross-refs.js
 *
 * CI gate: verifies that all /ck:<name> references in claude/ markdown files
 * point to a registered skill name (from SKILL.md frontmatter) and do not
 * collide with Claude Code built-in commands.
 *
 * Usage: node scripts/check-skill-cross-refs.js
 * Exit 0 = all references valid (or no references found)
 * Exit 1 = broken references or collisions found
 */

'use strict';

const { readFileSync, readdirSync, lstatSync } = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..');
const claudeDir = path.join(repoRoot, 'claude');

// Claude Code built-in commands that must not be used as skill names
const BUILTIN_COMMANDS = new Set([
  'help', 'clear', 'debug', 'plan', 'compact', 'review', 'search',
  'init', 'login', 'logout', 'doctor', 'mcp', 'memory', 'model',
  'permissions', 'status', 'config', 'cost', 'terminal-setup',
  'listen', 'bug', 'ide',
]);

// Skills that intentionally use ck-prefixed directory names to avoid built-in
// collision (e.g. ck-debug, ck-plan). Their SKILL.md name: field still reads
// "ck:debug" / "ck:plan" which normalizes to "debug" / "plan", but the actual
// slash-command invocation is /ck:ck-debug, /ck:ck-plan — no real collision.
const ALLOWED_BUILTIN_OVERLAPS = new Set(['ck-debug', 'ck-plan']);

// Regex to find /ck:<name> references in markdown
const CK_REF_RE = /\/ck:([a-z][a-z0-9-]*)/g;

/**
 * Recursively collect all files matching a predicate under a directory.
 */
function findFiles(dir, predicate) {
  const results = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return results;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry);
    let stat;
    try {
      stat = lstatSync(full);
    } catch {
      continue;
    }
    // Skip symlinks to prevent traversal outside the repo
    if (stat.isSymbolicLink()) continue;
    if (stat.isDirectory()) {
      results.push(...findFiles(full, predicate));
    } else if (predicate(entry, full)) {
      results.push(full);
    }
  }
  return results;
}

/**
 * Parses YAML frontmatter from a SKILL.md file and extracts the `name:` field.
 * Returns null if not found.
 */
function extractSkillName(content) {
  // Match YAML frontmatter block: --- ... ---
  const fmMatch = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fmMatch) return null;

  const frontmatter = fmMatch[1];
  // Extract name: value (unquoted or single/double quoted)
  const nameMatch = frontmatter.match(/^name:\s*['"]?([^\s'"]+)['"]?\s*$/m);
  if (!nameMatch) return null;

  return nameMatch[1].trim();
}

/**
 * Builds the canonical skill registry from all claude/skills/<skillname>/SKILL.md files.
 * Returns { registry: Set<string>, collisions: Array<{name, file}> }
 */
function buildSkillRegistry() {
  const skillsDir = path.join(claudeDir, 'skills');
  const skillFiles = findFiles(skillsDir, (entry) => entry === 'SKILL.md');

  const registry = new Set();
  const collisions = [];

  for (const filePath of skillFiles) {
    let content;
    try {
      content = readFileSync(filePath, 'utf8');
    } catch (err) {
      console.error(`[!] Could not read ${filePath}: ${err.message}`);
      continue;
    }

    const rawName = extractSkillName(content);
    if (!rawName) {
      // No name in frontmatter — skip silently (not our concern here)
      continue;
    }

    // Normalize: strip leading "ck:" prefix so we compare bare names against
    // the part captured after "/ck:" in references (e.g. "ck:journal" -> "journal")
    const name = rawName.startsWith('ck:') ? rawName.slice(3) : rawName;

    // Check collision, but skip skills that use ck-prefixed dir names to avoid it
    const dirName = path.basename(path.dirname(filePath));
    if (BUILTIN_COMMANDS.has(name) && !ALLOWED_BUILTIN_OVERLAPS.has(dirName)) {
      collisions.push({ name, file: path.relative(repoRoot, filePath) });
    }

    registry.add(name);
  }

  return { registry, collisions };
}

/**
 * Scans all .md files under claude/ and collects /ck: references.
 * Returns Array<{ ref: string, file: string, line: number }>
 */
function collectCkReferences() {
  const mdFiles = findFiles(claudeDir, (entry) => entry.endsWith('.md'));
  const refs = [];

  for (const filePath of mdFiles) {
    let content;
    try {
      content = readFileSync(filePath, 'utf8');
    } catch (err) {
      console.error(`[!] Could not read ${filePath}: ${err.message}`);
      continue;
    }

    const lines = content.split('\n');
    lines.forEach((line, idx) => {
      let match;
      // Reset lastIndex for global regex reuse
      CK_REF_RE.lastIndex = 0;
      while ((match = CK_REF_RE.exec(line)) !== null) {
        refs.push({
          ref: match[1],
          file: path.relative(repoRoot, filePath),
          line: idx + 1,
        });
      }
    });
  }

  return refs;
}

function main() {
  const { registry, collisions } = buildSkillRegistry();
  const allRefs = collectCkReferences();

  let hasErrors = false;

  // Report name collisions with built-ins
  if (collisions.length > 0) {
    hasErrors = true;
    console.error('[X] Skill name collision(s) with Claude Code built-in commands:');
    for (const { name, file } of collisions) {
      console.error(`  - /ck:${name}  (defined in ${file})`);
    }
    console.error('');
  }

  // Check each reference against registry
  const broken = allRefs.filter(({ ref }) => !registry.has(ref));

  if (broken.length > 0) {
    hasErrors = true;
    console.error('[X] Broken /ck: references (skill not registered in any SKILL.md):');
    for (const { ref, file, line } of broken) {
      console.error(`  - /ck:${ref}  at ${file}:${line}`);
    }
    console.error('');
    console.error('Registered skills:', [...registry].sort().join(', ') || '(none)');
  }

  if (!hasErrors) {
    const refCount = allRefs.length;
    const skillCount = registry.size;
    console.log(`[OK] skill-cross-refs: ${skillCount} skill(s) registered, ${refCount} reference(s) checked — all valid.`);
    process.exit(0);
  }

  process.exit(1);
}

main();
