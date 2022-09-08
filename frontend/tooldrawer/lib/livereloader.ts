export interface LivereloaderConfig {
  eventsUrl: string;
  workerJs: string;
  artifactName: string;
}

export type ReloadMessage = {
  type: "reload";
  path: string; // artifact_name
};

export type RestartMessage = {
  type: "restart";
};

export type BroadcastMessage = RestartMessage | ReloadMessage;

/**
 * Runs a SharedWorker to connect to the livereload SSE stream.
 * from the Lektor admin server.
 *
 * TheSharedWorker broadcasts (a filtered set) of received events
 * to all interested clients via a BroadcastChannel.
 *
 * When this controller reacts to the received messages, when
 * appropriate, by reloading the current page.
 *
 * Auto-reloading may be disabled by setting the `disabled` attribute
 * of the Livereloader. When reloading is re-enabled (by clearing the
 * `disabled` attribute) the page will reload if any reloads were
 * suppressed while disabled.
 */
export class Livereloader {
  artifactName: string;
  private _stale: boolean = false;
  private _disabled: boolean = false;

  constructor(config: LivereloaderConfig) {
    this.artifactName = config.artifactName;

    new BroadcastChannel("live-reload").addEventListener(
      "message",
      this._listener,
    );

    const workerPort = new SharedWorker(config.workerJs, {
      name: "livereload-worker",
    }).port;
    workerPort.start();
    workerPort.postMessage(config);
  }

  get disabled() {
    return this._disabled;
  }

  set disabled(disabled: boolean) {
    this._disabled = disabled;
    if (!disabled && this._stale) {
      this._reload();
    }
  }

  private _reload() {
    location.reload();
    this._stale = false;
  }

  private _listener = (event: MessageEvent<BroadcastMessage>) => {
    if (this._shouldReload(event.data)) {
      this._stale = true;
      if (!this._disabled) {
        this._reload();
      }
    }
  };

  private _shouldReload(message: BroadcastMessage) {
    switch (message.type) {
      case "restart":
        return true;
      case "reload":
        return message.path === this.artifactName;
      default:
        return false;
    }
  }
}

export default Livereloader;
