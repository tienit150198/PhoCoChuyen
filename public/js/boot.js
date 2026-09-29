/* Starts the /api/bootstrap request while the module graph is still downloading (a classic async script
 * with no imports, so it runs as soon as it arrives). api.js init() picks the request up; without it,
 * init() simply fetches on its own. */
try{globalThis.__mnlBoot={sent:Date.now(),response:fetch('/api/bootstrap',{credentials:'same-origin'})};}catch{/* old browser: api.js fetches */}
