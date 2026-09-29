/** Versioned URL of a static file: '/css/desk.css' -> '/css/desk.css?v=<content hash>' from the page's
 * import map (read by boot.js; see game/webassets.py). Unknown files and pages without a map keep
 * the plain URL, which the server answers with no-cache. ES modules need nothing: the import map
 * already resolves every import() to its versioned URL. */
export const asset=url=>globalThis.__mnlBoot?.asset?.(url)||url;
