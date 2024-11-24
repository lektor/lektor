import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeSVG } from "lit/directives/unsafe-svg.js";

/*
 * SVG_ICONS_FONTAWESOME gets defined in our esbuild config to a
 * pre-evaluated version of ./_svg-icons/fontawesome.ts.
 *
 * Equivalently, to compute the SVG icons at runtime, we could:
 *
 *     import SVG_ICONS_FONTAWESOME from "./_svg-icons/fontawesome.ts";
 *
 * however, this more than doubles the size of our bundle by pulling
 * in @fortawesome/fontawesome-svg-core.
 */
declare const SVG_ICONS_FONTAWESOME: { [name: string]: string };

const iconSvg = new Map<string, ReturnType<typeof html>>(
  Object.entries(SVG_ICONS_FONTAWESOME ?? {}).map(([name, svg]) => [
    name,
    html`${unsafeSVG(svg)}`,
  ]),
);
if (iconSvg.size === 0) {
  console.warn("No icon data is available");
}

declare global {
  interface HTMLElementTagNameMap {
    "lektor-icon": LektorIcon;
  }
}

/**
 * An icon, implemented as a SVG image.
 *
 * A small custom subset of the fontawesome icons are available.
 */
@customElement("lektor-icon")
export class LektorIcon extends LitElement {
  /**
   * Select which icon to display.
   */
  @property()
  icon: string = "";

  override render() {
    return iconSvg.get(this.icon);
  }

  static override styles = css`
    :host {
      width: 1em;
      display: flex;
      place-items: center stretch;
    }
  `;
}
