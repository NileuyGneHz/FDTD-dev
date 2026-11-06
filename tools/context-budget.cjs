#!/usr/bin/env node
/**
 * context-budget.cjs — 量化 Skill 对「会话上下文」的真实占用。
 *
 * 核心事实（2026-11-06 从 app.asar 复核）：
 *   会话启动时，宿主只把每个 skill 的 name + description 注入 available_skills；
 *   SKILL.md 正文、references/、以及薄壳指向的根手册都不进上下文，
 *   只有调用 Skill(name) 或主动 Read 时才按份加载。
 *   因此上下文成本 = 唯一 skill 数 x description 长度，与实体位置 / junction 条数无关。
 *
 * 用法：
 *   node .workbuddy/skills/context-budget.cjs            # 人类可读报告
 *   node .workbuddy/skills/context-budget.cjs --json     # 机器可读
 *
 * 只读脚本：不写任何文件，不修改 frontmatter。
 * 本文件是普通 .cjs，位于 skills 根而非 <name>/SKILL.md，不会被宿主当成 skill 发现。
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const PROJECT_SKILLS = __dirname;                              // .workbuddy/skills（实体）
const USER_SKILLS = path.join(os.homedir(), '.workbuddy', 'skills');
const ROOT_HANDBOOK = path.resolve(__dirname, '..', '..', 'SKILL.md'); // ws 根 SKILL.md

/** 粗估 token：CJK 约 1 字 1 token，其余约 4 字符 1 token。仅用于量级比较，不是计费值。 */
function estimateTokens(s) {
  let cjk = 0, other = 0;
  for (const ch of s || '') {
    const c = ch.codePointAt(0);
    if ((c >= 0x4e00 && c <= 0x9fff) ||
        (c >= 0x3000 && c <= 0x303f) ||
        (c >= 0xff00 && c <= 0xffef)) cjk++;
    else other++;
  }
  return Math.ceil(cjk + other / 4);
}

function parseFrontmatter(text) {
  const m = /^---\s*\r?\n([\s\S]*?)\r?\n---\s*\r?\n/.exec(text);
  if (!m) return { block: '', body: text };
  return { block: m[1], body: text.slice(m[0].length) };
}

/** 支持 description: 单行 / ">" "|" 折叠标量 / >- |- 变体。 */
function extractDescription(block) {
  const lines = block.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!/^description\s*:/.test(line)) continue;
    const v = line.replace(/^description\s*:\s*/, '').trim();
    if (/^[>|][+-]?$/.test(v)) {
      const out = [];
      for (let j = i + 1; j < lines.length; j++) {
        if (/^[ \t]/.test(lines[j])) out.push(lines[j].trim());
        else break;
      }
      return out.join(' ');
    }
    return v.replace(/^["']|["']$/g, '');
  }
  return '';
}

function dirBytes(dir) {
  let n = 0;
  let st;
  try { st = fs.lstatSync(dir); } catch { return 0; }
  if (!st.isDirectory() || st.isSymbolicLink()) return 0; // 不跟随链接
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) n += dirBytes(p);
    else if (e.isFile()) { try { n += fs.statSync(p).size; } catch {} }
  }
  return n;
}

