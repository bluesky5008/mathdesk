import numpy as np, json, cv2
B = np.load('bubbles_dedup.npy')
img = cv2.imread('omr300.png'); H, W = img.shape[:2]
S = 2  # half-scale coords -> full

def in_region(b, x0, y0, x1, y1):
    return x0*S <= b[0] <= x1*S and y0*S <= b[1] <= y1*S

def cluster(vals, gap):
    vals = sorted(vals); groups = [[vals[0]]]
    for v in vals[1:]:
        if v - groups[-1][-1] > gap: groups.append([v])
        else: groups[-1].append(v)
    return [float(np.mean(g)) for g in groups]

def grid(region, gap_x=18, gap_y=18):
    pts = [b for b in B if in_region(b, *region)]
    xs = cluster([p[0] for p in pts], gap_x); ys = cluster([p[1] for p in pts], gap_y)
    cells = {}
    for p in pts:
        ci = int(np.argmin([abs(p[0]-x) for x in xs])); ri = int(np.argmin([abs(p[1]-y) for y in ys]))
        cells[(ri, ci)] = (round(p[0], 1), round(p[1], 1))
    return xs, ys, cells

fields = []
def add(name, kind, region, rows, cols, labels_fn, meta=None):
    xs, ys, cells = grid(region)
    if len(xs) != cols or len(ys) != rows:
        print(f'WARN {name}: got {len(ys)} rows x {len(xs)} cols, expected {rows}x{cols}')
    items = []
    for (ri, ci), (x, y) in sorted(cells.items()):
        lab = labels_fn(ri, ci)
        if lab is None: continue
        items.append({**lab, 'x': round(x / W, 5), 'y': round(y / H, 5)})
    fields.append({'name': name, 'kind': kind, **(meta or {}), 'bubbles': items})
    print(f'{name}: {len(items)} bubbles ({len(ys)} rows x {len(xs)} cols)')

# 객관식 blocks: rows = question, cols = choice 1..5
def mc(first_q):
    return lambda ri, ci: {'q': first_q + ri, 'choice': ci + 1}
add('common_1_10',  'multiple_choice', (630, 165, 790, 645), 10, 5, mc(1))
add('common_11_15', 'multiple_choice', (845, 165, 995, 400), 5, 5, mc(11))
add('elective_23_28', 'multiple_choice', (1215, 735, 1365, 1020), 6, 5, mc(23))

# 단답형: 3 cols (백/십/일) ; rows 0..9 ; 백 has no 0 (row 0 empty)
def sa(q):
    def f(ri, ci):
        digit = ri  # row index equals digit (row 0 = '0' row, absent in 백 col)
        return {'q': q, 'place': ['hundreds', 'tens', 'ones'][ci], 'digit': digit}
    return f
sa_regions = {16: (1385, 165, 1480, 650), 17: (1505, 165, 1600, 650),
              18: (570, 735, 670, 1220), 19: (690, 735, 790, 1220), 20: (810, 735, 910, 1220),
              21: (930, 735, 1030, 1220), 22: (1050, 735, 1150, 1220),
              29: (1385, 735, 1480, 1220), 30: (1505, 735, 1600, 1220)}
for q, reg in sa_regions.items():
    add(f'short_{q}', 'short_answer', reg, 10, 3, sa(q))

# 수험번호: 8 cols, rows = digit 0..9 (sparse)
add('exam_number', 'digit_columns', (145, 560, 415, 1045), 10, 8,
    lambda ri, ci: {'col': ci + 1, 'digit': ri}, {'digits': 8})

# 문형 / 결시자
def single(name, region, label):
    pts = [b for b in B if in_region(b, *region)]
    if len(pts) != 1: print(f'WARN {name}: {len(pts)} candidates')
    x, y = pts[0][0], pts[0][1]
    fields.append({'name': name, 'kind': 'single', 'bubbles': [{**label, 'x': round(x / W, 5), 'y': round(y / H, 5)}]})
