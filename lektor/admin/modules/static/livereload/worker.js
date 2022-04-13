/* eslint-env worker */
"use strict";

let eventsPath = null;
let port = null;
let currentVersionId = null;
let eventSource = null;

addEventListener("connect", (event) => {
  // Only keep one active port, for whichever tab was last loaded.
  if (port) {
    port.close();
  }
  port = event.ports[0];
  port.addEventListener("message", receiveMessage);
  port.start();
});

const receiveMessage = (event) => {
  if (event.data.type === "initialize") {
    const givenEventsPath = event.data.eventsPath;

    if (givenEventsPath !== eventsPath) {
      if (eventSource) {
        eventSource.close();
      }

      resetConnectTimeout();

      setTimeout(connectToEvents, 0);
    }

    eventsPath = event.data.eventsPath;
  }
};

let connectAttempts;
let connectTimeoutMs;

const resetConnectTimeout = () => {
  connectAttempts = 0;
  connectTimeoutMs = 100;
};
resetConnectTimeout();

const bumpConnectTimeout = () => {
  connectAttempts++;

  if (connectTimeoutMs === 100 && connectAttempts === 20) {
    connectAttempts = 0;
    connectTimeoutMs = 300;
  } else if (connectTimeoutMs === 300 && connectAttempts === 20) {
    connectAttempts = 0;
    connectTimeoutMs = 1000;
  } else if (connectTimeoutMs === 1000 && connectAttempts === 20) {
    connectAttempts = 0;
    connectTimeoutMs = 3000;
  } else if (connectAttempts === 100) {
    // Give up after 5 minutes.
    console.debug(
      "😢 live-reload failed to connect after 5 minutes, shutting down."
    );
    close();
    return;
  }
  if (connectAttempts === 0) {
    console.debug(
      "😅 live-reload EventSource error, retrying every " +
        connectTimeoutMs +
        "ms"
    );
  }
};

const connectToEvents = () => {
  if (!eventsPath) {
    setTimeout(connectToEvents, connectTimeoutMs);
    return;
  }

  eventSource = new EventSource(eventsPath);

  eventSource.addEventListener("open", () => {
    console.debug("😎 live-reload connected");
  });

  eventSource.addEventListener("message", (event) => {
    // Reset connection timeout when receiving a message, as it’s proof that
    // we are actually connected.
    resetConnectTimeout();

    const message = JSON.parse(event.data);

    if (message.type === "ping") {
      if (currentVersionId !== null && currentVersionId !== message.versionId) {
        console.debug("🔁 live-reload triggering reload.");
        port.postMessage("Reload");
      }

      currentVersionId = message.versionId;
    } else if (message.type === "reload") {
      port.postMessage("Reload");
    }
  });

  eventSource.addEventListener("error", () => {
    eventSource.close();
    eventSource = null;
    bumpConnectTimeout();
    setTimeout(connectToEvents, connectTimeoutMs);
  });
};
