"""OMR reader reference implementation for template ksat-2027-math.

Pipeline: corner-mark registration (homography) -> red-channel drop-out ->
per-bubble darkness -> per-field decision with flags.
Pure OpenCV/NumPy, CPU only.
"""
import json, sys
import cv2, numpy as np

CANVAS_W, CANVAS_H = 3508, 2480  # canonical working resolution (A4 landscape @300dpi)


def load_template(path):
    return json.load(open(path, encoding='utf-8'))


def find_corner_marks(img):
    """Return the 4 black corner marks (TL, TR, BL, BR) as pixel centers."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    blk = (gray < 90).astype(np.uint8) * 255
    blk = cv2.morphologyEx(blk, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(blk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = []
    scale = w / CANVAS_W
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if area < 120 * scale * scale or bw > 200 * scale or bh > 200 * scale:
            continue
        if cv2.contourArea(c) / area < 0.6:
            continue
        blobs.append((x + bw / 2, y + bh / 2))
    if len(blobs) < 4:
        raise RuntimeError('corner marks not found')
    # corner marks are the outermost black blobs on the sheet: take the extremes
    # along the two diagonals (robust to the sheet being scaled/rotated inside a photo)
    P = np.array(blobs)
    s, d = P[:, 0] + P[:, 1], P[:, 0] - P[:, 1]
    tl, br, tr, bl = P[s.argmin()], P[s.argmax()], P[d.argmax()], P[d.argmin()]
    return np.float32([tl, tr, bl, br])


def register(img, tpl):
    src = find_corner_marks(img)
    c = tpl['timing_marks']['corners']
    dst = np.float32([[c[k]['x'] * CANVAS_W, c[k]['y'] * CANVAS_H]
                      for k in ('top_left', 'top_right', 'bottom_left', 'bottom_right')])
    Hm = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, Hm, (CANVAS_W, CANVAS_H), borderValue=(255, 255, 255))


def darkness_map(warped):
    """Pink print drops out on the red channel; black pen marks stay dark."""
    r = warped[:, :, 2]
    return 255 - r  # 0 = white, 255 = solid black


def bubble_darkness(dark, b, rx, ry):
    cx, cy = int(b['x'] * CANVAS_W), int(b['y'] * CANVAS_H)
    mask = np.zeros_like(dark)
    cv2.ellipse(mask, (cx, cy), (max(1, int(rx * 0.8)), max(1, int(ry * 0.8))), 0, 0, 360, 255, -1)
    return float(dark[mask == 255].mean())


def decide(values, abs_th=70.0, rel=0.5):
    """values: list of (label, darkness). Returns (labels_marked, flag)."""
    if not values:
        return [], 'empty'
    mx = max(v for _, v in values)
    marked = [l for l, v in values if v >= abs_th and v >= rel * mx]
    if not marked:
        return [], 'blank'
    if len(marked) > 1:
        return marked, 'multi'
    # low confidence when the runner-up is close
    others = sorted([v for l, v in values if l != marked[0]], reverse=True)
    if others and mx - others[0] < 25:
        return marked, 'low_confidence'
    return marked, 'ok'


def read_sheet(img, tpl):
    warped = register(img, tpl)
    dark = darkness_map(warped)
    rx = tpl['bubble_radius']['rx'] * CANVAS_W
    ry = tpl['bubble_radius']['ry'] * CANVAS_H
    result = {'answers': {}, 'flags': {}, 'exam_number': None, 'form': None, 'absent': False}

    for f in tpl['fields']:
        if f['kind'] == 'multiple_choice':
            byq = {}
            for b in f['bubbles']:
                byq.setdefault(b['q'], []).append((b['choice'], bubble_darkness(dark, b, rx, ry)))
            for q, vals in byq.items():
                marked, flag = decide(vals)
                result['answers'][q] = marked[0] if len(marked) == 1 else (marked or None)
                result['flags'][q] = flag
        elif f['kind'] == 'short_answer':
            q = f['bubbles'][0]['q']
            cols = {}
            for b in f['bubbles']:
                cols.setdefault(b['place'], []).append((b['digit'], bubble_darkness(dark, b, rx, ry)))
            digits, flags = {}, []
            for place in ('hundreds', 'tens', 'ones'):
                marked, flag = decide(cols[place])
                digits[place] = marked[0] if len(marked) == 1 else None
                if flag in ('multi', 'low_confidence'):
                    flags.append(f'{place}:{flag}')
            if digits['ones'] is None:
                result['answers'][q] = None
                flags.append('blank')
            else:
                result['answers'][q] = (digits['hundreds'] or 0) * 100 + (digits['tens'] or 0) * 10 + digits['ones']
            result['flags'][q] = ','.join(flags) or 'ok'
        elif f['kind'] == 'digit_columns':
            cols = {}
            for b in f['bubbles']:
                cols.setdefault(b['col'], []).append((b['digit'], bubble_darkness(dark, b, rx, ry)))
            num, bad = '', False
            for col in sorted(cols):
                marked, flag = decide(cols[col])
                if len(marked) != 1:
                    bad = True
                    num += '?'
                else:
                    num += str(marked[0])
            result['exam_number'] = num
            result['flags']['exam_number'] = 'incomplete' if bad else 'ok'
        elif f['kind'] == 'single':
            b = f['bubbles'][0]
            on = bubble_darkness(dark, b, rx, ry) >= 70
            if f['name'] == 'form_odd' and on:
                result['form'] = 'odd'
            elif f['name'] == 'form_even' and on:
                result['form'] = 'even'
            elif f['name'] == 'absent':
                result['absent'] = on
    return result, warped


if __name__ == '__main__':
    tpl = load_template(sys.argv[1])
    img = cv2.imread(sys.argv[2])
    res, _ = read_sheet(img, tpl)
    print(json.dumps(res, ensure_ascii=False, indent=1))
