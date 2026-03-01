/**
 * An esbuild-powered script to build Lektor's admin frontend.
 */

import { dirname, join, resolve } from "node:path";
import { argv } from "node:process";
import { fileURLToPath } from "node:url";
import { context, type Plugin } from "esbuild";
import fg from "fast-glob";
import { compile } from "sass";

// Optimization: compute fontawesome SVG at compile-time to minimize bundle size
import SVG_ICONS_FONTAWESOME from "./tooldrawer/components/_svg-icons/fontawesome.ts";
import tsconfig from "./tsconfig.json" with { type: "json" };

const { compilerOptions } = tsconfig;

const filename = fileURLToPath(import.meta.url);
const __dirname = dirname(filename);

// A simple esbuild plugin to compile sass.
const sassPlugin: Plugin = {
  name: "sass",
  setup: (build) => {
    build.onResolve({ filter: /\.scss$/ }, ({ path, resolveDir }) => ({
      path: resolve(resolveDir, path),
      namespace: "sass",
      watchFiles: fg.sync(["**/*.scss"], {
        cwd: dirname(resolve(resolveDir, path)),
        absolute: true,
      }),
    }));
    build.onLoad({ filter: /.*/, namespace: "sass" }, ({ path }) => ({
      contents: compile(path, {
        // silence warnings that are caused by bootstrap
        // see https://github.com/twbs/bootstrap/issues/40849
        silenceDeprecations: ["color-functions", "global-builtin", "import"],
      }).css.toString(),
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

const is_main = resolve(process.argv[1] ?? "") === filename;

if (is_main) {
  const dev = argv.includes("--watch");
  runBuild(dev).catch(console.error);
}
