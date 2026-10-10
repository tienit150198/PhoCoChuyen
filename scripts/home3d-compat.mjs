/** Narrow, tested transforms for pinned Three 0.186.1. No global Safari gate exemption.
 * Box3.union is a vector min/max method (not the new Set API); inline that operation.
 * WebGLTextures caches an OffscreenCanvas probe; repeat typeof at the use site so the
 * old-iPhone gate can verify the guard without interprocedural/dataflow analysis. */
export function homeCompatibility(path,source){
  if(path.replaceAll('\\','/').endsWith('math/Box3.js'))return source.replace('this.union( _box );','this.min.min( _box.min ); this.max.max( _box.max );');
  if(path.replaceAll('\\','/').endsWith('renderers/webgl/WebGLTextures.js'))return source.replace('return useOffscreenCanvas ?',"return useOffscreenCanvas && typeof OffscreenCanvas !== 'undefined' ?");
  return source;
}
