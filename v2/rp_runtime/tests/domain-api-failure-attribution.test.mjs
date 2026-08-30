import assert from 'node:assert/strict';
import http from 'node:http';
import test from 'node:test';

import {
  DomainApiTransportError,
  createDomainApiClient,
} from '../src/lib/domain-api-client.mjs';
import {
  FORENSIC_BOUNDARIES,
  classifyFailureBoundary,
  extractEnvironmentCognitionFailure,
} from '../src/lib/narrator-forensic-attribution.mjs';

function startMockServer(handler) {
  return new Promise((resolve) => {
    const server = http.createServer(handler);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({
        server,
        baseUrl: `http://127.0.0.1:${port}`,
        async close() {
          await new Promise((done) => server.close(done));
        },
      });
    });
  });
}

test('fetch rejection yields structured DomainApiTransportError', async () => {
  const api = createDomainApiClient('http://127.0.0.1:1');
  await assert.rejects(
    () => api.listCharacters(),
    (error) => {
      assert.ok(error instanceof DomainApiTransportError);
      assert.equal(error.failureClass, 'transport_error');
      assert.equal(error.operation, 'listCharacters');
      assert.equal(error.path, '/v1/catalog/characters');
      assert.ok(error.cause);
      assert.notEqual(error.failureClass, 'host_internal_error');
      return true;
    },
  );
});

test('GET transport failure preserves operation and path', async () => {
  const api = createDomainApiClient('http://127.0.0.1:1');
  await assert.rejects(
    () => api.listSceneTemplates(),
    (error) => {
      assert.equal(error.operation, 'listSceneTemplates');
      assert.equal(error.path, '/v1/catalog/scene-templates');
      return true;
    },
  );
});

test('POST transport failure preserves operation and path', async () => {
  const api = createDomainApiClient('http://127.0.0.1:1');
  await assert.rejects(
    () => api.createSession({ cast: ['Alice'] }),
    (error) => {
      assert.equal(error.operation, 'createSession');
      assert.equal(error.path, '/v1/sessions/create');
      return true;
    },
  );
});

test('HTTP 500 host_internal_error is application failure not transport', async () => {
  const mock = await startMockServer((_req, res) => {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      error: 'internal handler error',
      error_kind: 'host_internal_error',
    }));
  });
  try {
    const api = createDomainApiClient(mock.baseUrl);
    await assert.rejects(
      () => api.listCharacters(),
      (error) => {
        assert.equal(error.name, 'DomainApiHttpError');
        assert.equal(error.failureClass, 'host_internal_error');
        assert.equal(error.httpStatus, 500);
        assert.equal(error.errorKind, 'host_internal_error');
        assert.equal(error.operation, 'listCharacters');
        assert.equal(error.path, '/v1/catalog/characters');
        assert.notEqual(error.failureClass, 'transport_error');
        return true;
      },
    );
  } finally {
    await mock.close();
  }
});

test('HTTP 503 persistence_failure remains service_unavailable', async () => {
  const mock = await startMockServer((_req, res) => {
    res.writeHead(503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      error: 'persistence unavailable',
      error_kind: 'persistence_failure',
    }));
  });
  try {
    const api = createDomainApiClient(mock.baseUrl);
    await assert.rejects(
      () => api.prepareDirectorContext({}),
      (error) => {
        assert.equal(error.failureClass, 'service_unavailable');
        assert.equal(error.errorKind, 'persistence_failure');
        return true;
      },
    );
  } finally {
    await mock.close();
  }
});

test('HTTP 400 remains api_http_error', async () => {
  const mock = await startMockServer((_req, res) => {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'missing field' }));
  });
  try {
    const api = createDomainApiClient(mock.baseUrl);
    await assert.rejects(
      () => api.prepareDirectorContext({}),
      (error) => {
        assert.equal(error.failureClass, 'api_http_error');
        assert.equal(error.httpStatus, 400);
        return true;
      },
    );
  } finally {
    await mock.close();
  }
});

test('forensic attribution distinguishes transport and host internal errors', () => {
  const transport = new DomainApiTransportError({
    label: 'listCharacters',
    path: '/v1/catalog/characters',
    cause: Object.assign(new Error('connect ECONNREFUSED'), { code: 'ECONNREFUSED' }),
  });
  const transportExtracted = extractEnvironmentCognitionFailure(transport);
  assert.equal(transportExtracted.boundary, FORENSIC_BOUNDARIES.DOMAIN_API);
  assert.match(transportExtracted.reason, /ECONNREFUSED/);

  const hostInternal = Object.assign(new Error('Domain API /v1/catalog/characters failed (500): {}'), {
    name: 'DomainApiHttpError',
    failureClass: 'host_internal_error',
    errorKind: 'host_internal_error',
  });
  assert.equal(classifyFailureBoundary(hostInternal), FORENSIC_BOUNDARIES.DOMAIN_API);
  const hostExtracted = extractEnvironmentCognitionFailure(hostInternal);
  assert.equal(hostExtracted.reason, 'host_internal_error');
});
