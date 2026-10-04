import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as http from 'http';

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
            // Provide compatibility aliases
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

                // Read skills files
                const skills: any[] = [];
                const skillDir = path.join(wsPath, 'skills');
                if (fs.existsSync(skillDir)) {
                  try {
                    const sFiles = fs.readdirSync(skillDir).filter(f => f.endsWith('.md') || f.endsWith('.txt'));
                    for (const sf of sFiles) {
                      const sContent = fs.readFileSync(path.join(skillDir, sf), 'utf-8');
                      const sId = sf.replace(/\.(md|txt)$/, '');
                      const firstLine = sContent.split('\n')[0] || '';
                      const sName = firstLine.replace(/^[#\s*]+/, '').replace(/^Skill:\s*/i, '').trim() || sId;
                      skills.push({
                        id: sId,
                        name: sName,
                        content: sContent,
                        enabled: true
                      });
                    }
                  } catch {}
                }

                workspaces.push({
                  name: entry.name,
                  description: meta.description || '',
                  icon: meta.icon || 'Folder',
                  color: meta.color || '#3B82F6',
                  custom_instructions: meta.custom_instructions || '',
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
              const cleanName = (body.name || '').trim().replace(/[^a-zA-Z0-9_\-]/g, '-').toLowerCase();
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
              const cleanName = (body.name || '').trim().toLowerCase();
              if (!cleanName) {
                sendJson(res, 400, { error: 'Workspace name is required' });
                return;
              }

              let currentWsDir = path.join(wsDir, cleanName);
              if (!fs.existsSync(currentWsDir)) {
                sendJson(res, 404, { error: `Workspace '${cleanName}' not found` });
                return;
              }

              // Handle rename if newName specified and different
              let finalName = cleanName;
              if (body.newName && body.newName.trim().toLowerCase() !== cleanName && cleanName !== 'default') {
                const cleanNewName = body.newName.trim().replace(/[^a-zA-Z0-9_\-]/g, '-').toLowerCase();
                const newWsDir = path.join(wsDir, cleanNewName);
                if (!fs.existsSync(newWsDir)) {
                  fs.renameSync(currentWsDir, newWsDir);
                  currentWsDir = newWsDir;
                  finalName = cleanNewName;
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

              // Sync skills
              if (Array.isArray(body.skills)) {
                const skillDir = path.join(currentWsDir, 'skills');
                if (!fs.existsSync(skillDir)) fs.mkdirSync(skillDir, { recursive: true });

                const existingFiles = fs.readdirSync(skillDir).filter(f => f.endsWith('.md') || f.endsWith('.txt'));
                const newFileNames = new Set(body.skills.map((s: any) => `${(s.id || s.name).toLowerCase().replace(/[^a-z0-9_-]/g, '-')}.md`));

                // Remove deleted skills
                for (const ef of existingFiles) {
                  if (!newFileNames.has(ef)) {
                    try { fs.unlinkSync(path.join(skillDir, ef)); } catch {}
                  }
                }

                // Write active skills
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
                name: finalName,
                description: meta.description || '',
                icon: meta.icon || 'Folder',
                color: meta.color || '#3B82F6',
                custom_instructions: meta.custom_instructions || '',
                skills: body.skills || [],
                skillsCount: Array.isArray(body.skills) ? body.skills.length : 0
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

              for (const file of files) {
                try {
                  const filePath = path.join(sessionsDir, file);
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
                        timestamp: Date.now() - (history.length - i) * 1000
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
                  if (!title && messages.length > 0) {
                    const firstUserMsg = messages.find((m: any) => m.role === 'user');
                    if (firstUserMsg) {
                      title = firstUserMsg.content.slice(0, 32) + (firstUserMsg.content.length > 32 ? '...' : '');
                    }
                  }

                  const stats = fs.statSync(filePath);
                  const updatedAt = meta.updated_at ? new Date(meta.updated_at).getTime() : stats.mtimeMs;

                  sessionsList.push({
                    id: meta.session_id || file.replace('.json', ''),
                    title: title || 'New Chat',
                    workspace: targetWs,
                    updatedAt,
                    messages
                  });
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

              const payload = {
                metadata: {
                  session_id: sessionId,
                  title: body.title || 'New Chat',
                  workspace: targetWs,
                  updated_at: new Date().toISOString(),
                  message_count: (body.messages || []).length
                },
                history: (body.messages || []).map((m: any) => ({
                  role: m.role,
                  content: m.content,
                  ...(m.sources ? { sources: m.sources } : {})
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
            // Case B: targetBackend is a custom platform (e.g. iForte-GPU, vLLM, etc.)
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
              messages: body.messages || [{ role: 'user', content: body.message }],
              stream: true,
              temperature: typeof body.temperature === 'number' ? body.temperature : cfg.temperature,
              options: body.options || {}
            };

            const upstream = await fetch(`http://127.0.0.1:${serverPort}/v1/chat/completions`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
                'X-Workspace': workspace
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
