import json, random, cv2, numpy as np
from omr_reader import read_sheet, load_template, CANVAS_W, CANVAS_H

tpl = load_template('ksat-2027-math.json')
base = cv2.imread('omr300.png')
H, W = base.shape[:2]
rx, ry = tpl['bubble_radius']['rx'] * W, tpl['bubble_radius']['ry'] * H
random.seed(7)

# ---- ground truth
truth = {'answers': {}, 'exam_number': '', 'form': 'odd'}
for q in tpl['questions']['multiple_choice']:
    truth['answers'][q] = random.randint(1, 5)
for q in tpl['questions']['short_answer']:
    truth['answers'][q] = random.choice([random.randint(1, 9), random.randint(10, 99), random.randint(100, 999)])
truth['answers'][22] = None  # leave one blank on purpose
rng = tpl['exam_number_ranges']
truth['exam_number'] = ''.join(str(random.randint(*rng[str(i)])) for i in range(1, 9))

# ---- paint marks (imperfect: slightly offset, not fully filled)
img = base.copy()
def fill(b):
    cx, cy = int(b['x'] * W + random.uniform(-3, 3)), int(b['y'] * H + random.uniform(-3, 3))
    cv2.ellipse(img, (cx, cy), (int(rx * 0.9), int(ry * 0.9)), 0, 0, 360, (20, 20, 20), -1)

for f in tpl['fields']:
    for b in f['bubbles']:
        if f['kind'] == 'multiple_choice' and truth['answers'][b['q']] == b['choice']:
            fill(b)
        elif f['kind'] == 'short_answer':
            v = truth['answers'][b['q']]
            if v is None:
                continue
            d = {'hundreds': v // 100, 'tens': (v // 10) % 10, 'ones': v % 10}[b['place']]
            if b['place'] == 'hundreds' and v < 100:
                continue  # 백의 자리 무마킹
            if b['place'] == 'tens' and v < 10:
                continue  # 한 자리 정답: 일의 자리만
            if d == b['digit']:
                fill(b)
        elif f['kind'] == 'digit_columns' and int(truth['exam_number'][b['col'] - 1]) == b['digit']:
            fill(b)
        elif f['name'] == 'form_odd':
            fill(b)
# a deliberate double mark on Q3
for f in tpl['fields']:
    for b in f['bubbles']:
        if f['kind'] == 'multiple_choice' and b['q'] == 3 and b['choice'] == ((truth['answers'][3] % 5) + 1):
            fill(b)
cv2.imwrite('synthetic_filled.png', img)

# ---- simulate a phone photo: rotate 3°, scale to 0.6, mild perspective, gray background
M = cv2.getRotationMatrix2D((W / 2, H / 2), 3, 0.6)
M[:, 2] += (80, 60)
warped = cv2.warpAffine(img, M, (W, H), borderValue=(120, 120, 120))
pts1 = np.float32([[0, 0], [W, 0], [0, H], [W, H]])
pts2 = np.float32([[40, 30], [W - 10, 60], [20, H - 20], [W - 60, H - 70]])
warped = cv2.warpPerspective(warped, cv2.getPerspectiveTransform(pts1, pts2), (W, H), borderValue=(120, 120, 120))
cv2.imwrite('synthetic_photo.png', warped)

# ---- read back
res, reg = read_sheet(warped, tpl)
cv2.imwrite('registered.png', cv2.resize(reg, (1754, 1240)))
errors = []
for q in range(1, 31):
    got, exp = res['answers'].get(q), truth['answers'][q]
    if q == 3:
        ok = res['flags'][q] == 'multi'
    else:
        ok = got == exp
    if not ok:
        errors.append((q, exp, got, res['flags'][q]))
print('exam_number', truth['exam_number'], '->', res['exam_number'], res['flags']['exam_number'])
print('form', truth['form'], '->', res['form'])
print('Q3 double-mark flag ->', res['flags'][3], res['answers'][3])
print('Q22 blank flag ->', res['flags'][22], res['answers'][22])
print('errors', errors)
print('flags summary', {k: v for k, v in res['flags'].items() if v != 'ok'})
