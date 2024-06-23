from scipy.spatial import distance, Delaunay
import cv2
import sys
import os
import csv
import math
import numpy as np
from PIL import Image, ImageDraw

from bilinear import BilinearMap

def equal_edge(e1, e2):
	return e1[0] == e2[0] and e1[1] == e2[1] or e1[0] == e2[1] and e1[1] == e2[0]

def angle_between(p1, p2):
	(x1, y1) = p1
	(x2, y2) = p2
	(x, y) = (x1-x2, y1-y2)
	a = math.fabs(math.atan2(y, x))
	return a if a < math.pi / 2 else math.pi - a

def most_diagonal_edge(t):
	(p1, p2, p3) = t
	edges = [(p1, p2), (p2, p3), (p3, p1)]
	return min(edges, key=lambda e: math.fabs(angle_between(e[0], e[1]) - math.pi / 4))

def longest_edge(t):
	(p1, p2, p3) = t
	edges = [(p1, p2), (p2, p3), (p3, p1)]
	return min(edges, key=lambda e: distance.euclidean(e[0], e[1]))

def edge_triangle_index(edge, triangles):
	points = set(edge)
	for i, t in enumerate(triangles):
		points2 = set(t)
		if points.issubset(points2):
			return i
	return -1

def merge_triangle_pairs(edge, triangle_pair1, triangle_pair2):
	points1 = []
	points2 = []
	for i in range(3):
		p = triangle_pair1[0][i]
		if p != edge[0] and p != edge[1]:
			points1.append(p)
			points2.append(triangle_pair1[1][i])
			break
	for i in range(3):
		p = triangle_pair1[0][i]
		if p == edge[0]:
			points1.append(p)
			points2.append(triangle_pair1[1][i])
			break
	for i in range(3):
		p = triangle_pair2[0][i]
		if p != edge[0] and p != edge[1]:
			points1.append(p)
			points2.append(triangle_pair2[1][i])
			break
	for i in range(3):
		p = triangle_pair1[0][i]
		if p == edge[1]:
			points1.append(p)
			points2.append(triangle_pair1[1][i])
			break
	return (points1, points2)

def triangle_area(t):
	# Heron's formula
	(p1, p2, p3) = t
	a = distance.euclidean(p1, p2)
	b = distance.euclidean(p2, p3)
	c = distance.euclidean(p3, p1)
	s = (a+b+c) / 2
	return np.sqrt(s * (s-a) * (s-b) * (s-c))

def perp_dot_product(p1, p2):
	(x1,y1) = p1
	(x2,y2) = p2
	return x1*y2 - x2*y1

def triangle_acute(t):
	(p1, p2, p3) = t
	v1 = np.subtract(p1, p2)
	v2 = np.subtract(p2, p3)
	v3 = np.subtract(p3, p1)
	p1 = np.dot(v1, v2)
	p2 = np.dot(v2, v3)
	p3 = np.dot(v3, v1)
	return p1 > 0 and p2 > 0 and p3 > 0

def quad_convex(q):
	(p1, p2, p3, p4) = q
	v1 = np.subtract(p1, p2)
	v2 = np.subtract(p2, p3)
	v3 = np.subtract(p3, p4)
	v4 = np.subtract(p4, p1)
	p1 = perp_dot_product(v1, v2)
	p2 = perp_dot_product(v2, v3)
	p3 = perp_dot_product(v3, v4)
	p4 = perp_dot_product(v4, v1)
	return p1 > 0 and p2 > 0 and p3 > 0 and p4 > 0 or \
			p1 < 0 and p2 < 0 and p3 < 0 and p4 < 0

def moved_point(p, x, y):
	return (p[0] + x, p[1] + y)

def moved_polygon(t, x, y):
	return tuple([moved_point(p, x, y) for p in t])

