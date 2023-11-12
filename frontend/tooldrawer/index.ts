import { html, render } from "lit";

import { Livereloader, LivereloaderConfig } from "./lib/livereloader";
import { Marshall, marshallTypes as types } from "./lib/marshall";

import "./components/drawer";
import "./components/icon";
import "./components/link-button";
import "./components/livereload-widget";

// Configuration injected into HTML by lektor/admin/modules/serve.py
interface TooldrawerConfig {
  editUrl?: string;
  livereloadConfig?: LivereloaderConfig;
}
declare global {
  // eslint-disable-next-line no-var
  var TOOLDRAWER_CONFIG: TooldrawerConfig;
}

const { editUrl, livereloadConfig } = globalThis.TOOLDRAWER_CONFIG ?? {};

// skip if in iframe
if (window === window.top && (editUrl || livereloadConfig)) {
  document.addEventListener(
    "DOMContentLoaded",
    () => {
      render(tooldrawer({ editUrl, livereloadConfig }), document.body);
      persistDrawerState(document.getElementsByTagName("lektor-drawer")![0]);
    },
    { once: true },
  );
}

function tooldrawer({ editUrl, livereloadConfig }: TooldrawerConfig) {
  const tools = new Array<ReturnType<typeof html>>();

  if (editUrl) {
    tools.push(html`
      <lektor-link-button
        .href=${editUrl}
        .widgetRole=${"menuitem"}
        .label=${"Edit Page"}
      >
        <lektor-icon icon="faFilePen"></lektor-icon>
      </lektor-link-button>
    `);
  }
  if (livereloadConfig) {
    const livereloader = new Livereloader(livereloadConfig);
    tools.push(html`
      <lektor-livereload-widget
        .widgetRole=${"menuitemcheckbox"}
        .label=${"Enable Live-Reload"}
        .livereloader=${livereloader}
      ></lektor-livereload-widget>
    `);
  }

  return html`
    <lektor-drawer .widgetRole=${"menubar"} .label=${"Lektor Controls"}>
      ${tools}
    </lektor-drawer>
  `;
}

function persistDrawerState(drawer: HTMLElementTagNameMap["lektor-drawer"]) {
  const storage = localStorage;
  const storageKey = "com.getlektor--tooldrawer-state";
  const marshall = new Marshall({
    open: types.boolean,
    clientY: types.number,
  });

  try {
    const savedState = marshall.deserialize(
      storage.getItem(storageKey) ?? "{}",
    );
    Object.assign(drawer, savedState);
  } catch (err) {
    console.log("ignoring invalid saved drawer state: %o", err);
  }

  drawer.addEventListener("change", () => {
    storage.setItem(storageKey, marshall.serialize(drawer));
  });
}
