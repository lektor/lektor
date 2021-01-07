import ToggleGroup from "./ToggleGroup";
import React from "react";
import { render } from "react-dom";
import ReactTestUtils from "react-dom/test-utils";
import { JSDOM } from "jsdom";
import { ok } from "assert";

const jsdom = new JSDOM(`<!DOCTYPE html>`);
// @ts-expect-error Assigning jsdom.window to window fails
global.window = jsdom.window;
const document = window.document;

const renderToggle = (defaultVisibility: boolean) => {
  document.body.innerHTML = "";
  const container = document.createElement("div");
  document.body.appendChild(container);
  render(
    <ToggleGroup groupTitle={"TITLE"} defaultVisibility={defaultVisibility}>
      <div>Rick Astley rulz</div>
    </ToggleGroup>,
    container
  );
  return container;
};

describe("ToggleGroup", () => {
  describe("when rendered with defaults", () => {
    it("renders a closed toggle group", () => {
      const container = renderToggle(false);
      ok(container.innerHTML.includes("toggle-group-closed"));
    });

    it("renders an open toggle group when toggled", () => {
      const container = renderToggle(false);
      const el = document.querySelector(".toggle");
      el && ReactTestUtils.Simulate.click(el);
      ok(container.innerHTML.includes("toggle-group-open"));
    });
  });

  describe("when rendered with a default visibility of true", () => {
    it("renders an open toggle group", () => {
      const container = renderToggle(true);
      ok(container.innerHTML.includes("toggle-group-open"));
    });
  });
});
