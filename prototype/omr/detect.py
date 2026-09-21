import cv2, numpy as np, json
img = cv2.imread('omr300.png')
H, W = img.shape[:2]
b, g, r = cv2.split(img)

# ---- timing marks: black (all channels dark) blobs near edges
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blk = (gray < 90).astype(np.uint8) * 255
blk = cv2.morphologyEx(blk, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
cnts, _ = cv2.findContours(blk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
marks = []
for c in cnts:
    x, y, w, h = cv2.boundingRect(c)
    if w * h < 150 or w > 200 or h > 200:
        continue
    fill = cv2.contourArea(c) / (w * h)
    if fill < 0.6:
        continue
    marks.append((x, y, w, h))
print('black blobs', len(marks))

# ---- bubbles: pink ink -> low G channel. invert G, threshold
ginv = 255 - g
th = cv2.threshold(ginv, 60, 255, cv2.THRESH_BINARY)[1]
th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
cnts, hier = cv2.findContours(th, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
bubbles = []
for i, c in enumerate(cnts):
    x, y, w, h = cv2.boundingRect(c)
    if not (14 <= w <= 40 and 22 <= h <= 52):
        continue
    ar = w / h
    if not (0.45 <= ar <= 0.95):
        continue
    # ellipse-ness: contour area vs ellipse area
    a = cv2.contourArea(c)
    ell = np.pi * (w / 2) * (h / 2)
    if a / ell < 0.6:
        continue
    bubbles.append((x + w / 2, y + h / 2, w, h))
print('bubble candidates', len(bubbles))
np.save('bubbles.npy', np.array(bubbles))
np.save('marks.npy', np.array(marks))

vis = img.copy()
for (cx, cy, w, h) in bubbles:
    cv2.ellipse(vis, (int(cx), int(cy)), (int(w / 2), int(h / 2)), 0, 0, 360, (0, 180, 0), 2)
for (x, y, w, h) in marks:
    cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 0, 0), 3)
cv2.imwrite('vis.png', cv2.resize(vis, (1754, 1240)))