function scan(root, label) {
  const rows = [];
  let entries = [];
  try { entries = fs.readdirSync(root, { withFileTypes: true }); } catch { return rows; }
  for (const e of entries) {
    // Windows junction 的 Dirent.isDirectory() === false（lstat 视为 reparse point）。
    // 只判断 isDirectory() 会静默漏掉链接型 skill，必须把 isSymbolicLink() 一并算作目录。
    if (!(e.isDirectory() || e.isSymbolicLink())) continue;
    const skillFile = path.join(root, e.name, 'SKILL.md');
    let raw;
    try { raw = fs.readFileSync(skillFile, 'utf8'); } catch { continue; }
    const { block, body } = parseFrontmatter(raw);
    const desc = extractDescription(block);
    rows.push({
      name: e.name,
      source: label,
      descChars: desc.length,
      descTokens: estimateTokens(desc),
      skillBytes: Buffer.byteLength(raw),
      bodyBytes: Buffer.byteLength(body),
      refBytes: dirBytes(path.join(root, e.name, 'references')),
      assetBytes: dirBytes(path.join(root, e.name, 'assets')),
    });
  }
  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

const project = scan(PROJECT_SKILLS, 'project');
const user = scan(USER_SKILLS, 'user');
const all = [...project, ...user];

// 按 name 去重：宿主 addSkills 的去重逻辑，junction 造成的重复视图不应计入。
const seen = new Set();
const unique = all.filter(r => (seen.has(r.name) ? false : (seen.add(r.name), true)));

const sum = (rows, k) => rows.reduce((a, r) => a + r[k], 0);
const handbookBytes = (() => { try { return fs.statSync(ROOT_HANDBOOK).size; } catch { return 0; } })();

if (process.argv.includes('--json')) {
  console.log(JSON.stringify({
    project, user,
    uniqueCount: unique.length,
    residentDescChars: sum(unique, 'descChars'),
    residentDescTokens: sum(unique, 'descTokens'),
    onDiskSkillBodyBytes: sum(project, 'bodyBytes'),
    onDiskReferencesBytes: sum(project, 'refBytes'),
    rootHandbookBytes: handbookBytes,
  }, null, 2));
  process.exit(0);
}

const pad = (s, n) => String(s).padEnd(n);
const num = (n) => String(n).padStart(7);

function table(title, rows) {
  console.log('\n=== ' + title + ' ===');
  console.log('  ' + pad('name', 40) + ' desc(ch) ' + ' ~tok ' + ' SKILL.md ' + '   body ' + '  refs ' + ' assets');
  for (const r of rows) {
    console.log('  ' + pad(r.name, 40) + num(r.descChars) + ' ' + num(r.descTokens) + ' ' +
      num(r.skillBytes) + ' ' + num(r.bodyBytes) + ' ' + num(r.refBytes) + ' ' + num(r.assetBytes));
  }
  console.log('  ' + pad('TOTAL (' + rows.length + ')', 40) + num(sum(rows, 'descChars')) + ' ' +
    num(sum(rows, 'descTokens')) + ' ' + num(sum(rows, 'skillBytes')) + ' ' +
    num(sum(rows, 'bodyBytes')) + ' ' + num(sum(rows, 'refBytes')) + ' ' + num(sum(rows, 'assetBytes')));
}

console.log('Skill 上下文预算 — ' + new Date().toISOString());
console.log('project root: ' + PROJECT_SKILLS);
console.log('user root   : ' + USER_SKILLS);

table('project skills (FDTD_WS/.workbuddy/skills)', project);
table('user-level skills (~/.workbuddy/skills)', user);

console.log('\n=== 每轮对话常驻开销（注入 available_skills 的部分）===');
console.log('  唯一 skill 数（按 name 去重）      : ' + unique.length);
console.log('  description 合计                  : ' + sum(unique, 'descChars') + ' chars');
console.log('  粗估 tokens                       : ~' + sum(unique, 'descTokens'));
console.log('    - project (FDTD)                : ~' + sum(project, 'descTokens'));
console.log('    - user-level                    : ~' + sum(user, 'descTokens'));

console.log('\n=== 磁盘上、但默认不进上下文（按需加载）===');
console.log('  5 份 SKILL.md 正文                : ' + sum(project, 'bodyBytes') + ' bytes');
console.log('  references/ 合计                  : ' + sum(project, 'refBytes') + ' bytes');
console.log('  assets/ 合计                      : ' + sum(project, 'assetBytes') + ' bytes');
// 根手册以中文为主，UTF-8 约 2.5 bytes/字；1 汉字约 1 token，给个量级即可。
console.log('  根 SKILL.md（薄壳二次读取目标）   : ' + handbookBytes + ' bytes  ~' +
  Math.round(handbookBytes / 2.5) + ' tokens (仅调用该薄壳时才发生)');

console.log('\n  说明：调用一次 Skill(name) 只加载该一份 SKILL.md；');
console.log('  references/ 需 SKILL.md 内指引才 Read；根手册仅 lumerical-fdtd-headless 会二次读。');
console.log('  junction 是指针不是副本，不增加上述任何一项。');
