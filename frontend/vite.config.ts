import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as http from 'http';
import * as child_process from 'child_process';

function getLocaLLMDir(): string {
  const dir = path.join(os.homedir(), '.locallm');
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return dir;
}

function getConfigFilePath(): string {
  return path.join(getLocaLLMDir(), 'config.json');
}

function getWorkspacesDir(): string {
  const dir = path.join(getLocaLLMDir(), 'workspaces');
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return dir;
}

function loadConfigOnDisk(): Record<string, any> {
  const configPath = getConfigFilePath();
  if (fs.existsSync(configPath)) {
    try {
      const raw = fs.readFileSync(configPath, 'utf-8');
      return JSON.parse(raw);
    } catch (e) {
      console.error('Failed to parse config.json:', e);
    }
  }
  return {
    active_backend: 'ollama',
    ollama_host: 'http://127.0.0.1:11434',
    ollama_model: 'gemma4:12b',
    custom_platforms: [],
    default_model: 'gemma4:12b',
    temperature: 0.7,
    context_window: 8192,
    system_prompt: 'You are locaLLM, a helpful, fast, and intelligent local AI assistant.',
    agent_permission_policy: 'ask',
    agent_max_steps: 25,
    active_workspace: 'default',
    search_provider: 'auto',
    search_api_url: '',
    ui_theme: 'cyber_neon',
    server_enabled: true,
    server_host: '127.0.0.1',
    server_port: 8080,
    server_api_key: ''
  };
}

function resolveUserName(cfg: Record<string, any>, activeWs?: string): string | undefined {
  if (cfg.user_name && typeof cfg.user_name === 'string' && cfg.user_name.trim()) {
    return cfg.user_name.trim();
  }
  // Check active workspace knowledge files for an author or user profile declaration
  try {
    const wsRoot = getWorkspacesDir();
    const ws = activeWs || cfg.active_workspace || 'default';
    const kDir = path.join(wsRoot, ws, 'knowledge');
    if (fs.existsSync(kDir)) {
      const files = fs.readdirSync(kDir);
      for (const file of files) {
        if (file.endsWith('.md') || file.endsWith('.txt')) {
          const content = fs.readFileSync(path.join(kDir, file), 'utf-8');
          const m = content.match(/(?:user(?:name)?|author|owner|my name is)\s*[:=]?\s*([A-Za-z0-9_-]+)/i);
          if (m && m[1] && !['the', 'a', 'default', 'an', 'is', 'admin'].includes(m[1].toLowerCase())) {
            return m[1].charAt(0).toUpperCase() + m[1].slice(1);
          }
        }
      }
    }
  } catch {
    // ignore
  }
  // Try git config user.name
  try {
    const gitUser = child_process.execSync('git config user.name', { encoding: 'utf-8' }).trim();
    if (gitUser && !gitUser.includes('\n')) {
      const first = gitUser.split(' ')[0].replace(/[^a-zA-Z0-9_-]/g, '');
      if (first.length > 1 && !['root', 'runner', 'admin', 'user'].includes(first.toLowerCase())) {
        return first.charAt(0).toUpperCase() + first.slice(1);
      }
    }
  } catch {
    // ignore
  }
  // Try OS username if not a generic daemon/system account
  try {
    const rawUser = os.userInfo()?.username;
    if (rawUser && !['root', 'runner', 'admin', 'node', 'daemon', 'system', 'default'].includes(rawUser.toLowerCase())) {
      return rawUser.charAt(0).toUpperCase() + rawUser.slice(1);
    }
  } catch {
    // ignore
  }
  return undefined;
}

function saveConfigOnDisk(newConfig: Record<string, any>): void {
  const configPath = getConfigFilePath();
  fs.writeFileSync(configPath, JSON.stringify(newConfig, null, 2), 'utf-8');
}

function parseJsonBody(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk;
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', err => reject(err));
  });
}

function sendJson(res: http.ServerResponse, statusCode: number, data: any) {
  const payload = JSON.stringify(data);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Workspace'
  });
  res.end(payload);
}

