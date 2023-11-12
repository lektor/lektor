/** A limited equivalent of python's asyncio.Condition
 */
export class Condition {
  private _promise!: Promise<void>;
  private _resolve = () => {};

  constructor() {
    this.notify_all();
  }

  notify_all() {
    this._resolve();
    this._promise = new Promise<void>((resolve) => {
      this._resolve = resolve;
    });
  }

  wait() {
    return this._promise;
  }
}

export default Condition;
