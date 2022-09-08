import type { PropertyValues } from "lit";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";

import { WindowEventListenerController } from "./controllers/window-event-listener";
import { WidgetMixin } from "./widget";
import type { DragEvent } from "./drag-handle";

import "./drag-handle";
import "./icon";

declare global {
  interface HTMLElementTagNameMap {
    "lektor-drawer": LektorDrawer;
  }
}

/** A draggable, collapsible tool drawer.
 *
 * This drawer sits on the right side of the screen. Its vertical position may be
 * adjusted by dragging.
 *
 * It is possible to collapse to minimize how much of the page it obscures. A collapsed
 * drawer will open when hovered over or when the collapse button is clicked.
 */
@customElement("lektor-drawer")
export class LektorDrawer extends WidgetMixin(LitElement) {
  @property({ attribute: false })
  override widgetRole = "menubar";

  @property({ type: Boolean, reflect: true })
  open = true;

  /* Position of top of tooldrawer in pixels from the top of the viewport. */
  @property({ attribute: false })
  clientY = 5;

  // This._closing is set temporarily when the user clicks the toggle
  // to close the drawer.  When set, the .closing class is added to
  // the drawer, disabling the auto-open-on-hover effect (thus
  // allowing the drawer to actually close.)
  @state()
  private _closing = false;

  @query("#drawer", true)
  private _drawer!: HTMLDivElement;

  private _hostStyle: CSSStyleDeclaration;

  constructor() {
    super();
    const windowEventListeners = new WindowEventListenerController(this);
    // eslint-disable-next-line @typescript-eslint/unbound-method
    windowEventListeners.add("resize", this._clampPosition);
    this._hostStyle = getComputedStyle(this);
  }

  override firstUpdated() {
    this._clampPosition();
  }

  override willUpdate(changedProperties: PropertyValues<this>) {
    this._closing =
      changedProperties.has("open") &&
      !this.open &&
      this.hasUpdated &&
      this._drawer.matches(":hover");

    if (changedProperties.has("clientY")) {
      this._clampPosition();
    }
  }

  /**
   * Clamp vertical position of tool drawer to ensure that it is visible.
   */
  private _clampPosition() {
    // NB: can not compute drawer height until after first update
    if (this.hasUpdated) {
      const marginTop = parseInt(this._hostStyle.marginTop);
      const marginBottom = parseInt(this._hostStyle.marginBottom);
      const ymax =
        window.innerHeight - this._drawer.offsetHeight - marginBottom;
      this.clientY = Math.max(marginTop, Math.min(ymax, this.clientY));
    }
  }

  override render() {
    /* eslint-disable @typescript-eslint/unbound-method */
    return html`
      <div
        id="drawer"
        role="menubar"
        class=${classMap({
          open: this.open,
          closing: this._closing,
        })}
        style="top: ${this.clientY}px;"
        @keydown=${this._onkeydown}
        @mouseleave=${this._closing ? this._mouseleave : nothing}
        title=${(this.tooltip ?? this.label) || nothing}
        aria-label=${this.label}
      >
        ${this._renderToggle()}
        <slot></slot>
        ${this._renderDragHandle()}
      </div>
    `;
    /* eslint-enable */
  }

  private _mouseleave() {
    this._closing = false;
  }

  private _onkeydown(event: KeyboardEvent) {
    // Support navigation between menubar items with arrow keys.
    // Ref: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/menubar_role#keyboard_interactions

    const navKeyFocusNextMap = {
      ArrowLeft: (cur: Element) => cur.previousElementSibling,
      ArrowRight: (cur: Element) => cur.nextElementSibling,
      Home: (cur: Element) => cur.parentElement?.firstElementChild,
      End: (cur: Element) => cur.parentElement?.lastElementChild,
      ArrowUp: () => null,
      ArrowDown: () => null,
    } as const;
    type NavKey = keyof typeof navKeyFocusNextMap;

    if (event.code in navKeyFocusNextMap) {
      const keycode = event.code as NavKey;
      const focused = event.target as HTMLElement;
      const focusNext = navKeyFocusNextMap[keycode](focused);

      event.preventDefault();
      if (focusNext instanceof HTMLElement) focusNext.focus();
    }
  }

  private _renderToggle() {
    /* eslint-disable @typescript-eslint/unbound-method */
    return html`
      <div
        id="toggle"
        class="control"
        title="Click to hide/show drawer"
        aria-hidden="true"
        @click=${this._toggle}
      >
        <lektor-icon id="icon-open" .icon=${"faAngleRight"}></lektor-icon>
        <lektor-icon id="icon-closed" .icon=${"faAngleLeft"}></lektor-icon>
        <lektor-icon id="icon-hovered" .icon=${"faThumbtack"}></lektor-icon>
      </div>
    `;
    /* eslint-enable */
  }

  private _toggle() {
    this.open = !this.open;
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  private _renderDragHandle() {
    /* eslint-disable @typescript-eslint/unbound-method */
    return html`
      <lektor-drag-handle
        class="control"
        @drag-start=${this._ondragstart}
        @drag-move=${this._ondragmove}
        @drag-stop=${this._ondragstop}
      ></lektor-drag-handle>
    `;
    /* eslint-enable */
  }

  private _dragOffset!: number;

  private _ondragstart(event: DragEvent) {
    this._dragOffset = this.clientY - event.clientY;
  }

  private _ondragmove(event: DragEvent) {
    this.clientY = event.clientY + this._dragOffset;
  }

  private _ondragstop() {
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  static override styles = css`
    :host {
      /* The top and bottom margins of the host are used to set
       * limits the drag range of the drawer. */
      margin: 5px 0px;
    }
    #drawer {
      position: fixed;
      right: 0;
      z-index: 1000;

      min-height: 32px; /* 2rem */
      color: var(--lektor-drawer-color, hsl(336, 16%, 50%));
      background-color: var(--lektor-drawer-bg, hsla(24, 5%, 85%, 0.87));
      border: 1px solid var(--lektor-drawer-border-color, hsl(24, 2%, 67%));
      border-right: none;
      border-radius: 3px 0 0 3px;

      display: flex;

      /* move drawer off-screen to the right just enough to leave the toggle control visible */
      transform: translateX(calc(100% - 17px));
      transition: transform 0.5s ease-out;
    }
    #drawer.open,
    #drawer:not(.closing):where(:hover, :active, :focus-within) {
      /* open drawer */
      transform: none;
    }

    .control:is(:hover, :active) {
      color: var(--lektor-drawer-hover-color, hsl(336, 43%, 33%));
    }

    #toggle {
      cursor: pointer;
      display: flex;
      align-items: center;
    }
    lektor-icon {
      width: 12px;
      margin: 2px;
    }
    #drawer:not(.open) #icon-open,
    #drawer:where(.open, .closing, :not(:hover, :active, :focus-within))
      #icon-hovered,
    #drawer:where(.open, :not(.closing):where(:hover, :active, :focus-within))
      #icon-closed {
      display: none;
    }

    ::slotted(*) {
      font-size: 28px;
    }

    slot {
      margin: 3px;
      display: flex;
      align-items: center;
      gap: 3px;
    }
  `;
}
