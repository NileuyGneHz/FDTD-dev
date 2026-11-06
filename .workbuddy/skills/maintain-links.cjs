#!/usr/bin/env node
/*
 * maintain-links.cjs - FDTD_WS skill link maintenance (idempotent)
 *
 *   node maintain-links.cjs check     read-only status of the 3 roots + user-level links
 *   node maintain-links.cjs verify    verify 5 SKILL.md per root, byte-identical
 *   node maintain-links.cjs link      create 5 junctions in the WorkBuddy user-level dir
 *   node maintain-links.cjs unlink    remove those 5 junctions only (entity untouched)
 *
 * Windows notes:
 *   - junction target MUST be an absolute NTFS path; relative targets do not work.
 *   - Git Bash `ln -s` silently degrades to a copy. Use fs.symlinkSync(..., 'junction').
 *   - Delete links with fs.unlinkSync. NEVER rmSync / Remove-Item -Recurse:
 *     those follow the link and delete the entity.
 *   - Junctions do not cross an OS boundary. On Linux rebuild with `ln -s`.
 *
 * This script is a plain file at the skills root, not a skill directory:
 * hosts only scan one level for <name>/SKILL.md, so it cannot be discovered as a skill.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const WS = 'F:\\Lumercial_WS\\FDTD_WS';
const ENTITY = path.join(WS, 'skills');
const USER_SKILLS = 'C:\\Users\\saber\\.workbuddy\\skills';

const NAMES = [
  'fdtd-paper-parameter-extraction',
  'fdtd-lumerical-unitcell-simulation',
  'fdtd-lumerical-phase-retrieval',
  'fdtd-package-workspace',
  'fdtd-lumerical-headless',
];

const ROOTS = [
  { label: '.workbuddy/skills', dir: path.join(WS, '.workbuddy', 'skills') },
  { label: '.agents/skills', dir: path.join(WS, '.agents', 'skills') },
  { label: 'skills', dir: ENTITY },
];

function linkTarget(p) {
  try { return fs.readlinkSync(p); } catch { return null; }
}
function exists(p) {
  try { fs.lstatSync(p); return true; } catch { return false; }
}
function md5(p) {
  return crypto.createHash('md5').update(fs.readFileSync(p)).digest('hex');
}
function countSkills(dir) {
  let n = 0;
  try {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      let isDir = e.isDirectory();
      if (!isDir && e.isSymbolicLink()) {
        try { isDir = fs.statSync(p).isDirectory(); } catch { isDir = false; }
      }
      if (isDir && fs.existsSync(path.join(p, 'SKILL.md'))) n++;
    }
  } catch { return -1; }
  return n;
}

function cmdCheck() {
  console.log('[check] entity: ' + ENTITY);
  for (const r of ROOTS) {
    const t = linkTarget(r.dir);
    console.log('[check]   ' + r.label.padEnd(20) + ' : ' + countSkills(r.dir) +
      ' skills' + (t ? '  (link -> ' + t + ')' : '  (entity)'));
  }
  console.log('[check] user-level: ' + USER_SKILLS);
  for (const n of NAMES) {
    const p = path.join(USER_SKILLS, n);
    const t = linkTarget(p);
    let state = 'MISSING';
    if (t) state = 'LINK -> ' + t;
    else if (exists(p)) state = 'REAL DIR (unexpected)';
    console.log('[check]   ' + n.padEnd(38) + ' : ' + state);
  }
  console.log('[check] runtime registry is session-scoped and cannot be verified here.');
}

function cmdVerify() {
  let bad = 0;
  for (const r of ROOTS) {
    const c = countSkills(r.dir);
    console.log('[verify] ' + r.label.padEnd(20) + ' : ' + c + ' skills');
    if (c !== NAMES.length) { bad++; console.log('  EXPECT ' + NAMES.length); }
  }
  for (const n of NAMES) {
    const hashes = ROOTS.map(r => {
      const f = path.join(r.dir, n, 'SKILL.md');
      try { return md5(f); } catch { return 'MISSING'; }
    });
    const same = hashes.every(h => h === hashes[0] && h !== 'MISSING');
    console.log('[verify] ' + (same ? 'OK  ' : 'FAIL') + ' ' + n.padEnd(38) + ' ' + hashes[0].slice(0, 8));
    if (!same) bad++;
  }
  console.log('[verify] ' + (bad === 0 ? 'ALL GREEN' : bad + ' PROBLEM(S)'));
  process.exitCode = bad === 0 ? 0 : 1;
}

function cmdLink() {
  if (!fs.existsSync(USER_SKILLS)) {
    console.error('[link] user-level skills dir missing: ' + USER_SKILLS);
    process.exitCode = 1;
    return;
  }
  for (const n of NAMES) {
    const dst = path.join(USER_SKILLS, n);
    const src = path.join(ENTITY, n);
    if (!fs.existsSync(path.join(src, 'SKILL.md'))) {
      console.log('[link] SKIP  ' + n + ' : entity missing');
      continue;
    }
    if (exists(dst)) {
      console.log('[link] SKIP  ' + n + ' : already exists (use unlink first)');
      continue;
    }
    try {
      fs.symlinkSync(src, dst, 'junction');
      console.log('[link] OK    ' + n + ' -> ' + src);
    } catch (e) {
      console.log('[link] FAIL  ' + n + ' : ' + e.message);
      process.exitCode = 1;
    }
  }
  console.log('[link] done. Open a NEW conversation for the host to rescan.');
}

function cmdUnlink() {
  for (const n of NAMES) {
    const dst = path.join(USER_SKILLS, n);
    const t = linkTarget(dst);
    if (!t) {
      console.log('[unlink] SKIP ' + n + ' : not a link (entity left untouched)');
      continue;
    }
    try {
      fs.unlinkSync(dst);
      console.log('[unlink] OK   ' + n);
    } catch (e) {
      console.log('[unlink] FAIL ' + n + ' : ' + e.message);
      process.exitCode = 1;
    }
  }
}

const cmd = process.argv[2] || 'check';
const table = { check: cmdCheck, verify: cmdVerify, link: cmdLink, unlink: cmdUnlink };
if (!table[cmd]) {
  console.error('usage: node maintain-links.cjs <check|verify|link|unlink>');
  process.exitCode = 2;
} else {
  table[cmd]();
}
