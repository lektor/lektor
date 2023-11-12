/**
 * An esbuild-powered script to build Lektor's admin frontend.
 */

import { context, Plugin } from "esbuild";
import fg from "fast-glob";
import { resolve, dirname, join } from "path";
import { argv } from "process";
import { compile } from "sass";

import { compilerOptions } from "./tsconfig.json";

// Optimization: compute fontawesome SVG at compile-time to minimize bundle size
import SVG_ICONS_FONTAWESOME from "./tooldrawer/components/_svg-icons/fontawesome";

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
  const ctx = await context({
    entryPoints: {
      app: join(__dirname, "js", "main.tsx"),
      tooldrawer: join(__dirname, "tooldrawer"),
      "livereload-worker": join(
        __dirname,
        "tooldrawer",
        "livereload-worker.ts",
      ),
    },
    outdir: join(__dirname, "..", "lektor", "admin", "static"),
    format: "iife",
    bundle: true,
    target: compilerOptions.target,
    loader: {
      ".eot": "empty",
      ".ttf": "empty",
      ".svg": "empty",
      ".woff": "empty",
      // Only keep the modern small woff2 font files
      ".woff2": "file",
    },
    plugins: [sassPlugin],
    // Always produce sourcemaps, but only include the full source in dev.
    sourcemap: true,
    sourcesContent: dev,
    // The following options differ between dev and prod builds.
    // For prod builds, we want to use React's prod build and minify.
    define: {
      "process.env.NODE_ENV": dev ? '"development"' : '"production"',
      SVG_ICONS_FONTAWESOME: JSON.stringify(SVG_ICONS_FONTAWESOME),
    },
    // Only minify syntax (like DCE and not by removing whitespace and renaming
    // identifiers). This keeps the bundle size a bit larger but still very
    // readable.
    minifySyntax: !dev,
    logLevel: dev ? "info" : "warning",
  });
  console.log("starting build");
  await ctx.rebuild();
  console.log("finished build");
  if (!dev) {
    await ctx.dispose();
  } else {
    console.log("starting watch mode");
    await ctx.watch();
  }
}

if (require.main === module) {
  const dev = argv.includes("--watch");
  runBuild(dev).catch(console.error);
}
