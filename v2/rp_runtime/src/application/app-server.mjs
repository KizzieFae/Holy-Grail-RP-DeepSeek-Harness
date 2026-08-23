import http from 'node:http';
import { URL } from 'node:url';

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

export function createHolyGrailAppServer(applicationClient, options = {}) {
  const host = options.host ?? '127.0.0.1';
  const port = Number(options.port ?? 0);

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', `http://${host}`);
      const path = url.pathname;

      if (req.method === 'GET' && path === '/api/health') {
        return sendJson(res, 200, applicationClient.getHealth());
      }

      if (req.method === 'GET' && path === '/api/status') {
        return sendJson(res, 200, {
          health: applicationClient.getHealth(),
          active_session_id: applicationClient.activeSessionId,
          transcript: applicationClient.getTranscript(),
        });
      }

      if (req.method === 'GET' && path === '/api/characters') {
        const characters = await applicationClient.listCharacters();
        return sendJson(res, 200, { characters });
      }

      if (req.method === 'GET' && path === '/api/scene-templates') {
        const sceneTemplates = await applicationClient.listSceneTemplates();
        return sendJson(res, 200, { scene_templates: sceneTemplates });
      }

      if (req.method === 'GET' && path.startsWith('/api/scene-templates/') && path.endsWith('/openers')) {
        const templateId = path.slice('/api/scene-templates/'.length, -'/openers'.length);
        const openers = await applicationClient.listTemplateOpeners(templateId);
        return sendJson(res, 200, { template_id: templateId, openers });
      }

      if (req.method === 'GET' && path === '/api/settings/defaults') {
        return sendJson(res, 200, applicationClient.getSettingsView());
      }

      if (req.method === 'GET' && path === '/api/settings/runtime') {
        return sendJson(res, 200, { runtime: applicationClient.getRuntimeSettings() });
      }

      if (req.method === 'PUT' && path === '/api/settings/runtime') {
        const body = await readJson(req);
        try {
          const runtime = applicationClient.updateRuntimeSettings(body);
          return sendJson(res, 200, { runtime });
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          return sendJson(res, 400, { error: message });
        }
      }

      if (req.method === 'POST' && path === '/api/sessions/create') {
        const body = await readJson(req);
        const session = await applicationClient.createSession(body);
        return sendJson(res, 201, {
          session,
          transcript: applicationClient.getTranscript(),
        });
      }

      if (req.method === 'POST' && path === '/api/sessions/open') {
        const body = await readJson(req);
        const hgSessionId = body.hg_session_id ?? body.hgSessionId;
        if (!hgSessionId) return sendJson(res, 400, { error: 'hg_session_id required' });
        const session = await applicationClient.openSession(hgSessionId);
        return sendJson(res, 200, { session });
      }

      if (req.method === 'GET' && path.startsWith('/api/sessions/') && path.endsWith('/state')) {
        const hgSessionId = path.slice('/api/sessions/'.length, -'/state'.length);
        if (hgSessionId !== applicationClient.activeSessionId) {
          await applicationClient.openSession(hgSessionId);
        }
        const state = await applicationClient.getSessionState();
        return sendJson(res, 200, { state });
      }

      if (req.method === 'GET' && path.startsWith('/api/sessions/') && path.endsWith('/transcript')) {
        const hgSessionId = path.slice('/api/sessions/'.length, -'/transcript'.length);
        if (hgSessionId !== applicationClient.activeSessionId) {
          await applicationClient.openSession(hgSessionId);
        }
        return sendJson(res, 200, { transcript: applicationClient.getTranscript() });
      }

      if (req.method === 'GET' && path === '/api/transcript') {
        return sendJson(res, 200, { transcript: applicationClient.getTranscript() });
      }

      if (req.method === 'POST' && path === '/api/turns/submit') {
        const body = await readJson(req);
        try {
          const result = await applicationClient.submitUserTurn(body);
          return sendJson(res, 200, result);
        } catch (err) {
          const failure = err.failure ?? { category: 'round_failure', message: String(err) };
          return sendJson(res, 502, { error: failure, transcript: applicationClient.getTranscript() });
        }
      }

      if (req.method === 'POST' && path === '/api/turns/skip') {
        const body = await readJson(req);
        try {
          const result = await applicationClient.submitSkipTurn(body);
          return sendJson(res, 200, result);
        } catch (err) {
          const failure = err.failure ?? { category: 'round_failure', message: String(err) };
          return sendJson(res, 502, { error: failure, transcript: applicationClient.getTranscript() });
        }
      }

      return sendJson(res, 404, { error: 'not found' });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return sendJson(res, 500, { error: message });
    }
  });

  return {
    server,
    async listen(listenPort = port) {
      await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(listenPort, host, resolve);
      });
      const address = server.address();
      const resolvedPort = typeof address === 'object' && address ? address.port : listenPort;
      return { host, port: resolvedPort, baseUrl: `http://${host}:${resolvedPort}` };
    },
    async close() {
      await new Promise((resolve, reject) => {
        server.close((err) => (err ? reject(err) : resolve()));
      });
    },
  };
}
