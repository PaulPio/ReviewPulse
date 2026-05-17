#!/usr/bin/env node
/**
 * Converts VoltAgent (Claude Code) subagent .md files to OpenCode agent markdown.
 * Usage:
 *   node scripts/volt-to-opencode-agents.mjs [path/to/voltagent-subagents/categories] [outputDir]
 * Defaults: ~/.claude/plugins/marketplaces/voltagent-subagents/categories → ~/.config/opencode/agents
 */
import fs from "fs";
import path from "path";
import os from "os";

/** Every subagent uses this OpenCode model (see `opencode models` if the id differs for your account). */
const AGENT_MODEL = "minimax/minimax-m2.7";

const DEFAULT_SRC = path.join(
  os.homedir(),
  ".claude",
  "plugins",
  "marketplaces",
  "voltagent-subagents",
  "categories",
);

const DEFAULT_DEST = path.join(os.homedir(), ".config", "opencode", "agents");

function parseSimpleFrontmatter(text) {
  const lines = text.split(/\r?\n/);
  if (lines[0] !== "---") return null;
  const fm = {};
  let i = 1;
  for (; i < lines.length; i++) {
    if (lines[i] === "---") break;
    const m = lines[i].match(/^([\w-]+):\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    fm[m[1]] = v;
  }
  if (i >= lines.length || lines[i] !== "---") return null;
  const body = lines.slice(i + 1).join("\n");
  return { fm, body };
}

function parseTools(s) {
  if (!s) return [];
  return s
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

function buildPermission(toolsTokens, isMetaOrchestration) {
  const set = new Set(toolsTokens);
  const canWrite = set.has("Write") || set.has("Edit");
  const canBash = set.has("Bash");
  const canWebFetch = set.has("WebFetch");
  const canWebSearch = set.has("WebSearch");

  return {
    read: "allow",
    glob: "allow",
    grep: "allow",
    list: "allow",
    edit: canWrite ? "allow" : "deny",
    bash: canBash ? "allow" : "deny",
    webfetch: canWebFetch ? "allow" : "deny",
    websearch: canWebSearch ? "allow" : "deny",
    task: isMetaOrchestration ? "allow" : "deny",
  };
}

function yamlDescription(desc) {
  if (desc == null || desc === "") return '""';
  return JSON.stringify(String(desc));
}

function permYaml(perm) {
  let y = "permission:\n";
  for (const [k, v] of Object.entries(perm)) {
    y += `  ${k}: ${v}\n`;
  }
  return y;
}

function convertFile(srcPath, destDir) {
  const text = fs.readFileSync(srcPath, "utf8");
  const parsed = parseSimpleFrontmatter(text);
  if (!parsed) {
    console.warn("skip (no valid frontmatter):", srcPath);
    return false;
  }
  const { fm, body } = parsed;
  const desc = fm.description ?? "";
  const toolsTokens = parseTools(fm.tools ?? "");
  const isMeta = srcPath.includes(`${path.sep}09-meta-orchestration${path.sep}`);
  const perm = buildPermission(toolsTokens, isMeta);

  const base = path.basename(srcPath, ".md");
  let out = "---\n";
  out += `description: ${yamlDescription(desc)}\n`;
  out += "mode: subagent\n";
  out += `model: ${AGENT_MODEL}\n`;
  out += permYaml(perm);
  out += "---\n\n";
  out +=
    "<!-- Converted from VoltAgent (Claude Code). Tune `permission` if needed; Claude `tools` / MCP ids are not auto-mapped. -->\n\n";
  out += body.replace(/^\uFEFF/, "").trimStart();

  fs.writeFileSync(path.join(destDir, `${base}.md`), out, "utf8");
  return true;
}

function walkCategories(categoriesDir, destDir) {
  const entries = fs.readdirSync(categoriesDir, { withFileTypes: true });
  let count = 0;
  for (const e of entries) {
    if (!e.isDirectory()) continue;
    const cat = path.join(categoriesDir, e.name);
    for (const f of fs.readdirSync(cat)) {
      if (!f.endsWith(".md") || f === "README.md") continue;
      if (convertFile(path.join(cat, f), destDir)) count += 1;
    }
  }
  return count;
}

const src = process.argv[2] || DEFAULT_SRC;
const dest = process.argv[3] || DEFAULT_DEST;

if (!fs.existsSync(src)) {
  console.error("Source categories directory not found:", src);
  console.error("Add the marketplace: claude plugin marketplace add VoltAgent/awesome-claude-code-subagents");
  process.exit(1);
}

fs.mkdirSync(dest, { recursive: true });
const n = walkCategories(src, dest);
console.log(`Wrote ${n} OpenCode agents to ${dest}`);
