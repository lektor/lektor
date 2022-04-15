/* eslint-env worker */
"use strict";

const eventsPath = {{ events_url|tojson }};
let currentVersionId = null;
let eventSource = null;
let ports = [];

addEventListener("connect", (event) => {
  const port = event.ports[0];
  port.start();
  ports.push(port);
});

const retryInterval = 1000;

const connectToEvents = () => {

  eventSource = new EventSource(eventsPath);

  eventSource.addEventListener("open", () => {
    console.debug("😎 live-reload connected");
  });

  eventSource.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "ping") {
      if (currentVersionId !== null && currentVersionId !== message.versionId) {
        console.debug("🔁 live-reload triggering reload.");
        ports.forEach((port) => port.postMessage({type: "restart"}));
      }

      currentVersionId = message.versionId;
    } else if (message.type === "reload") {
      ports.forEach((port) => port.postMessage(message));
    }
  });

  eventSource.addEventListener("error", () => {
    eventSource.close();
    eventSource = null;
    setTimeout(connectToEvents, retryInterval);
  });
};

connectToEvents();