def triangles_to_affine(triangles1, triangles2):
	tr = cv2.getAffineTransform(np.float32(triangles1), np.float32(triangles2))
	return [tr[0][0], tr[0][1], tr[0][2], tr[1][0], tr[1][1], tr[1][2]]

def apply_affine(x, y, af):
	return af[0] * x + af[1] * y + af[2], af[3] * x + af[4] * y + af[5]

def quads_to_transform(t1, t2):
	inputs = np.float32(t1)
	outputs = np.float32(t2)
	return cv2.getPerspectiveTransform(inputs, outputs)

def quad_distort(source, transform, w, h):
	source_cv = cv2.cvtColor(np.array(source), cv2.COLOR_RGB2BGR)
	target_cv = cv2.warpPerspective(source_cv, transform, (w, h))
	return Image.fromarray(cv2.cvtColor(target_cv, cv2.COLOR_BGR2RGB))

def bilinear_distort(source, transform, w, h):
	source_cv = cv2.cvtColor(np.array(source), cv2.COLOR_RGB2BGR)
	grid = get_grid(w, h)
	grid_warped = transform.map_grid(grid)
	target_cv = cv2.remap(source_cv, grid_warped[:, :, 0], grid_warped[:, :, 1], cv2.INTER_CUBIC)
	target = Image.fromarray(cv2.cvtColor(target_cv, cv2.COLOR_BGR2RGB))
	return target

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

def do_delaunay(source_points):
	triangles = []
	for indices in Delaunay(source_points).simplices:
		p1 = source_points[indices[0]]
		p2 = source_points[indices[1]]
		p3 = source_points[indices[2]]
		triangles.append((p1, p2, p3))
	return triangles

def point_pairs_to_triangle_pairs(point_pairs):
	source_points = [(x1, y1) for ((x1, y1), _) in point_pairs]
	source_to_target = {p1: p2 for (p1, p2) in point_pairs}
	triangles = do_delaunay(source_points)
	return [((p1, p2, p3), (source_to_target[p1], source_to_target[p2], source_to_target[p3])) \
		for (p1, p2, p3) in triangles]

def split_point_pairs(point_pairs):
	source_points = [[x, y] for ((x, y), _) in point_pairs]
	dest_points = [[x, y] for (_, (x, y)) in point_pairs]
	source_points = np.int32(source_points).reshape(1, -1, 2)
	dest_points = np.int32(dest_points).reshape(1, -1, 2)
	matches = [cv2.DMatch(i, i, 0) for i in range(len(point_pairs))]
	return source_points, dest_points, matches

def normalize_polygon(t):
	xs = [x for (x,_) in t]
	ys = [y for (_,y) in t]
	x_min = min(xs)
	y_min = min(ys)
	x_max = max(xs)
	y_max = max(ys)
	return moved_polygon(t, -x_min, -y_min), x_min, y_min, x_max-x_min+1, y_max-y_min+1

def polygon_mask(t, w, h):
	mask = Image.new('L', (w,h), 0)
	draw = ImageDraw.Draw(mask)
	draw.polygon(list(t), fill=255, outline=None)
	return mask

def merge_triangles(triangle_pairs):
	pairs = []
	while len(triangle_pairs) > 0:
		triangle_pair = triangle_pairs.pop()
		edge = most_diagonal_edge(triangle_pair[0])
		i = edge_triangle_index(edge, [t1 for (t1, t2) in triangle_pairs])
		if i < 0:
			pairs.append(triangle_pair)
		else:
			triangle_pair2 = triangle_pairs.pop(i)
			merged_quad_pair = merge_triangle_pairs(edge, triangle_pair, triangle_pair2)
			if quad_convex(merged_quad_pair[0]) and quad_convex(merged_quad_pair[1]):
				pairs.append(merged_quad_pair)
			else:
				pairs.append(triangle_pair)
				pairs.append(triangle_pair2)
	return pairs

