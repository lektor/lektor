/* eslint-env worker */
declare let self: SharedWorkerGlobalScope;

/**
 * This is the code that runs in the SharedWorker started by ./lib/livereloader.
 *
 * It connects to the livereload SSE stream from the admin server, lightly processes
 * the received events, then broadcasts them to all connected client windows via
 * the BroadcastChannel API.
 */
import type { BroadcastMessage, LivereloaderConfig } from "./lib/livereloader";
import { sseDataStream } from "./lib/server-sent-events";

// We expect a stream of data-only messages from the /events SSE endpoint.
// The data in the messages are JSON strings which are expected decode to
// one of the following type.
type SSEDataType =
  | { type: "ping"; versionId: string }
  | { type: "reload"; path: string };

/** The livereload shared worker.
 *
 * Streams from the admin GUI SSE stream. Translates and the rebroadcasts
 * messages to all clients.
 */
async function worker({ eventsUrl }: LivereloaderConfig) {
  // Clients listen on this BroadcastChannel for BroadcastMessages
  const broadcastChannel = new BroadcastChannel("live-reload");
  const broadcast = (message: BroadcastMessage) =>
    broadcastChannel.postMessage(message);

  let prevVID: string | undefined;

  for await (const sse of sseDataStream<SSEDataType>(eventsUrl, {
    name: self.name,
  })) {
    switch (sse.type) {
      case "reload":
        // SSEData["reload"] is (somewhat coincidentally) compatible
        // with BroadcastMessage so requires no translation.
        broadcast(sse);
        break;
      case "ping":
        if (prevVID && sse.versionId !== prevVID) {
          console.debug("🔁 live-reload triggering reload.");
          broadcast({ type: "restart" });
        }
        prevVID = sse.versionId;
        break;
    }
  }
}

/**
 * Get the livereload configuration.
 *
 * The livereload configuration is sent as a single message from each
 * client that connects to the shared worker.  (Each of those
 * configurations should, hopefully, be identical.)
 *
 * This function returns a promise that resolves to the configuration
 * contained in the first such message.
 */
function getConfig(): Promise<LivereloaderConfig> {
  return new Promise((resolve) => {
    self.addEventListener("connect", (event) => {
      // we expect one message from the client containing the livereload config
      const port = event.ports[0];
      port.addEventListener(
        "message",
        (event: MessageEvent<LivereloaderConfig>) => resolve(event.data),
        { once: true },
      );
      port.start();
    });
  });
}

/** Fire it up */
getConfig()
  .then((config) => worker(config))
  .catch(console.error);
