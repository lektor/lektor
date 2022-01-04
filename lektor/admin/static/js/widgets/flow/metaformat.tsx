/** Check whether the (trimmed) line is at least 3 chars wide and only dashes. */
export function lineIsDashes(rawLine: string): boolean {
  const line = rawLine.trim();
  return line.length >= 3 && line.match(/[^-]/) === null;
}

export function processBuf(buf: string[]): string[] {
  if (buf.length === 0) {
    return buf;
  }
  const lines = buf.map((line) => (lineIsDashes(line) ? line.substr(1) : line));
  const lastLine = lines[lines.length - 1];
  if (lastLine[lastLine.length - 1] === "\n") {
    // trim newline at the end of the last line.
    lines[lines.length - 1] = lastLine.substr(0, lastLine.length - 1);
  }
  return lines;
}

function trimTabsAndSpaces(str: string): string {
  const match = str.match(/^[\t ]*(.*?)[\t ]*$/m);
  return match ? match[1] : "";
}

export function tokenize(lines: string[]): [string, string[]][] {
  let key: string | null = null;
  let buf: string[] = [];
  let wantNewline = false;
  const rv: [string, string[]][] = [];

  function flushItem() {
    if (key !== null) {
      rv.push([key, processBuf(buf)]);
      key = null;
      buf = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const match = lines[i].match(/^(.*?)(\r?\n)*$/m);
    const line = match ? `${match[1]}\n` : "\n";

    if (line.trimRight() === "---") {
      wantNewline = false;
      flushItem();
    } else if (key !== null) {
      if (wantNewline) {
        wantNewline = false;
        if (line.match(/^\s*$/)) {
          continue;
        }
      }
      buf.push(line);
    } else {
      const bits = line.split(":");
      if (bits.length >= 2) {
        const [rawKey, ...rest] = bits;
        key = rawKey.trim();
        const firstBit = trimTabsAndSpaces(rest.join(":"));
        if (!firstBit.match(/^\s*$/)) {
          buf = [firstBit];
        } else {
          buf = [];
          wantNewline = true;
        }
      }
    }
  }

  flushItem();
  return rv;
}

export function serialize(blocks: [string, string][]): string[] {
  const rv: string[] = [];

  blocks.forEach((item, idx) => {
    const [key, value] = item;
    if (idx > 0) {
      rv.push("---\n");
    }
    if (value.match(/([\r\n]|(^[\t ])|([\t ]$))/m)) {
      rv.push(key + ":\n");
      rv.push("\n");
      const lines = value.split(/\n/);
      if (lines[lines.length - 1] === "") {
        lines.pop();
      }
      lines.forEach((line) => {
        rv.push(lineIsDashes(line) ? `-${line}\n` : `${line}\n`);
      });
    } else {
      rv.push(key + ": " + value + "\n");
    }
  });

  return rv;
}