def distort_image(source, pairs, w, h, bilinear):
	target = Image.new(mode='RGB', size=(w,h), color='black')
	for (t1, t2) in pairs:
		t1_norm, x1, y1, w1, h1 = normalize_polygon(t1)
		t2_norm, x2, y2, w2, h2 = normalize_polygon(t2)
		w3 = max(w1, w2)
		h3 = max(h1, h2)
		if len(t1_norm) == 3:
			af = triangles_to_affine(t2_norm, t1_norm)
			sub_source = source.crop((x1, y1, x1+w3, y1+h3))
			sub_target = sub_source.transform(sub_source.size, Image.AFFINE, af, resample=Image.BICUBIC)
			mask_target = polygon_mask(t2_norm, w3, h3)
			target.paste(sub_target, (x2, y2), mask_target)
		elif len(t1_norm) == 4:
			sub_source = source.crop((x1, y1, x1+w3, y1+h3))
			if bilinear:
				transform = BilinearMap(t2_norm, t1_norm)
				sub_target = bilinear_distort(sub_source, transform, w3, h3)
			else:
				transform = quads_to_transform(t1_norm, t2_norm)
				sub_target = quad_distort(sub_source, transform, w3, h3)
			mask_target = polygon_mask(t2_norm, w3, h3)
			target.paste(sub_target, (x2, y2), mask_target)
	return target

def distort_point(x, y, triangle_pairs):
	for (t1, t2) in triangle_pairs:
		if in_triangle(x, y, t1):
			t1_norm, x1, y1, w1, h1 = normalize_polygon(t1)
			t2_norm, x2, y2, w2, h2 = normalize_polygon(t2)
			af = triangles_to_affine(t1_norm, t2_norm)
			(x3, y3) = apply_affine(x-x1, y-y1, af)
			return (int(x3 + x2), int(y3 + y2))
	return None

def undistort_point(x, y, triangle_pairs):
	for (t1, t2) in triangle_pairs:
		if in_triangle(x, y, t2):
			t1_norm, x1, y1, w1, h1 = normalize_polygon(t1)
			t2_norm, x2, y2, w2, h2 = normalize_polygon(t2)
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

def get_grid(w, h):
	xs = np.stack([np.arange(0, w) for _ in range(h)]).astype(np.float32)
	ys = np.stack([np.arange(0, h) for _ in range(w)]).astype(np.float32).T
	return np.concatenate([xs[..., np.newaxis], ys[..., np.newaxis]], 2)

def warp_image(source, pts_src, pts_dst, matches, w, h):
	w_source, h_source = source.size
	w_max = max(w, w_source)
	h_max = max(h, h_source)
	bottom = h_max - h_source
	right = w_max - w_source
	source_cv = cv2.cvtColor(np.array(source), cv2.COLOR_RGB2BGR)
	source_cv = cv2.copyMakeBorder(source_cv, 0, bottom, 0, right, \
			cv2.BORDER_CONSTANT, value=(255,255,255))
	grid = get_grid(w, h)
	tps = cv2.createThinPlateSplineShapeTransformer()
	tps.estimateTransformation(pts_src, pts_dst, matches)
	grid_warped = tps.applyTransformation(grid.reshape(1, -1, 2))[1].reshape(h, w, 2)
	target_cv = cv2.remap(source_cv, grid_warped[:, :, 0], grid_warped[:, :, 1], cv2.INTER_LINEAR)
	target = Image.fromarray(cv2.cvtColor(target_cv, cv2.COLOR_BGR2RGB))
	target = target.crop((0, 0, w, h))
	return target

def unwarp_point(x, y, pts_dst, pts_src, matches):
	tps = cv2.createThinPlateSplineShapeTransformer()
	tps.estimateTransformation(pts_src, pts_dst, matches)
	in_p = np.array([(x,y)], np.float32).reshape((-1,1,2))
	out_p = tps.applyTransformation(in_p)
	return round(out_p[1][0][0][0]), round(out_p[1][0][0][1])

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
