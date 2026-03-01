import { ok } from "node:assert";
import { before, describe, it } from "node:test";
import ToggleGroup from "./ToggleGroup";
import React, { act } from "react";
import { JSDOM } from "jsdom";
import { createRoot } from "react-dom/client";

before(() => {
  const jsdom = new JSDOM(`<!DOCTYPE html>`);
  // @ts-expect-error Assigning jsdom.window to window fails
  global.window = jsdom.window;
  global.document = window.document;
  // @ts-expect-error To get Reacts act() to work
  global.IS_REACT_ACT_ENVIRONMENT = true;
});

const renderToggle = () => {
  const container = document.createElement("div");
  const root = createRoot(container);
  root.render(
    <ToggleGroup groupTitle={"TITLE"}>
      <div>Rick Astley rulz</div>
    </ToggleGroup>,
  );
  return container;
};

describe("ToggleGroup", () => {
  it("renders a closed toggle group", async () => {
    const container = await act(() => renderToggle());
    ok(container.innerHTML.includes("closed"));
  });

  it("renders an open toggle group when toggled", async () => {
    const container = await act(() => renderToggle());
    const el = container.querySelector("h4");
    ok(el);
    act(() => {
      el.click();
    });
    ok(!container.innerHTML.includes("closed"));
  });
});
