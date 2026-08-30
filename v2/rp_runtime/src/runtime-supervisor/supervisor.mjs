import { createHolyGrailRpContext } from '../bootstrap.mjs';
import { startDomainHost, stopDomainHostProcess } from './domain-host-process.mjs';

/**
 * Supervises Domain Host process lifecycle and DSH runtime bootstrap.
 * Does not own RP/domain semantics.
 */
export class HolyGrailRuntimeSupervisor {
  constructor(options = {}) {
    this.options = options;
    this.domainHost = null;
    this.domainHostUrl = null;
    this.runtime = null;
    this.state = 'idle';
    this.lastError = null;
  }

  get ready() {
    return this.state === 'ready';
  }

  async start() {
    if (this.state === 'ready') {
      return this.getReadyState();
    }
    this.state = 'starting';
    this.lastError = null;

    const externalUrl = this.options.domainHostUrl ?? this.options.domainApi?.baseUrl;
    if (externalUrl) {
      this.domainHostUrl = String(externalUrl).replace(/\/$/, '');
      this.domainHost = null;
    } else {
      try {
        this.domainHost = await startDomainHost(this.options.domainHost ?? {});
        this.domainHostUrl = this.domainHost.baseUrl;
        process.env.HG_DOMAIN_HOST_URL = this.domainHostUrl;
      } catch (err) {
        this.state = 'failed';
        this.lastError = err;
        throw err;
      }
    }

    try {
      this.runtime = await createHolyGrailRpContext({
        ...this.options.runtime,
        domainApi: { baseUrl: this.domainHostUrl },
      });
      this.state = 'ready';
      return this.getReadyState();
    } catch (err) {
      this.lastError = err;
      await this.stop();
      this.state = 'failed';
      throw err;
    }
  }

  getReadyState() {
    return {
      domain_host: this.domainHost ? 'healthy' : 'external',
      domain_host_url: this.domainHostUrl,
      dsh_runtime: this.state === 'ready' ? 'ready' : this.state,
      supervisor_state: this.state,
      ...(this.domainHost?.health ?? {}),
    };
  }

  async stop() {
    if (this.runtime?.ctx) {
      await this.runtime.ctx.fiber.dispose();
      this.runtime = null;
    }
    let stopResult = null;
    if (this.domainHost?.proc) {
      stopResult = await stopDomainHostProcess(this.domainHost.proc, this.options.shutdown ?? {});
      this.domainHost = null;
    }
    this.state = 'stopped';
    return stopResult;
  }

  onDomainHostExit(handler) {
    if (!this.domainHost?.proc) return;
    this.domainHost.proc.on('exit', handler);
  }
}

export async function startSupervisedRuntime(options = {}) {
  const supervisor = new HolyGrailRuntimeSupervisor(options);
  const ready = await supervisor.start();
  return { supervisor, ready, ...supervisor.runtime };
}
