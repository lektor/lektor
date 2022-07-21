/**
 * An esbuild-powered script to build Lektor's admin frontend.
 */

import { build, Plugin } from "esbuild";
import fg from "fast-glob";
import { resolve, dirname, join } from "path";
import { argv } from "process";
import { compile } from "sass";

// A simple esbuild plugin to compile sass.
const sassPlugin: Plugin = {
  name: "sass",
  setup: ({ onResolve, onLoad }) => {
    onResolve({ filter: /\.scss$/ }, ({ path, resolveDir }) => ({
      path: resolve(resolveDir, path),
      namespace: "sass",
      watchFiles: fg.sync(["**/*.scss"], {
        cwd: dirname(resolve(resolveDir, path)),
        absolute: true,
      }),
    }));
    onLoad({ filter: /.*/, namespace: "sass" }, ({ path }) => ({
      contents: compile(path).css.toString(),
      resolveDir: dirname(path),
      loader: "css",
    }));
  },
};

/**
 * Build the frontend using esbuild.
 * @param dev - Whether to generate sourcemaps and watch for changes.
 */
async function runBuild(dev: boolean) {
  console.log("starting build");
  await build({
    entryPoints: [join(__dirname, "js", "main.tsx")],
    outfile: join(__dirname, "..", "lektor", "admin", "static", "app.js"),
    format: "iife",
    bundle: true,
    loader: {
      ".eot": "file",
      ".ttf": "file",
      ".svg": "file",
      ".woff": "file",
      ".woff2": "file",
    },
    plugins: [sassPlugin],
    sourcemap: true,
    // The following options differ between dev and prod builds.
    // For prod builds, we want to use React's prod build and minify.
    define: { "process.env.NODE_ENV": dev ? '"development"' : '"production"' },
    // Only minify syntax (like DCE and not by removing whitespace and renaming
    // identifiers). This keeps the bundle size a bit larger but still very
    // readable.
    minifySyntax: !dev,
    // For dev builds, watch source files and rebuild.
    watch: dev ? { onRebuild: () => console.log("finished rebuild") } : false,
  });
  console.log("finished build");
}

if (require.main === module) {
  const dev = argv.includes("--watch");
  runBuild(dev).catch(console.error);
}