single('form_odd',  (500, 590, 535, 625), {'value': 'odd'})
single('form_even', (500, 665, 535, 700), {'value': 'even'})
single('absent',    (470, 235, 505, 270), {'value': 'absent'})

# timing marks (black blobs) -> top row / bottom row / left / right
M = np.load('marks.npy')
def marks_in(x0, y0, x1, y1):
    out = []
    for x, y, w, h in M:
        cx, cy = x + w/2, y + h/2
        if x0*S <= cx <= x1*S and y0*S <= cy <= y1*S:
            out.append({'x': round(cx / W, 5), 'y': round(cy / H, 5), 'w': round(w / W, 5), 'h': round(h / H, 5)})
    return sorted(out, key=lambda m: (m['y'], m['x']))
allm = marks_in(0, 0, 1754, 1240)
def nearest(px, py): return min(allm, key=lambda m: (m['x']-px)**2 + (m['y']-py)**2)
corners = {'top_left': nearest(0, 0), 'top_right': nearest(1, 0), 'bottom_left': nearest(0, 1), 'bottom_right': nearest(1, 1)}
timing = {'corners': corners, 'top': marks_in(100, 0, 1700, 40), 'bottom': marks_in(100, 1100, 1754, 1240),
          'left': marks_in(40, 600, 70, 730), 'right': marks_in(1690, 600, 1754, 730)}
for k, v in timing.items(): print('timing', k, len(v) if isinstance(v, list) else v)

# bubble radius (normalized) from mean size
rw, rh = B[:, 2].mean() / 2 / W, B[:, 3].mean() / 2 / H
tpl = {
    'template_id': 'ksat-2027-math',
    'description': '2027학년도 대학수학능력시험 수학영역 답안지 (A4 가로)',
    'page': {'width_mm': 297, 'height_mm': 210, 'orientation': 'landscape'},
    'coordinate_system': 'normalized page coordinates (0..1), origin top-left, derived from 300 DPI render of the source PDF',
    'bubble_radius': {'rx': round(rw, 5), 'ry': round(rh, 5)},
    'timing_marks': timing,
    'exam_number_ranges': {'1': [1, 9], '2': [0, 9], '3': [0, 5], '4': [0, 9], '5': [0, 9], '6': [0, 9], '7': [0, 2], '8': [0, 9]},
    'questions': {'multiple_choice': list(range(1, 16)) + list(range(23, 29)), 'short_answer': [16, 17, 18, 19, 20, 21, 22, 29, 30]},
    'fields': fields,
}
json.dump(tpl, open('ksat-2027-math.json', 'w'), ensure_ascii=False, indent=1)
print('total bubbles', sum(len(f['bubbles']) for f in fields))

# verification overlay
vis = img.copy()
colors = {'multiple_choice': (0, 160, 0), 'short_answer': (200, 0, 0), 'digit_columns': (0, 0, 200), 'single': (0, 140, 200)}
for f in fields:
    for b in f['bubbles']:
        cx, cy = int(b['x'] * W), int(b['y'] * H)
        cv2.ellipse(vis, (cx, cy), (int(rw * W), int(rh * H)), 0, 0, 360, colors[f['kind']], 3)
        lab = str(b.get('choice', b.get('digit', b.get('value', ''))))
        cv2.putText(vis, lab, (cx + 14, cy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
for k, v in timing.items():
    for m in (v.values() if isinstance(v, dict) else v):
        cv2.rectangle(vis, (int((m['x'] - m['w']/2) * W), int((m['y'] - m['h']/2) * H)), (int((m['x'] + m['w']/2) * W), int((m['y'] + m['h']/2) * H)), (255, 0, 255), 4)
cv2.imwrite('template_overlay.png', vis)
cv2.imwrite('template_overlay_small.png', cv2.resize(vis, (1754, 1240)))
