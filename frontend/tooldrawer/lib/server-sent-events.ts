import Condition from "./condition";

/** Connect to SSE endpoint.
 *
 * This async generator connects to an SSE stream at `url` then yields
 * JSON-decoded data from the data-only messages in the stream.
 *
 * The generic parameter `T` may be used to specify the expected type
 * of the decoded JSON data. (But note that no run-time checking of
 * the values is performed.)
 */
export async function* sseDataStream<T extends object = object>(
  url: string,
  options?: { name?: string },
): AsyncIterable<T> {
  const queue = new Array<T>();
  const condition = new Condition();

  const eventSource = new EventSource(url);
  eventSource.addEventListener("message", (event: MessageEvent<string>) => {
    queue.push(JSON.parse(event.data) as T);
    condition.notify_all();
  });
  // diagnostics
  const name = options?.name || "sseDataStream";

  eventSource.addEventListener("open", () => {
    console.debug(`😎 ${name} connected to ${url}`);
  });
  eventSource.addEventListener("error", () => {
    // Note that EventStream will handle retries on its own.
    console.debug(`😞 ${name} connection to ${url} failed`);
  });

  for (;;) {
    yield* queue.splice(0);
    await condition.wait();
  }
}
