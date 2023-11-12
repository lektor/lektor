import { css, html, LitElement } from "lit";
import { customElement, eventOptions, state } from "lit/decorators.js";
import { WindowEventListenerController } from "./controllers/window-event-listener";

interface DragPosition {
  clientX: number;
  clientY: number;
}

type DragEventInit = EventInit & DragPosition;

export class DragEvent extends Event implements DragPosition {
  clientX: number;
  clientY: number;

  constructor(type_: string, init: DragEventInit) {
    super(type_, init);
    this.clientX = init.clientX;
    this.clientY = init.clientY;
  }
}

declare global {
  interface HTMLElementEventMap {
    "drag-start": DragEvent;
    "drag-move": DragEvent;
    "drag-stop": Event;
  }

  interface HTMLElementTagNameMap {
    "lektor-drag-handle": DragHandle;
  }
}

/**
 * A drag handle.
 *
 * This widget generates drag-start, drag-move, and drag-end events
 * when attempts are made to drag it.
 */
@customElement("lektor-drag-handle")
export class DragHandle extends LitElement {
  @state()
  private _dragging: boolean = false;

  override render() {
    /* eslint-disable @typescript-eslint/unbound-method */
    return html`
      <div
        id="handle"
        aria-hidden="true"
        title="Drag to reposition"
        @mousedown=${this._onmousedown}
        @touchstart=${this._ontouchstart}
      >
        <div id="icon"></div>
      </div>
      ${this._dragging ? html`<div id="cover"></div>` : null}
    `;
    /* eslint-enable */
  }

  private _windowEventListeners = new WindowEventListenerController(this, {
    passive: true,
    capture: true,
  });

  private _onmousedown(event: MouseEvent) {
    if (event.buttons === 1) {
      event.preventDefault();
      // eslint-disable-next-line @typescript-eslint/unbound-method
      this._windowEventListeners.add("mousemove", this._onmousemove);
      // eslint-disable-next-line @typescript-eslint/unbound-method
      this._windowEventListeners.add("mouseup", this._dragStop);
      this._drag("drag-start", event);
    }
  }

  private _onmousemove(event: MouseEvent) {
    if (event.buttons !== 1) {
      this._dragStop();
    } else {
      this._drag("drag-move", event);
    }
  }

  @eventOptions({ passive: true, capture: true })
  private _ontouchstart(event: TouchEvent) {
    if (event.targetTouches.length === 1) {
      /* eslint-disable @typescript-eslint/unbound-method */
      this._windowEventListeners.add("touchmove", this._ontouchmove);
      this._windowEventListeners.add("touchend", this._dragStop);
      this._windowEventListeners.add("touchcancel", this._dragStop);
      /* eslint-enable */
      this._drag("drag-start", event.targetTouches[0]);
    }
  }

  private _ontouchmove(event: TouchEvent) {
    if (event.targetTouches.length !== 1) {
      this._dragStop();
    } else {
      this._drag("drag-move", event.targetTouches[0]);
    }
  }

  private _drag(eventType: "drag-start" | "drag-move", pos: DragPosition) {
    this._dragging = true;
    this.dispatchEvent(
      new DragEvent(eventType, {
        bubbles: true,
        composed: true,
        clientX: pos.clientX,
        clientY: pos.clientY,
      }),
    );
  }

  private _dragStop() {
    this._dragging = false;
    this._windowEventListeners.clear();
    this.dispatchEvent(
      new Event("drag-stop", { bubbles: true, composed: true }),
    );
  }

  static override styles = css`
    #handle {
      --dot-size: 6px;
      --margin: 2px;
      cursor: grab;
      width: calc(2 * var(--dot-size) + 2 * var(--margin));
      height: 100%;
      display: flex;
    }
    #icon {
      margin: var(--margin);
      flex-grow: 1;
      background: radial-gradient(currentcolor 35%, transparent 45%) left /
        var(--dot-size) var(--dot-size) repeat space;
    }

    #cover {
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      right: 0;
      z-index: 10000;
      cursor: grabbing;
    }
  `;
}
