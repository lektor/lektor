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
      eventsPath = event.data.eventsPath;
      if (eventSource) {
        eventSource.close();
      }
      setTimeout(connectToEvents, 0);
    }
  }
};

const retryInterval = 1000;

const connectToEvents = () => {
  if (!eventsPath) {
    setTimeout(connectToEvents, retryInterval);
    return;
  }

  eventSource = new EventSource(eventsPath);

  eventSource.addEventListener("open", () => {
    console.debug("😎 live-reload connected");
  });

  eventSource.addEventListener("message", (event) => {
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
    setTimeout(connectToEvents, retryInterval);
  });
};
