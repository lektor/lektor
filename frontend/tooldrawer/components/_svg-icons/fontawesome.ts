/*
 * Compute JSON.stringifiable object containing SVG markup for a
 * select subset of font-awesome icons.
 *
 * We do this at compile time, to reduce our compiled bundle size.
 * Using @fortawesome/fontawesome-svg-core at runtime pulls in a large
 * chunk of code that more than doubles our bundle size.
 */
import { icon } from "@fortawesome/fontawesome-svg-core";
import { fas } from "@fortawesome/free-solid-svg-icons";

const iconNames = [
  "faAngleLeft",
  "faAngleRight",
  "faFilePen",
  "faRetweet",
  "faThumbtack",
];

function svgFor(iconName: string) {
  if (iconName in fas) {
    return icon(fas[iconName]).html.join("");
  }
  throw new Error(`unknown icon name "${iconName}"`);
}

export default Object.fromEntries(
  iconNames.map((name) => [name, svgFor(name)]),
);