function readSkillsRecursively(baseDir: string): any[] {
  const IGNORE_DIRS = new Set([
    '.git', 'node_modules', 'tests', 'test', 'evals', 'benchmarks',
    'examples', 'dist', 'build', 'target', '.venv', 'venv',
    '__pycache__', 'cli', 'packages', 'references', 'templates', 'assets', 'scripts'
  ]);
  const IGNORE_FILES = new Set([
    'changelog', 'license', 'contributing', 'code_of_conduct',
    'security', 'third-party', 'package-lock', 'package', 'background-tasks', 'agents', 'soul'
  ]);

  const skills: any[] = [];
  const seenIds = new Set<string>();

  function walk(currentDir: string) {
    if (!fs.existsSync(currentDir)) return;
    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(currentDir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        if (!IGNORE_DIRS.has(entry.name.toLowerCase())) {
          walk(fullPath);
        }
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (ext !== '.md' && ext !== '.txt') continue;
        const stem = path.basename(entry.name, ext).toLowerCase();
        if (IGNORE_FILES.has(stem) || stem.startsWith('license') || stem.startsWith('changelog')) continue;

        let skillId = path.basename(entry.name, ext);
        const parentName = path.basename(currentDir);
        const isSkillDoc = entry.name.toLowerCase() === 'skill.md' || entry.name.toLowerCase() === 'readme.md';

        if (isSkillDoc && currentDir !== baseDir) {
          skillId = parentName;
        }

        const cleanId = skillId.toLowerCase().replace(/[^a-z0-9_-]/g, '-');
        if (!cleanId || seenIds.has(cleanId)) continue;

        try {
          const content = fs.readFileSync(fullPath, 'utf-8');
          let name = cleanId;
          let description = '';

          const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
          if (fmMatch) {
            const yaml = fmMatch[1];
            const nameMatch = yaml.match(/(?:^|\n)name:\s*([^\n]+)/);
            if (nameMatch) name = nameMatch[1].replace(/['"]/g, '').trim();
            const descMatch = yaml.match(/(?:^|\n)description:\s*([^\n]+)/);
            if (descMatch) description = descMatch[1].replace(/['"]/g, '').trim();
          }

          if (name === cleanId) {
            const lines = content.split('\n');
            for (const line of lines) {
              const trimmed = line.trim();
              if (trimmed && !trimmed.startsWith('---')) {
                name = trimmed.replace(/^[#\s*-]+/, '').replace(/^Skill:\s*/i, '').trim();
                break;
              }
            }
          }

          if (!description) {
            const lines = content.split('\n');
            let foundHeader = false;
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed || trimmed.startsWith('---')) continue;
              if (trimmed.startsWith('#')) {
                foundHeader = true;
                continue;
              }
              if (foundHeader && !trimmed.startsWith('#')) {
                description = trimmed.replace(/^[#\s*-]+/, '').slice(0, 160);
                break;
              }
            }
          }

          seenIds.add(cleanId);
          skills.push({
            id: cleanId,
            name: name || cleanId,
            description: description || undefined,
            content,
            path: path.relative(baseDir, fullPath).replace(/\\/g, '/'),
            enabled: true
          });
        } catch {}
      }
    }
  }

  walk(baseDir);
  return skills;
}

function locallmBridgePlugin(): Plugin {
  return {
    name: 'locallm-bridge-plugin',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const urlObj = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
        const pathname = urlObj.pathname;

        // Handle CORS Pre-flight
        if (req.method === 'OPTIONS') {
          res.writeHead(204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Workspace'
          });
          res.end();
          return;
        }

        // 1. GET /api/config & POST /api/config
        if (pathname === '/api/config') {
          if (req.method === 'GET') {
            const cfg = loadConfigOnDisk();
            // Provide compatibility aliases and dynamic user identity (never hardcoded)
            cfg.user_name = resolveUserName(cfg);
            cfg.model = cfg.default_model || cfg.ollama_model || 'gemma4:12b';
            cfg.provider = cfg.active_backend === 'ollama' ? 'ollama' : 'openai';
            cfg.contextLength = cfg.context_window;
            sendJson(res, 200, cfg);
            return;
          }

          if (req.method === 'POST') {
            try {
              const body = await parseJsonBody(req);
              const current = loadConfigOnDisk();
              const merged = { ...current, ...body };
              // Ensure default_model is kept aligned
              if (body.model && !body.default_model) {
                merged.default_model = body.model;
              }
              if (body.provider && !body.active_backend) {
                merged.active_backend = body.provider;
              }
              if (body.contextLength && !body.context_window) {
                merged.context_window = body.contextLength;
              }
              saveConfigOnDisk(merged);

              // Hot-sync to locaLLM Python API server if running
              const serverPort = merged.server_port || 8080;
              const apiKey = merged.server_api_key || '';
              try {
                await fetch(`http://127.0.0.1:${serverPort}/api/config`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {})
                  },
                  body: JSON.stringify(merged),
                  signal: AbortSignal.timeout(1500)
                });
              } catch {
                // Background server may not be running or reachable, ignore
              }

              sendJson(res, 200, { success: true, config: merged });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }
        }

        // 2. GET, POST, PUT, DELETE /api/workspaces
        if (pathname === '/api/workspaces') {
          const wsDir = getWorkspacesDir();

          if (req.method === 'GET') {
            try {
              const entries = fs.readdirSync(wsDir, { withFileTypes: true });
              const workspaces: any[] = [];

              for (const entry of entries) {
                if (!entry.isDirectory()) continue;
                const wsPath = path.join(wsDir, entry.name);
                let meta: any = {};
                const metaFile = path.join(wsPath, 'workspace.json');
                if (fs.existsSync(metaFile)) {
                  try {
                    meta = JSON.parse(fs.readFileSync(metaFile, 'utf-8'));
                  } catch {}
                }

                // Read knowledge count
                let knowledgeCount = 0;
                const knowDir = path.join(wsPath, 'knowledge');
                if (fs.existsSync(knowDir)) {
                  try {
                    knowledgeCount = fs.readdirSync(knowDir).filter(f => f.endsWith('.md') || f.endsWith('.txt')).length;
                  } catch {}
                }

                // Read skills files recursively
                const skillDir = path.join(wsPath, 'skills');
                const skills = readSkillsRecursively(skillDir);

                workspaces.push({
                  name: entry.name,
                  description: meta.description || '',
                  icon: meta.icon || 'Folder',
                  color: meta.color || '#3B82F6',
                  custom_instructions: meta.custom_instructions || '',
                  auto_memory: meta.auto_memory !== undefined ? !!meta.auto_memory : true,
                  skills,
                  knowledgeCount,
                  skillsCount: skills.length
                });
              }

              // Ensure default workspace is listed if directory empty
              if (workspaces.length === 0) {
                workspaces.push({
                  name: 'default',
                  description: 'Default general-purpose workspace',
                  icon: 'Folder',
                  color: '#3B82F6',
                  custom_instructions: '',
                  auto_memory: true,
                  skills: [],
                  knowledgeCount: 0,
                  skillsCount: 0
                });
              }

              sendJson(res, 200, workspaces);
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }

          if (req.method === 'POST') {
            try {
              const body = await parseJsonBody(req);
              const cleanName = (body.name || '').trim().replace(/[^a-zA-Z0-9_\- ]/g, '-').trim();
              if (!cleanName) {
                sendJson(res, 400, { error: 'Invalid workspace name' });
                return;
              }

              const targetDir = path.join(wsDir, cleanName);
              if (!fs.existsSync(targetDir)) {
                fs.mkdirSync(targetDir, { recursive: true });
                fs.mkdirSync(path.join(targetDir, 'sessions'), { recursive: true });
                fs.mkdirSync(path.join(targetDir, 'knowledge'), { recursive: true });
                fs.mkdirSync(path.join(targetDir, 'skills'), { recursive: true });
                fs.mkdirSync(path.join(targetDir, 'files'), { recursive: true });
                fs.mkdirSync(path.join(targetDir, 'images'), { recursive: true });
              }

              const meta = {
                name: cleanName,
                description: body.description || '',
                icon: body.icon || 'Folder',
                color: body.color || '#3B82F6',
                custom_instructions: body.custom_instructions || '',
                auto_memory: body.auto_memory !== undefined ? !!body.auto_memory : true,
                created_at: new Date().toISOString()
              };

              fs.writeFileSync(
                path.join(targetDir, 'workspace.json'),
                JSON.stringify(meta, null, 2),
                'utf-8'
              );

              // Sync instructions into AGENTS.md
              if (body.custom_instructions) {
                const agentsFile = path.join(targetDir, 'AGENTS.md');
                fs.writeFileSync(
                  agentsFile,
                  `# Workspace Instructions: ${cleanName}\n\n${body.custom_instructions}\n`,
                  'utf-8'
                );
              }

              // Write initial skills if provided
              if (Array.isArray(body.skills)) {
                const skillDir = path.join(targetDir, 'skills');
                for (const s of body.skills) {
                  const sId = (s.id || s.name || 'skill').toLowerCase().replace(/[^a-z0-9_-]/g, '-');
                  fs.writeFileSync(
                    path.join(skillDir, `${sId}.md`),
                    s.content || `# Skill: ${s.name}\n${s.description || ''}\n`,
                    'utf-8'
                  );
                }
              }

              sendJson(res, 200, {
                name: cleanName,
                description: meta.description,
                icon: meta.icon,
                color: meta.color,
                custom_instructions: meta.custom_instructions,
                auto_memory: meta.auto_memory,
                skills: body.skills || [],
                knowledgeCount: 0,
                skillsCount: (body.skills || []).length
              });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }

          if (req.method === 'PUT') {
            try {
              const body = await parseJsonBody(req);
              const origName = (body.oldName || body.old_name || body.name || '').trim();
              const targetName = (body.newName || body.name || origName).trim().replace(/[^a-zA-Z0-9_\- ]/g, '-').trim();
              if (!origName && !targetName) {
                sendJson(res, 400, { error: 'Workspace name is required' });
                return;
              }

              // Locate existing workspace directory (exact or case-insensitive)
              let currentWsDir = path.join(wsDir, origName);
              if (!fs.existsSync(currentWsDir)) {
                try {
                  const entries = fs.readdirSync(wsDir, { withFileTypes: true });
                  const matched = entries.find(e => e.isDirectory() && e.name.toLowerCase() === origName.toLowerCase());
                  if (matched) {
                    currentWsDir = path.join(wsDir, matched.name);
                  } else if (targetName && fs.existsSync(path.join(wsDir, targetName))) {
                    currentWsDir = path.join(wsDir, targetName);
                  } else {
                    sendJson(res, 404, { error: `Workspace '${origName}' not found` });
                    return;
                  }
                } catch {
                  sendJson(res, 404, { error: `Workspace '${origName}' not found` });
                  return;
                }
              }

              const currentActualName = path.basename(currentWsDir);
              let finalName = currentActualName;

              // Handle rename if targetName specified and differs from current directory name
              if (targetName && targetName !== currentActualName && currentActualName.toLowerCase() !== 'default') {
                const newWsDir = path.join(wsDir, targetName);
                if (newWsDir !== currentWsDir) {
                  if (fs.existsSync(newWsDir)) {
                    sendJson(res, 400, { error: `Workspace '${targetName}' already exists` });
                    return;
                  }
                  fs.renameSync(currentWsDir, newWsDir);
                  currentWsDir = newWsDir;
                  finalName = targetName;

                  // Keep active_workspace in config.json synced
                  try {
                    const cfg = loadConfigOnDisk();
                    if (cfg.active_workspace && cfg.active_workspace.toLowerCase() === currentActualName.toLowerCase()) {
                      cfg.active_workspace = targetName;
                      saveConfigOnDisk(cfg);
                    }
                  } catch {}
                }
              }

              // Load existing metadata
              let meta: any = {};
              const metaFile = path.join(currentWsDir, 'workspace.json');
              if (fs.existsSync(metaFile)) {
                try {
                  meta = JSON.parse(fs.readFileSync(metaFile, 'utf-8'));
                } catch {}
              }

              meta.name = finalName;
              if (body.description !== undefined) meta.description = body.description;
              if (body.icon !== undefined) meta.icon = body.icon;
              if (body.color !== undefined) meta.color = body.color;
              if (body.custom_instructions !== undefined) meta.custom_instructions = body.custom_instructions;
              if (body.auto_memory !== undefined) meta.auto_memory = !!body.auto_memory;
              meta.updated_at = new Date().toISOString();

              fs.writeFileSync(metaFile, JSON.stringify(meta, null, 2), 'utf-8');

              // Update AGENTS.md
              if (body.custom_instructions !== undefined) {
                const agentsFile = path.join(currentWsDir, 'AGENTS.md');
                fs.writeFileSync(
                  agentsFile,
                  `# Workspace Instructions: ${finalName}\n\n${body.custom_instructions}\n`,
                  'utf-8'
                );
              }

              // Handle explicitly removed skills safely
              if (Array.isArray(body.deletedSkills)) {
                const skillDir = path.join(currentWsDir, 'skills');
                for (const ds of body.deletedSkills) {
                  const dsId = (ds.id || ds.name || '').toLowerCase().replace(/[^a-z0-9_-]/g, '-');
                  const targetFile = ds.path ? path.join(skillDir, ds.path) : (dsId ? path.join(skillDir, `${dsId}.md`) : null);
                  if (targetFile && fs.existsSync(targetFile)) {
                    try { fs.unlinkSync(targetFile); } catch {}
                  }
                }
              }

              // Sync skills safely without deleting existing files
              if (Array.isArray(body.skills)) {
                const skillDir = path.join(currentWsDir, 'skills');
                if (!fs.existsSync(skillDir)) fs.mkdirSync(skillDir, { recursive: true });

                for (const s of body.skills) {
                  const sId = (s.id || s.name || 'skill').toLowerCase().replace(/[^a-z0-9_-]/g, '-');
                  const targetFile = s.path ? path.join(skillDir, s.path) : path.join(skillDir, `${sId}.md`);
                  try {
                    const dirOfFile = path.dirname(targetFile);
                    if (!fs.existsSync(dirOfFile)) fs.mkdirSync(dirOfFile, { recursive: true });
                    if (s.content) {
                      fs.writeFileSync(targetFile, s.content, 'utf-8');
                    } else if (!fs.existsSync(targetFile)) {
                      fs.writeFileSync(
                        targetFile,
                        `# Skill: ${s.name}\n${s.description || ''}\n`,
                        'utf-8'
                      );
                    }
                  } catch {}
                }
              }

              const updatedSkills = readSkillsRecursively(path.join(currentWsDir, 'skills'));

              sendJson(res, 200, {
                name: finalName,
                description: meta.description || '',
                icon: meta.icon || 'Folder',
                color: meta.color || '#3B82F6',
                custom_instructions: meta.custom_instructions || '',
                auto_memory: meta.auto_memory !== undefined ? !!meta.auto_memory : true,
                skills: updatedSkills,
                skillsCount: updatedSkills.length
              });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }

          if (req.method === 'DELETE') {
            try {
              const wsName = (urlObj.searchParams.get('name') || '').trim();
              if (!wsName || wsName.toLowerCase() === 'default') {
                sendJson(res, 400, { error: "The 'default' workspace cannot be deleted." });
                return;
              }
              const targetDir = path.join(wsDir, wsName);
              if (fs.existsSync(targetDir)) {
                fs.rmSync(targetDir, { recursive: true, force: true });
              }
              sendJson(res, 200, { success: true });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }
        }

        // 2b. GET, PUT, DELETE /api/workspaces/:name/memory or /api/workspaces/memory
        if (
          pathname === '/api/workspaces/memory' ||
          (pathname.startsWith('/api/workspaces/') && pathname.endsWith('/memory'))
        ) {
          const wsDir = getWorkspacesDir();
          let wsName = (urlObj.searchParams.get('workspace') || urlObj.searchParams.get('name') || '').trim();
          if (!wsName && pathname.startsWith('/api/workspaces/')) {
            const parts = pathname.split('/');
            if (parts.length >= 4 && parts[parts.length - 1] === 'memory') {
              wsName = decodeURIComponent(parts[parts.length - 2]);
            }
          }
          wsName = wsName || 'default';
          const targetDir = path.join(wsDir, wsName);
          const memFile = path.join(targetDir, 'memory.json');
          const metaFile = path.join(targetDir, 'workspace.json');

          let meta: any = {};
          if (fs.existsSync(metaFile)) {
            try { meta = JSON.parse(fs.readFileSync(metaFile, 'utf-8')); } catch {}
          }

          let memData: { facts: Record<string, string> } = { facts: {} };
          if (fs.existsSync(memFile)) {
            try { memData = JSON.parse(fs.readFileSync(memFile, 'utf-8')); } catch {}
          }
          if (!memData.facts || typeof memData.facts !== 'object') {
            memData.facts = {};
          }

          if (req.method === 'GET') {
            sendJson(res, 200, {
              workspace: wsName,
              auto_memory: meta.auto_memory !== undefined ? !!meta.auto_memory : true,
              facts: memData.facts
            });
            return;
          }

          if (req.method === 'DELETE') {
            try {
              const key = (urlObj.searchParams.get('key') || '').trim();
              if (key) {
                delete memData.facts[key];
              } else {
                memData.facts = {};
              }
              if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
              fs.writeFileSync(memFile, JSON.stringify(memData, null, 2), 'utf-8');
              sendJson(res, 200, { success: true, message: key ? `Fact '${key}' deleted` : 'Memory cleared' });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }

          if (req.method === 'PUT') {
            try {
              const body = await parseJsonBody(req);
              if (body.auto_memory !== undefined) {
                meta.auto_memory = !!body.auto_memory;
                fs.writeFileSync(metaFile, JSON.stringify(meta, null, 2), 'utf-8');
              }
              const factVal = body.value !== undefined ? body.value : body.fact;
              if (body.key && factVal !== undefined) {
                memData.facts[String(body.key).trim()] = String(factVal).trim();
              }
              if (body.facts && typeof body.facts === 'object') {
                Object.assign(memData.facts, body.facts);
              }
              if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
              fs.writeFileSync(memFile, JSON.stringify(memData, null, 2), 'utf-8');
              sendJson(res, 200, {
                workspace: wsName,
                auto_memory: meta.auto_memory !== undefined ? !!meta.auto_memory : true,
                facts: memData.facts
              });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }
        }

        // 3. GET, POST, DELETE /api/sessions
        if (pathname === '/api/sessions') {
          const wsDir = getWorkspacesDir();
          const targetWs = (urlObj.searchParams.get('workspace') || 'default').trim();
          const sessionsDir = path.join(wsDir, targetWs, 'sessions');

          if (!fs.existsSync(sessionsDir)) {
            fs.mkdirSync(sessionsDir, { recursive: true });
          }

          if (req.method === 'GET') {
            try {
              const files = fs.readdirSync(sessionsDir).filter(f => f.endsWith('.json'));
              const sessionsList: any[] = [];

              const sessionParseCache: Record<string, { mtimeMs: number; session: any }> = (global as any).__sessionParseCache || {};
              (global as any).__sessionParseCache = sessionParseCache;

              for (const file of files) {
                try {
                  const filePath = path.join(sessionsDir, file);
                  const stats = fs.statSync(filePath);

                  if (sessionParseCache[filePath] && sessionParseCache[filePath].mtimeMs === stats.mtimeMs) {
                    sessionsList.push(sessionParseCache[filePath].session);
                    continue;
                  }

                  const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
                  const meta = content.metadata || {};
                  const history = content.history || [];

                  // Sanitize history: remove tool dumps, collapse intermediate agent steps, extract sources
                  const fileId = file.replace('.json', '');
                  const cleanMessages: any[] = [];
                  let turnSources: any[] = [];
                  const seenUrls = new Set<string>();

                  const collect = (text: string) => {
                    if (!text) return;
                    // Extract markdown links [Title](url)
                    const mdRegex = /\[([^\]]+)\]\((https?:\/\/[^\s\)\"\'>]+)\)/g;
                    let m: RegExpExecArray | null;
                    while ((m = mdRegex.exec(text)) !== null) {
                      const uStr = m[2].trim();
                      const key = uStr.toLowerCase().replace(/\/$/, '');
                      if (!seenUrls.has(key) && !uStr.startsWith('#')) {
                        seenUrls.add(key);
                        try {
                          const domain = new URL(uStr).hostname.replace(/^www\./i, '');
                          turnSources.push({
                            id: `src-${turnSources.length}`,
                            title: m[1].trim(),
                            url: uStr,
                            domain,
                            snippet: uStr,
                            favicon: `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
                          });
                        } catch {}
                      }
                    }

                    // Extract raw URLs
                    const rawRegex = /(https?:\/\/[a-zA-Z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;=%]+)/g;
                    while ((m = rawRegex.exec(text)) !== null) {
                      const uStr = m[1].replace(/[.,;\)]$/, '');
                      const key = uStr.toLowerCase().replace(/\/$/, '');
                      if (!seenUrls.has(key)) {
                        seenUrls.add(key);
                        try {
                          const domain = new URL(uStr).hostname.replace(/^www\./i, '');
                          turnSources.push({
                            id: `src-${turnSources.length}`,
                            title: domain,
                            url: uStr,
                            domain,
                            snippet: uStr,
                            favicon: `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
                          });
                        } catch {}
                      }
                    }
                  };

                  let i = 0;
                  while (i < history.length) {
                    const msg = history[i];
                    const role = msg.role || 'user';
                    const msgContent = msg.content || '';

                    if (role === 'tool') {
                      collect(msgContent);
                      i++;
                      continue;
                    }

                    if (role === 'user') {
                      cleanMessages.push({
                        id: `${fileId}-${cleanMessages.length}`,
                        role: 'user',
                        content: msgContent,
                        timestamp: Date.now() - (history.length - i) * 1000,
                        files: msg.files || undefined,
                        options: msg.options || undefined
                      });
                      turnSources = [];
                      seenUrls.clear();
                      i++;
                      continue;
                    }

                    if (role === 'assistant') {
                      const group: any[] = [];
                      let j = i;
                      while (j < history.length && history[j].role !== 'user') {
                        if (history[j].role === 'tool') {
                          collect(history[j].content || '');
                        } else if (history[j].role === 'assistant') {
                          group.push(history[j]);
                        }
                        j++;
                      }

                      if (group.length > 1) {
                        for (let k = 0; k < group.length - 1; k++) {
                          collect(group[k].content || '');
                        }
                        const finalMsg = group[group.length - 1];
                        collect(finalMsg.content || '');

                        let cleanText = (finalMsg.content || '')
                          .replace(/<think>[\s\S]*?<\/think>/gi, '')
                          .replace(/Web Search Results for '[^']+':[\s\S]*?(?=\n\n(?:Based on|According to|Here are|Summary|In summary|[A-Z#]))/gi, '')
                          .trim();

                        cleanMessages.push({
                          id: `${fileId}-${cleanMessages.length}`,
                          role: 'assistant',
                          content: cleanText || finalMsg.content || '',
                          timestamp: Date.now() - (history.length - j) * 1000,
                          sources: turnSources.length > 0 ? [...turnSources] : (finalMsg.sources || undefined)
                        });
                      } else if (group.length === 1) {
                        const singleMsg = group[0];
                        collect(singleMsg.content || '');

                        let cleanText = (singleMsg.content || '')
                          .replace(/<think>[\s\S]*?<\/think>/gi, '')
                          .replace(/Web Search Results for '[^']+':[\s\S]*?(?=\n\n(?:Based on|According to|Here are|Summary|In summary|[A-Z#]))/gi, '')
                          .trim();

                        if (cleanText || singleMsg.content) {
                          cleanMessages.push({
                            id: `${fileId}-${cleanMessages.length}`,
                            role: 'assistant',
                            content: cleanText || singleMsg.content || '',
                            timestamp: Date.now() - (history.length - j) * 1000,
                            sources: turnSources.length > 0 ? [...turnSources] : (singleMsg.sources || undefined)
                          });
                        }
                      }

                      i = j;
                      continue;
                    }

                    i++;
                  }

                  const messages = cleanMessages;

                  let title = meta.title;
                  if (title) {
                    title = title
                      .replace(/<(?:think|thought)>[\s\S]*?(?:<\/(?:think|thought)>|$)/gi, '')
                      .replace(/^["'«»“”\s*#`_-]+|["'«»“”\s*#`_-]+$/g, '')
                      .trim();
                  }
                  if (!title && messages.length > 0) {
                    const firstUserMsg = messages.find((m: any) => m.role === 'user');
                    if (firstUserMsg && firstUserMsg.content) {
                      const cleanFirst = firstUserMsg.content
                        .replace(/<(?:think|thought)>[\s\S]*?(?:<\/(?:think|thought)>|$)/gi, '')
                        .trim();
                      title = cleanFirst.slice(0, 32) + (cleanFirst.length > 32 ? '...' : '');
                    }
                  }

                  const updatedAt = meta.updated_at ? new Date(meta.updated_at).getTime() : stats.mtimeMs;

                  const sessionObj = {
                    id: meta.session_id || file.replace('.json', ''),
                    title: title || 'New Chat',
                    workspace: targetWs,
                    updatedAt,
                    messages
                  };
                  sessionParseCache[filePath] = { mtimeMs: stats.mtimeMs, session: sessionObj };
                  sessionsList.push(sessionObj);
                } catch {}
              }

              sessionsList.sort((a, b) => b.updatedAt - a.updatedAt);
              sendJson(res, 200, sessionsList);
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }

          if (req.method === 'POST') {
            try {
              const body = await parseJsonBody(req);
              const sessionId = (body.id || Date.now().toString()).replace(/[^a-zA-Z0-9_\-]/g, '_');
              const sessionPath = path.join(sessionsDir, `${sessionId}.json`);

              let cleanTitle = (body.title || 'New Chat')
                .replace(/<(?:think|thought)>[\s\S]*?(?:<\/(?:think|thought)>|$)/gi, '')
                .replace(/^["'«»“”\s*#`_-]+|["'«»“”\s*#`_-]+$/g, '')
                .trim();
              if (!cleanTitle) cleanTitle = 'New Chat';

              const payload = {
                metadata: {
                  session_id: sessionId,
                  title: cleanTitle,
                  workspace: targetWs,
                  updated_at: new Date().toISOString(),
                  message_count: (body.messages || []).length
                },
                history: (body.messages || []).map((m: any) => ({
                  role: m.role,
                  content: m.content,
                  ...(m.sources ? { sources: m.sources } : {}),
                  ...(m.files ? { files: m.files } : {}),
                  ...(m.options ? { options: m.options } : {})
                }))
              };

              fs.writeFileSync(sessionPath, JSON.stringify(payload, null, 2), 'utf-8');
              sendJson(res, 200, { success: true, session: body });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }

          if (req.method === 'DELETE') {
            try {
              const sessionId = (urlObj.searchParams.get('id') || '').replace(/[^a-zA-Z0-9_\-]/g, '_');
              if (sessionId) {
                const sessionPath = path.join(sessionsDir, `${sessionId}.json`);
                if (fs.existsSync(sessionPath)) {
                  fs.unlinkSync(sessionPath);
                }
              }
              sendJson(res, 200, { success: true });
            } catch (err: any) {
              sendJson(res, 500, { error: err.message });
            }
            return;
          }
        }

        // 3.5 POST /api/parse-file - Parse document attachments (.docx, .pdf, txt) into clean readable text
        if (pathname === '/api/parse-file' && req.method === 'POST') {
          try {
            const body = await parseJsonBody(req);
            const filename = body.filename || 'document.txt';
            const rawB64 = (body.data || '').includes(',') ? body.data.split(',')[1] : (body.data || '');
            const buffer = Buffer.from(rawB64, 'base64');

            const tmpFile = path.join(os.tmpdir(), `locallm_${Date.now()}_${path.basename(filename)}`);
            fs.writeFileSync(tmpFile, buffer);
            try {
              const pyScript = [
                'import sys, json',
                'from locallm.core.file_parser import parse_attachment_file',
                'with open(sys.argv[1], "rb") as f: b = f.read()',
                'ok, txt, err = parse_attachment_file(sys.argv[2], b)',
                'print(json.dumps({"success": ok, "text": txt, "error": err}))'
              ].join('\n');

              const pyBin = path.resolve(process.cwd(), '..', '.venv', 'bin', 'python');
              const pyResult = child_process.execFileSync(
                pyBin,
                ['-c', pyScript, tmpFile, filename],
                { encoding: 'utf-8', timeout: 15000 }
              );
              const parsed = JSON.parse(pyResult.trim());
              sendJson(res, parsed.success ? 200 : 400, parsed);
            } finally {
              try { fs.unlinkSync(tmpFile); } catch {}
            }
          } catch (err: any) {
            sendJson(res, 500, { success: false, error: err.message, text: '' });
          }
          return;
        }

        // 4. GET /api/models - Dynamically queries the requested or active service platform
        if (pathname === '/api/models' && req.method === 'GET') {
          const cfg = loadConfigOnDisk();
          const targetBackend = (urlObj.searchParams.get('backend') || cfg.active_backend || 'ollama').trim();

          // Check in-memory cache (60s TTL)
          const now = Date.now();
          if ((global as any).__modelsCache?.[targetBackend] && now - (global as any).__modelsCache[targetBackend].time < 60000) {
            sendJson(res, 200, (global as any).__modelsCache[targetBackend].data);
            return;
          }

          const setModelsCache = (data: any[]) => {
            if (!(global as any).__modelsCache) (global as any).__modelsCache = {};
            (global as any).__modelsCache[targetBackend] = { time: Date.now(), data };
          };

          // Case A: targetBackend is Ollama
          if (targetBackend === 'ollama') {
            try {
              const ollamaHost = cfg.ollama_host || 'http://127.0.0.1:11434';
              const ollamaRes = await fetch(`${ollamaHost}/api/tags`, { signal: AbortSignal.timeout(3000) });
              if (ollamaRes.ok) {
                const data = (await ollamaRes.json()) as any;
                const models = (data.models || []).map((m: any) => ({
                  id: m.name,
                  name: m.name,
                  provider: 'Ollama',
                  platform: 'Ollama',
                  capabilities: {
                    files: true,
                    webSearch: true,
                    tools: m.name.includes('code') || m.name.includes('qwen') || m.name.includes('llama3') || m.name.includes('gemma')
                  }
                }));
                models.unshift({
                  id: 'auto',
                  name: 'Auto Dynamic Router',
                  provider: 'Ollama',
                  platform: 'Ollama',
                  capabilities: { files: true, webSearch: true, tools: true }
                });
                setModelsCache(models);
                sendJson(res, 200, models);
                return;
              }
            } catch (e) {
              console.warn('Failed to fetch from Ollama directly:', e);
            }
          } else {
            // Case B: targetBackend is a custom platform (e.g. vLLM, LocalAI, etc.)
            const platform = (cfg.custom_platforms || []).find((p: any) => p.name.toLowerCase() === targetBackend.toLowerCase());
            if (platform && platform.api_base) {
              try {
                const customRes = await fetch(`${platform.api_base.replace(/\/+$/, '')}/models`, {
                  headers: platform.api_key ? { Authorization: `Bearer ${platform.api_key}` } : {},
                  signal: AbortSignal.timeout(4000)
                });
                if (customRes.ok) {
                  const data = (await customRes.json()) as any;
                  const models = (data.data || []).map((m: any) => {
                    const id = m.id || m.name;
                    return {
                      id,
                      name: id,
                      provider: platform.name,
                      platform: platform.name,
                      capabilities: {
                        files: true,
                        webSearch: true,
                        tools: true
                      }
                    };
                  });
                  models.unshift({
                    id: 'auto',
                    name: 'Auto Dynamic Router',
                    provider: platform.name,
                    platform: platform.name,
                    capabilities: { files: true, webSearch: true, tools: true }
                  });
                  setModelsCache(models);
                  sendJson(res, 200, models);
                  return;
                }
              } catch (e) {
                console.warn(`Failed to fetch models from custom platform ${platform.name}:`, e);
              }
            }
          }

          // Case C: Fallback to querying gateway server on 8080 if running
          const serverPort = cfg.server_port || 8080;
          const apiKey = cfg.server_api_key || '';
          try {
            const gatewayRes = await fetch(`http://127.0.0.1:${serverPort}/v1/models`, {
              headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {}
            });
            if (gatewayRes.ok) {
              const data = (await gatewayRes.json()) as any;
              const platformName = cfg.active_backend === 'ollama' ? 'Ollama' : (cfg.active_backend || 'OpenAI');
              const models = (data.data || []).map((m: any) => {
                const id = m.id;
                const isAgent = id === 'auto' || id === 'locallm-agent';
                return {
                  id,
                  name: isAgent ? (id === 'auto' ? 'Auto Dynamic Router' : 'Autonomous Agent') : id,
                  provider: platformName,
                  platform: platformName,
                  capabilities: {
                    files: true,
                    webSearch: true,
                    tools: isAgent || id.includes('tool') || id.includes('coder')
                  }
                };
              });
              sendJson(res, 200, models);
              return;
            }
          } catch {}

          // Fallback static list
          sendJson(res, 200, [
            { id: cfg.default_model || 'gemma4:12b', name: cfg.default_model || 'gemma4:12b', provider: 'ollama', capabilities: { files: true, webSearch: true, tools: true } },
            { id: 'auto', name: 'Auto Dynamic Router', provider: 'ollama', capabilities: { files: true, webSearch: true, tools: true } }
          ]);
          return;
        }

        // 5. POST /api/chat - Streaming inference bridge
        if (pathname === '/api/chat' && req.method === 'POST') {
          const cfg = loadConfigOnDisk();
          const serverPort = cfg.server_port || 8080;
          const apiKey = cfg.server_api_key || '';

          try {
            const body = await parseJsonBody(req);
            const targetModel = body.model || cfg.default_model || 'gemma4:12b';
            const workspace = body.workspace || cfg.active_workspace || 'default';

            const payload = {
              model: targetModel,
              backend: body.backend || body.platform || body.provider || cfg.active_backend || 'ollama',
              provider: body.provider || cfg.active_backend || 'ollama',
              messages: body.messages || [
                {
                  role: 'user',
                  content: body.message,
                  ...(Array.isArray(body.images) && body.images.length > 0 ? { images: body.images } : {})
                }
              ],
              stream: true,
              temperature: typeof body.temperature === 'number' ? body.temperature : cfg.temperature,
              options: body.options || {}
            };

            const upstream = await fetch(`http://127.0.0.1:${serverPort}/v1/chat/completions`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
                'X-Workspace': workspace,
                'X-Backend': String(payload.backend)
              },
              body: JSON.stringify(payload)
            });

            if (!upstream.ok || !upstream.body) {
              const errText = await upstream.text();
              sendJson(res, upstream.status, { error: errText || 'Inference error' });
              return;
            }

            res.writeHead(200, {
              'Content-Type': 'text/event-stream',
              'Cache-Control': 'no-cache',
              'Connection': 'keep-alive',
              'Access-Control-Allow-Origin': '*'
            });

            const reader = upstream.body.getReader();
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              res.write(value);
            }
            res.end();
            return;
          } catch (err: any) {
            sendJson(res, 500, { error: `Failed to connect to locaLLM API server: ${err.message}` });
            return;
          }
        }

        // 6. POST /api/skills/inspect
        if (pathname === '/api/skills/inspect' && req.method === 'POST') {
          try {
            const body = await parseJsonBody(req);
            const source = (body.source || '').trim();
            if (!source) {
              sendJson(res, 400, { success: false, error: 'Source repository or URL is required.' });
              return;
            }

            const cfg = loadConfigOnDisk();
            const serverPort = cfg.server_port || 8080;
            const apiKey = cfg.server_api_key || '';
            let result: any = null;

            // Try Python gateway server first
            try {
              const gwRes = await fetch(`http://127.0.0.1:${serverPort}/api/skills/inspect`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {})
                },
                body: JSON.stringify({ source }),
                signal: AbortSignal.timeout(30000)
              });
              if (gwRes.ok) {
                result = await gwRes.json();
              }
            } catch {}

            // Fallback to local python invocation if gateway offline
            if (!result) {
              const baseDir = import.meta.dirname || path.resolve('.');
              const pythonBin = path.resolve(baseDir, '../.venv/bin/python');
              const pyScript = `
import json, sys
from locallm.core.workspace import inspect_github_skills
ok, msg, skills, _, _ = inspect_github_skills(sys.argv[1])
print(json.dumps({"success": ok, "message": msg, "skills": skills, "count": len(skills)}))
`;
              const cpRes = child_process.spawnSync(pythonBin, ['-c', pyScript, source], {
                encoding: 'utf-8',
                cwd: path.resolve(baseDir, '..'),
                timeout: 60000
              });
              if (cpRes.stdout) {
                try { result = JSON.parse(cpRes.stdout.trim()); } catch {}
              }
            }

            if (result) {
              sendJson(res, result.success ? 200 : 400, result);
            } else {
              sendJson(res, 500, { success: false, error: 'Inspection failed to return output.' });
            }
          } catch (err: any) {
            sendJson(res, 500, { success: false, error: err.message });
          }
          return;
        }

        // 7. POST /api/skills/install
        if (pathname === '/api/skills/install' && req.method === 'POST') {
          try {
            const body = await parseJsonBody(req);
            const source = (body.source || '').trim();
            const workspace = (body.workspace || '').trim() || 'default';
            const skills = body.skills;

            if (!source) {
              sendJson(res, 400, { success: false, error: 'Source repository or URL is required.' });
              return;
            }

            const cfg = loadConfigOnDisk();
            const serverPort = cfg.server_port || 8080;
            const apiKey = cfg.server_api_key || '';
            let result: any = null;

            // Try Python gateway server first
            try {
              const gwRes = await fetch(`http://127.0.0.1:${serverPort}/api/skills/install`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {})
                },
                body: JSON.stringify({ source, workspace, skills }),
                signal: AbortSignal.timeout(60000)
              });
              if (gwRes.ok) {
                result = await gwRes.json();
              }
            } catch {}

            // Fallback to local python invocation if gateway offline
            if (!result) {
              const baseDir = import.meta.dirname || path.resolve('.');
              const pythonBin = path.resolve(baseDir, '../.venv/bin/python');
              const pyScript = `
import json, sys
from locallm.core.workspace import install_skill_from_source
source = sys.argv[1]
ws = sys.argv[2]
selected = json.loads(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
ok, msg, installed = install_skill_from_source(ws, source, selected)
print(json.dumps({"success": ok, "message": msg, "installed": installed, "count": len(installed)}))
`;
              const cpRes = child_process.spawnSync(pythonBin, ['-c', pyScript, source, workspace, JSON.stringify(skills || null)], {
                encoding: 'utf-8',
                cwd: path.resolve(baseDir, '..'),
                timeout: 90000
              });
              if (cpRes.stdout) {
                try { result = JSON.parse(cpRes.stdout.trim()); } catch {}
              }
            }

            if (result) {
              sendJson(res, result.success ? 200 : 400, result);
            } else {
              sendJson(res, 500, { success: false, error: 'Installation failed to execute.' });
            }
          } catch (err: any) {
            sendJson(res, 500, { success: false, error: err.message });
          }
          return;
        }

        next();
      });
    }
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), locallmBridgePlugin()],
  server: {
    port: 5173,
    host: true,
  },
});
