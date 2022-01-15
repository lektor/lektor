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

const renderToggle = () => {
  document.body.innerHTML = "";
  const container = document.createElement("div");
  document.body.appendChild(container);
  render(
    <ToggleGroup groupTitle={"TITLE"}>
      <div>Rick Astley rulz</div>
    </ToggleGroup>,
    container
  );
  return container;
};

describe("ToggleGroup", () => {
  it("renders a closed toggle group", () => {
    const container = renderToggle();
    ok(container.innerHTML.includes("closed"));
  });

  it("renders an open toggle group when toggled", () => {
    const container = renderToggle();
    const el = document.querySelector(".toggle-group h4");
    el && ReactTestUtils.Simulate.click(el);
    ok(!container.innerHTML.includes("closed"));
  });
});
