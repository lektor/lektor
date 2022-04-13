"use strict";

{
  const dataset = document.currentScript.dataset;
  const workerScriptPath = dataset.workerScript;
  const eventsPath = dataset.eventsPath;

  if (!window.SharedWorker) {
    console.debug("😭 live-reload cannot work in this browser.");
  } else {
    const worker = new SharedWorker(workerScriptPath, {
      name: "live-reload",
    });

    worker.port.addEventListener("message", (event) => {
      if (event.data === "Reload") {
        location.reload();
      }
    });

    worker.port.postMessage({
      type: "initialize",
      eventsPath,
    });

    worker.port.start();
  }
}
