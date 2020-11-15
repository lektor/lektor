/* eslint-env mocha */
import { expect } from "chai";
import ToggleGroup from "./ToggleGroup";
import React from "react";
import ReactDOM, { render } from "react-dom";
import ReactTestUtils from "react-dom/test-utils";
import JSDOMGlobal from "jsdom-global";

JSDOMGlobal();

const renderToggle = (defaultVisibility) => {
  document.body.innerHTML = '<div id="container"></div>';
  ReactDOM.render(
    <ToggleGroup defaultVisibility={defaultVisibility}>
      <div>Rick Astley rulz</div>
    </ToggleGroup>,
    document.getElementById("container")
  );
};

describe("ToggleGroup", () => {
  describe("when rendered with defaults", () => {
    it("renders a closed toggle group", () => {
      renderToggle(false);
      expect(document.getElementById("container").innerHTML).to.contain(
        "toggle-group-closed"
      );
    });

    it("renders an open toggle group when toggled", () => {
      renderToggle(false);
      ReactTestUtils.Simulate.click(document.querySelector(".toggle"));
      expect(document.getElementById("container").innerHTML).to.contain(
        "toggle-group-open"
      );
    });
  });

  describe("when rendered with a default visibility of true", () => {
    it("renders an open toggle group", () => {
      renderToggle(true);
      expect(document.getElementById("container").innerHTML).to.contain(
        "toggle-group-open"
      );
    });
  });
});
