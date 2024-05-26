import cv2
import sys
import os
import csv
import numpy as np
from PIL import Image, ImageDraw

def moved_point(p, x, y):
	return (p[0] + x, p[1] + y)

def moved_triangle(t, x, y):
	return (moved_point(t[0], x, y), moved_point(t[1], x, y), moved_point(t[2], x, y))

def triangles_to_affine(triangles1, triangles2):
	tr = cv2.getAffineTransform(np.float32(triangles1), np.float32(triangles2))
	return [tr[0][0], tr[0][1], tr[0][2], tr[1][0], tr[1][1], tr[1][2]]

def apply_affine(x, y, af):
	return af[0] * x + af[1] * y + af[2], af[3] * x + af[4] * y + af[5]

def in_triangle(x, y, t):
	((x1,y1), (x2,y2), (x3,y3)) = t
	v1 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
	v2 = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
	v3 = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)
	if x1 == x2 and x == x1:
		return (y1 <= y and y <= y2 or y2 <= y and y <= y1)
	elif x2 == x3 and x == x2:
		return (y2 <= y and y <= y3 or y3 <= y and y <= y2)
	elif x3 == x1 and x == x3:
		return (y3 <= y and y <= y1 or y1 <= y and y <= y3)
	elif v1 == 0 and (x1 <= x and x <= x2 or x2 <= x and x <= x1):
		return True
	elif v2 == 0 and (x2 <= x and x <= x3 or x3 <= x and x <= x2):
		return True
	elif v3 == 0 and (x3 <= x and x <= x1 or x1 <= x and x <= x3):
		return True
	else:
		return (v1 * v2 > 0) and (v2 * v3 > 0)

def point_pairs_to_triangle_pairs(point_pairs):
	source_points = [(x1, y1) for ((x1, y1), _) in point_pairs]
	source_to_target = {p1: p2 for (p1, p2) in point_pairs}
	x_min = min([x for (x, _) in source_points])
	y_min = min([y for (_, y) in source_points])
	x_max = max([x for (x, _) in source_points])
	y_max = max([y for (_, y) in source_points])
	w = x_max - x_min + 1
	h = y_max - y_min + 1
	subdiv = cv2.Subdiv2D((x_min, y_min, w, h))
	subdiv.insert(source_points)
	triangles = [((int(x1), int(y1)), (int(x2), int(y2)), (int(x3), int(y3))) \
		for (x1, y1, x2, y2, x3, y3) in subdiv.getTriangleList()]
	return [((p1, p2, p3), (source_to_target[p1], source_to_target[p2], source_to_target[p3])) \
		for (p1, p2, p3) in triangles]

def normalize_triangle(t):
	xs = [x for (x,_) in t]
	ys = [y for (_,y) in t]
	x_min = min(xs)
	y_min = min(ys)
	x_max = max(xs)
	y_max = max(ys)
	return moved_triangle(t, -x_min, -y_min), x_min, y_min, x_max-x_min+1, y_max-y_min+1

def triangle_mask(t, w, h):
	mask = Image.new('L', (w,h), 0)
	draw = ImageDraw.Draw(mask)
	draw.polygon(list(t), fill=255, outline=None)
	return mask

def distort_image(source, triangle_pairs, w, h):
	target = Image.new(mode='RGB', size=(w,h), color='black')
	for (t1, t2) in triangle_pairs:
		t1_norm, x1, y1, w1, h1 = normalize_triangle(t1)
		t2_norm, x2, y2, w2, h2 = normalize_triangle(t2)
		w3 = max(w1, w2)
		h3 = max(h1, h2)
		af = triangles_to_affine(t2_norm, t1_norm)
		sub_source = source.crop((x1, y1, x1+w3, y1+h3))
		sub_target = sub_source.transform(sub_source.size, Image.AFFINE, af, resample=Image.BICUBIC)
		mask_target = triangle_mask(t2_norm, w3, h3)
		target.paste(sub_target, (x2, y2), mask_target)
	return target

def distort_point(x, y, triangle_pairs):
	for (t1, t2) in triangle_pairs:
		if in_triangle(x, y, t1):
			t1_norm, x1, y1, w1, h1 = normalize_triangle(t1)
			t2_norm, x2, y2, w2, h2 = normalize_triangle(t2)
			af = triangles_to_affine(t1_norm, t2_norm)
			(x3, y3) = apply_affine(x-x1, y-y1, af)
			return (int(x3 + x2), int(y3 + y2))
	return None

def undistort_point(x, y, triangle_pairs):
	for (t1, t2) in triangle_pairs:
		if in_triangle(x, y, t2):
			t1_norm, x1, y1, w1, h1 = normalize_triangle(t1)
			t2_norm, x2, y2, w2, h2 = normalize_triangle(t2)
			af = triangles_to_affine(t2_norm, t1_norm)
			(x3, y3) = apply_affine(x-x2, y-y2, af)
			return (int(x3 + x1), int(y3 + y1))
	return None

def distort_points(in_points, triangle_pairs):
	out_points = []
	for point in in_points:
		distorted = distort_point(point[0], point[1], triangle_pairs)
		if distorted is None:
			print('Ignored', point)
		else:
			out_points.append(distorted)
	return out_points

def read_point_pairs(path):
	if not os.path.isfile(path):
		return []
	with open(path) as handler:
		reader = csv.reader(handler, delimiter=' ')
		rows = list(reader)
	return [((int(x1), int(y1)), (int(x2), int(y2))) for x1, y1, x2, y2 in rows]

def write_point_pairs(point_pairs, path):
	with open(path, 'w') as handle:
		writer = csv.writer(handle, delimiter=' ')
		for ((x1, y1), (x2, y2)) in point_pairs:
			writer.writerow([x1, y1, x2, y2])

def read_points(path):
	if not os.path.isfile(path):
		return []
	with open(path) as handler:
		reader = csv.reader(handler, delimiter=' ')
		rows = list(reader)
	return [(int(x), int(y)) for x, y in rows]

def write_points(points, path):
	with open(path, 'w') as handle:
		writer = csv.writer(handle, delimiter=' ')
		for (x, y) in points:
			writer.writerow([x, y])

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print('Required are file with point pairs, and two files with input and output points')
		sys.exit(1) 
	pair_file = sys.argv[1]
	in_file = sys.argv[2]
	out_file = sys.argv[3]
	point_pairs = read_point_pairs(pair_file)
	triangle_pairs = point_pairs_to_triangle_pairs(point_pairs)
	in_points = read_points(in_file)
	out_points = distort_points(in_points, triangle_pairs)
	write_points(out_points, out_file)
