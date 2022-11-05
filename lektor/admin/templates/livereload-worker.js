/* eslint-env worker */
"use strict";

const eventsPath = {{ events_url|tojson }};
let currentVersionId = null;
let eventSource = null;

const retryInterval = 1000;
const channel = new BroadcastChannel("live-reload");

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
        channel.postMessage({type: "restart"});
      }

      currentVersionId = message.versionId;
    } else if (message.type === "reload") {
      channel.postMessage(message);
    }
  });

  eventSource.addEventListener("error", () => {
    eventSource.close();
    eventSource = null;
    setTimeout(connectToEvents, retryInterval);
  });
};

connectToEvents();
