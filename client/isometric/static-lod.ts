/** Scene-owned rasters for static images viewed far below their source resolution.
 * The caller owns the original texture/frame and restores it when get() returns null.
 * This helper never changes a display object, source image, frame, or animation.
 */
export interface StaticLodFrame {
  source: CanvasImageSource;
  frameId: string | number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface StaticLodRaster {
  readonly key: string;
  readonly canvas: HTMLCanvasElement;
  readonly width: number;
  readonly height: number;
  readonly source: CanvasImageSource;
  readonly frameId: string | number;
}

export interface StaticLodOptions {
  createCanvas?: (width: number, height: number) => HTMLCanvasElement;
  keyPrefix?: string;
  maxEntries?: number;
}

let cacheSequence = 0;
const LEVELS = [64, 128, 256] as const;
const makeCanvas = (width: number, height: number): HTMLCanvasElement => {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  return canvas;
};

export class StaticLodCache {
  private readonly createCanvas: NonNullable<StaticLodOptions['createCanvas']>;
  private readonly prefix: string;
  private readonly limit: number;
  private sourceIds = new WeakMap<CanvasImageSource, number>();
  private readonly entries = new Map<string, StaticLodRaster>();
  private sourceSequence = 0;
  private builds = 0;
  private disposed = false;

  constructor(options: StaticLodOptions = {}) {
    this.createCanvas = options.createCanvas ?? makeCanvas;
    this.prefix = options.keyPrefix ?? `static-lod-${++cacheSequence}`;
    this.limit = Number.isFinite(options.maxEntries) ? Math.max(1, Math.min(1024, Math.floor(options.maxEntries!))) : 256;
  }

  /** displayWidth/Height are world display dimensions, resolution is renderer DPR.
   * Keep at least two source samples per projected screen pixel on both axes.
   * The longest raster edge has only three possible sizes, never a per-zoom size.
   */
  get(frame: Readonly<StaticLodFrame>, displayWidth: number, displayHeight: number, zoom: number, resolution = 1): StaticLodRaster | null {
    if (this.disposed || !frame.source || typeof frame.source !== 'object') return null;
    const geometry = [frame.x, frame.y, frame.width, frame.height, displayWidth, displayHeight, zoom, resolution];
    if (!geometry.every(Number.isFinite) || frame.x < 0 || frame.y < 0 || geometry.slice(2).some(value => value <= 0)) return null;

    const scale = Math.max(displayWidth / frame.width, displayHeight / frame.height) * zoom * resolution;
    if (scale >= .5) return null; // An original no larger than 2× the target already fits.
    const longest = Math.max(frame.width, frame.height);
    const level = LEVELS.find(value => value >= longest * scale * 2);
    if (level === undefined || level >= longest) return null;

    let sourceId = this.sourceIds.get(frame.source);
    if (sourceId === undefined) {
      sourceId = ++this.sourceSequence;
      this.sourceIds.set(frame.source, sourceId);
    }
    const key = `${this.prefix}:${sourceId}:${JSON.stringify([frame.frameId, frame.x, frame.y, frame.width, frame.height])}:${level}`;
    const hit = this.entries.get(key);
    if (hit) {
      this.entries.delete(key);
      this.entries.set(key, hit);
      return hit;
    }

    const width = Math.max(1, Math.round(frame.width * level / longest));
    const height = Math.max(1, Math.round(frame.height * level / longest));
    const canvas = this.createCanvas(width, height);
    const context = canvas.getContext('2d');
    if (!context) return null;
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    context.drawImage(frame.source, frame.x, frame.y, frame.width, frame.height, 0, 0, width, height);
    const raster: StaticLodRaster = {key, canvas, width, height, source: frame.source, frameId: frame.frameId};
    this.entries.set(key, raster);
    this.builds++;
    while (this.entries.size > this.limit) this.entries.delete(this.entries.keys().next().value!);
    return raster;
  }

  stats(): {entries: number; pixels: number; builds: number} {
    let pixels = 0;
    for (const raster of this.entries.values()) pixels += raster.width * raster.height;
    return {entries: this.entries.size, pixels, builds: this.builds};
  }

  /** Release after the owning scene has released its registered raster textures.
   * Do not resize canvases here: an external texture may still reference one.
   */
  dispose(): void {
    this.disposed = true;
    this.entries.clear();
    this.sourceIds = new WeakMap();
  }
}
