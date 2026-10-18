"""🖼️ Khung danh hiệu, step 1: cut the avatar frame and the chat bubble out of each concept board of the owner's pack
"Phố Có Chuyện — 72 bộ khung" (1254x1254 PNG boards on cream paper, 17/10). Step 2: scripts/build_honour_frames.py.

usage: python -I scripts/cut_honour_frames.py <pack dir> <out dir> [ids...]
Writes <out>/<id>_av.png, <id>_chat.png (RGBA, full resolution) and meta.json:
  av: crop size, window centre + radius (the avatar's circle) in crop pixels
  chat: crop size, window box (the text area) in crop pixels
"""
import json, os, sys, glob
import numpy as np
from PIL import Image
from scipy import ndimage as nd

F_DIFF = 45        # a pixel this far from the paper (max channel) belongs to a drawing
AA_DIFF = 12       # anti-aliased edge pixels next to a drawing
NEAR = 14          # decorations this close to the frame belong to it


def paper(a):
    band = a[240:700]
    q = (band // 4).reshape(-1, 3)
    vals, cnt = np.unique(q, axis=0, return_counts=True)
    return vals[cnt.argmax()] * 4 + 2


def window(lab, boxes, area, seeds, wide, h, w):
    """The light region (not touching the board's edge) the seeds fall in: the biggest that looks like a window."""
    best = None
    for x, y in seeds:
        l = int(lab[y, x])
        if not l:
            continue
        sy, sx = boxes[l - 1]
        if sy.start == 0 or sx.start == 0 or sy.stop == h or sx.stop == w:
            continue
        bw, bh = sx.stop - sx.start, sy.stop - sy.start
        if wide and not (bw > 350 and 120 < bh < 420):
            continue
        if not wide and not (180 < bw < 520 and 180 < bh < 520 and 0.7 < bw / bh < 1.4):
            continue
        if best is None or area[l] > area[best]:
            best = l
    return best


TOP_Y = 236        # the boards' titles end above this
LABEL_Y = 688      # the "Khung avatar" / "Khung chat" labels start below this


# Boards whose label or background art touches the frame: a clip box (x0, y0, x1, y1) in board pixels.
CLIP = {('36', 'av'): [(0, 0, 1254, 672)], ('13', 'av'): [(0, 0, 1254, 684)], ('50', 'av'): [(0, 0, 1254, 686)],
        ('60', 'av'): [(226, 316, 292, 745), (70, 338, 470, 745), (25, 520, 470, 745)], ('60', 'chat'): [(470, 422, 1230, 750), (1040, 385, 1225, 750)]}


def region(win_mask, wide, h, w, clip=None):
    ys, xs = np.nonzero(win_mask)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    W, H = x1 - x0, y1 - y0
    if wide:
        y0, y1, x0, x1 = y0 - 0.5 * H, y1 + 0.4 * H, x0 - 0.14 * W, x1 + 0.1 * W
    else:
        y0, y1, x0, x1 = y0 - 0.45 * H, y1 + 0.4 * H, x0 - 0.42 * W, x1 + 0.42 * W
    E = np.zeros((h, w), bool)
    E[max(TOP_Y, int(y0)):min(h, int(y1)), max(0, int(x0)):min(w, int(x1))] = True
    if clip:
        C = np.zeros((h, w), bool)
        for x0, y0, x1, y1 in clip:
            C[y0:y1, x0:x1] = True
        E &= C
    return E


def cut(a, bg, diff, win_mask, keep_window, E):
    F = diff > F_DIFF
    flab, fn = nd.label(F, structure=np.ones((3, 3)))
    # the frame itself: the biggest drawing around the window (with what touches it), mostly inside the region
    big = np.bincount(flab.ravel())
    inE = np.bincount(flab[E].ravel(), minlength=len(big))
    inE[0] = 0
    mid = int(inE.argmax())
    main = (flab == mid) & E
    near = nd.binary_dilation(main, iterations=NEAR)
    ids = np.unique(flab[near & F])
    ids = ids[ids > 0]
    boxes = nd.find_objects(flab)
    sizes = np.bincount(flab.ravel())
    inside = np.bincount(flab[E].ravel(), minlength=len(sizes))
    wy = np.nonzero(win_mask)[0]
    low = wy.max() + 0.05 * (wy.max() - wy.min())   # the "Khung avatar" label starts below the frame's own bottom
    ids = [i for i in ids if inside[i] >= 0.85 * sizes[i] and boxes[i - 1][0].start < min(LABEL_Y, low)]
    obj = (np.isin(flab, ids) | main) & E
    # anti-aliased rims
    obj |= nd.binary_dilation(obj, iterations=1) & (diff > AA_DIFF) & E
    filled = nd.binary_fill_holes(obj | win_mask)
    holes = filled & ~obj
    hlab, hn = nd.label(holes)
    opaque = obj.copy()
    for i in range(1, hn + 1):
        m = hlab == i
        n = int(m.sum())
        if (m & win_mask).sum() > n * 0.5:
            if keep_window:
                opaque |= m
            continue
        if n < 3000 or diff[m].mean() > 8:
            opaque |= m
    if keep_window:
        opaque |= win_mask
    ys, xs = np.nonzero(opaque)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([a, (opaque * 255).astype(np.uint8)])[y0:y1, x0:x1]
    return Image.fromarray(rgba.astype(np.uint8), 'RGBA'), (x0, y0)


def board(path, num=''):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
    bg = paper(a)
    diff = np.abs(a - bg).max(axis=2)
    free = diff <= F_DIFF
    lab, n = nd.label(free)
    area = np.bincount(lab.ravel())
    boxes = nd.find_objects(lab)
    h, w = free.shape
    av_seeds = [(x, y) for x in range(120, 430, 30) for y in range(330, 600, 30)]
    ch_seeds = [(x, y) for x in range(620, 1180, 20) for y in range(380, 640, 20)]
    av = window(lab, boxes, area, av_seeds, False, h, w)
    ch = window(lab, boxes, area, ch_seeds, True, h, w)
    out = {}
    a8 = a.astype(np.uint8)
    if av:
        wm = nd.binary_fill_holes(lab == av)
        img, (ox, oy) = cut(a8, bg, diff, wm, False, region(wm, False, h, w, CLIP.get((num, 'av'))))
        ys, xs = np.nonzero(wm)
        out['av'] = dict(img=img, cx=float(xs.mean() - ox), cy=float(ys.mean() - oy), r=float(np.sqrt(wm.sum() / np.pi)))
    if ch:
        wm = nd.binary_fill_holes(lab == ch)
        img, (ox, oy) = cut(a8, bg, diff, wm, True, region(wm, True, h, w, CLIP.get((num, 'chat'))))
        ys, xs = np.nonzero(wm)
        out['chat'] = dict(img=img, box=[int(xs.min() - ox), int(ys.min() - oy), int(xs.max() - ox + 1), int(ys.max() - oy + 1)],
                           fill=[int(v) for v in np.median(a[ys, xs], axis=0)])
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    want = set(sys.argv[3:])
    os.makedirs(dst, exist_ok=True)
    meta_path = os.path.join(dst, 'meta.json')
    meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
    for p in sorted(glob.glob(os.path.join(src, '*', '*.png'))):
        num = os.path.basename(p)[:2]
        if want and num not in want:
            continue
        r = board(p, num)
        m = dict(file=os.path.relpath(p, src).replace('\\', '/'))
        if 'av' in r:
            r['av']['img'].save(os.path.join(dst, f'{num}_av.png'))
            m['av'] = dict(w=r['av']['img'].width, h=r['av']['img'].height, cx=round(r['av']['cx'], 1), cy=round(r['av']['cy'], 1), r=round(r['av']['r'], 1))
        if 'chat' in r:
            r['chat']['img'].save(os.path.join(dst, f'{num}_chat.png'))
            m['chat'] = dict(w=r['chat']['img'].width, h=r['chat']['img'].height, box=r['chat']['box'], fill=r['chat']['fill'])
        meta[num] = m
        print(num, 'av' in r, 'chat' in r, m.get('av', {}).get('w'), m.get('chat', {}).get('w'), flush=True)
    json.dump(meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
