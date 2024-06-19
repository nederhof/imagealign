import numpy as np
import cv2
import sys
from PIL import Image

MIN_MATCH_COUNT = 10
MAX_CV_SIZE = 2000
INNER_MARGIN = 5

def pil_to_cv(im_pil):
	im_cv = cv2.cvtColor(np.array(im_pil), cv2.COLOR_RGB2GRAY)
	h, w = im_cv.shape
	scale = min(MAX_CV_SIZE / h, MAX_CV_SIZE / w, 1)
	return scale, cv2.resize(im_cv, (0,0), fx=scale, fy=scale)

def scale_points(scale, pts_scaled):
	pts = [(x / scale, y / scale) for (x,y) in pts_scaled]
	return np.float32(pts).reshape(-1,1,2)

def get_flann():
	FLANN_INDEX_KDTREE = 1
	index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
	search_params = dict(checks = 50)
	return cv2.FlannBasedMatcher(index_params, search_params)

def get_sift_matches(im1, im2):
	sift = cv2.SIFT_create()
	kp1, ds1 = sift.detectAndCompute(im1, None)
	kp2, ds2 = sift.detectAndCompute(im2, None)
	flann = get_flann()
	matches = flann.knnMatch(ds1, ds2, k=2)
	for f in range(3, 8):
		f = f / 10
		good = [m for (m,n) in matches if m.distance < f * n.distance]
		if len(good) >= MIN_MATCH_COUNT:
			return kp1, kp2, good
	return kp1, kp2, None

def get_homography(im1_pil, im2_pil):
	scale1, im1_cv = pil_to_cv(im1_pil)
	scale2, im2_cv = pil_to_cv(im2_pil)
	kp1, kp2, good = get_sift_matches(im1_cv, im2_cv)
	if good is None:
		return None
	pts1 = scale_points(scale1, [kp1[m.queryIdx].pt for m in good])
	pts2 = scale_points(scale2, [kp2[m.trainIdx].pt for m in good])
	hom, _ = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
	return hom

def apply_hom(hom, source):
	p = np.float32([[source[0], source[1]]]).reshape(-1,1,2)
	target = cv2.perspectiveTransform(p, hom)
	return round(target[0][0][0]), round(target[0][0][1])

def in_image(p, w1, h1):
	(x,y) = p
	return 0 <= x and x < w1 and 0 <= y and y < h1

def add_point(points, p, hom, inv, w1, h1, w2, h2):
	q = apply_hom(hom, p)
	if q[0] < 0:
		q = (INNER_MARGIN, q[1])
		p = apply_hom(inv, q)
	if q[0] >= w2:
		q = (w2-INNER_MARGIN-1, q[1])
		p = apply_hom(inv, q)
	if q[1] < 0:
		q = (q[0], INNER_MARGIN)
		p = apply_hom(inv, q)
	if q[1] >= h2:
		q = (q[0], h2-INNER_MARGIN-1)
		p = apply_hom(inv, q)

	if p[0] < 0:
		p = (INNER_MARGIN, p[1])
		q = apply_hom(hom, p)
	if p[0] >= w1:
		p = (w1-INNER_MARGIN-1, p[1])
		q = apply_hom(hom, p)
	if p[1] < 0:
		p = (p[0], INNER_MARGIN)
		q = apply_hom(hom, p)
	if p[1] >= h1:
		p = (p[0], h1-INNER_MARGIN-1)
		q = apply_hom(hom, p)

	if not in_image(p, w1, h1) or not in_image(q, w2, h2):
		return
	points.append((p, q))

def get_point_pairs(im1, im2):
	hom = get_homography(im1, im2)
	inv = np.linalg.inv(hom)
	if hom is None:
		return None
	w1, h1 = im1.size
	w2, h2 = im2.size
	p1 = (INNER_MARGIN, INNER_MARGIN)
	p2 = (INNER_MARGIN, h1-INNER_MARGIN-1)
	p3 = (w1-INNER_MARGIN-1, INNER_MARGIN)
	p4 = (w1-INNER_MARGIN-1, h1-INNER_MARGIN-1)
	q1 = (INNER_MARGIN, INNER_MARGIN)
	q2 = (INNER_MARGIN, h2-INNER_MARGIN-1)
	q3 = (w2-INNER_MARGIN-1, INNER_MARGIN)
	q4 = (w2-INNER_MARGIN-1, h2-INNER_MARGIN-1)
	points = []
	add_point(points, p1, hom, inv, w1, h1, w2, h2)
	add_point(points, p2, hom, inv, w1, h1, w2, h2)
	add_point(points, p3, hom, inv, w1, h1, w2, h2)
	add_point(points, p4, hom, inv, w1, h1, w2, h2)
	return points

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print('Required are two images')
	in_file1 = sys.argv[1]
	in_file2 = sys.argv[2]
	im1 = Image.open(in_file1).convert('RGB')
	im2 = Image.open(in_file2).convert('RGB')
	point_pairs = get_point_pairs(im1, im2)
	print(point_pairs)
