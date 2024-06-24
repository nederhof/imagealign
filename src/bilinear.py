import numpy as np
import math

"""
Consider quadrilateral with corner points (x0,y0), (x1,y1), (x2,y2), (x3,y3).
Express point (x,y) within quadrilateral in terms of u and v, both between 0 and 1:
x = (1-u)(1-v) x0 + u(1-v) x1 + uv x2 + (1-u)v x3
y = (1-u)(1-v) y0 + u(1-v) y1 + uv y2 + (1-u)v y3
So:
x = [x0-x1+x2-x3] uv + [-x0+x1] u + [-x0+x3] v + [x0]
  = Ax uv + Bx u + Cx v + Dx
y = [y0-y1+y2-y3] uv + [-y0+y1] u + [-y0+y3] v + [y0]
  = Ay uv + By u + Cy v + Dy
where
Ax = x0-x1+x2-x3
Bx = -x0+x1
Cx = -x0+x3
Dx = x0
Ay = y0-y1+y2-y3
By = -y0+y1
Cy = -y0+y3
Dy = y0
Rewrite expression for x above:
u = (x - Cx v - Dx) / (Ax v + Bx)
Substitute in expression for y above:
y = (Ay v + By) (x - Cx v - Dx) / (Ax v + Bx) + Cy v + Dy
Hence:
0 = (Ay v + By) (x - Cx v - Dx) + (Cy v + Dy - y) (Ax v + Bx)
  = [Ax Cy - Ay Cx] v^2 + [Ay x - Ax y + Ax Dy - Ay Dx + Bx Cy - By Cx] v + [By x - Bx y + Bx Dy - By Dx]
  = E v^2 + F v + G
where
E = Ax Cy - Ay Cx
F = Ay x - Ax y + F1
F1 = Ax Dy - Ay Dx + Bx Cy - By Cx
G = By x - Bx y + G1
G1 = Bx Dy - By Dx
Quadratic formula:
v = [-F +- sqrt(F^2 - 4 E G)] / (2 E)
"""

class BilinearMap:
	def __init__(self, quad1, quad2):
		if not clockwise(quad1):
			quad1 = reverse(quad1)
			quad2 = reverse(quad2)
		self.quad1 = quad1
		self.quad2 = quad2
		((x0,y0),(x1,y1),(x2,y2),(x3,y3)) = quad1
		self.Ax = x0-x1+x2-x3
		self.Bx = -x0+x1
		self.Cx = -x0+x3
		self.Dx = x0
		self.Ay = y0-y1+y2-y3
		self.By = -y0+y1
		self.Cy = -y0+y3
		self.Dy = y0
		self.Ev = self.Ax * self.Cy - self.Ay * self.Cx
		self.F1v = self.Ax * self.Dy - self.Ay * self.Dx + self.Bx * self.Cy - self.By * self.Cx
		self.G1v = self.Bx * self.Dy - self.By * self.Dx
		self.Eu = self.Ay * self.Bx - self.Ax * self.By
		self.F1u = self.Ay * self.Dx - self.Ax * self.Dy + self.Cy * self.Bx - self.Cx * self.By
		self.G1u = self.Cy * self.Dx - self.Cx * self.Dy

	def coefficients(self, x, y):
		Fv = self.Ay * x - self.Ax * y + self.F1v
		Gv = self.By * x - self.Bx * y + self.G1v
		if self.Ev == 0:
			if Fv == 0:
				v = 0
			else:
				v = -Gv / Fv
		else:
			sqrt_arg = max(Fv * Fv - 4 * self.Ev * Gv, 0)
			v = (-Fv + math.sqrt(sqrt_arg)) / (2 * self.Ev)
		if self.Ax * v + self.Bx == 0:
			u = (y - self.Cy * v - self.Dy) / (self.Ay * v + self.By)
		else:
			u = (x - self.Cx * v - self.Dx) / (self.Ax * v + self.Bx)
		return u, v

	def coefficients_grid(self, grid):
		xs = grid[:,:,0]
		ys = grid[:,:,1]
		Fv_vector = \
			np.add( \
				np.subtract( \
					np.multiply(self.Ay, xs, dtype=np.float32), \
					np.multiply(self.Ax, ys, dtype=np.float32), dtype=np.float32), \
				self.F1v, dtype=np.float32)
		Gv_vector = \
			np.add( \
				np.subtract( \
					np.multiply(self.By, xs, dtype=np.float32), \
					np.multiply(self.Bx, ys, dtype=np.float32), dtype=np.float32), \
				self.G1v, dtype=np.float32)
		if self.Ev == 0:
			vs = np.full(xs.shape, 0.0, dtype=np.float32)
			np.divide(-Gv_vector, Fv_vector, where=Fv_vector!=0, out=vs)
		else:
			zeros = np.full((xs.shape), 0.0, dtype=np.float32)
			sqrt_arg_vector = \
				np.maximum( \
					np.subtract( \
						np.multiply(Fv_vector, Fv_vector, dtype=np.float32), \
						np.multiply(4, np.multiply(self.Ev, Gv_vector, dtype=np.float32), 
							dtype=np.float32), dtype=np.float32), \
					zeros, dtype=np.float32)
			vs = np.divide( \
					np.subtract(np.sqrt(sqrt_arg_vector, dtype=np.float32), Fv_vector, dtype=np.float32), \
					np.multiply(2, self.Ev, dtype=np.float32), dtype=np.float32)
		num1 = np.subtract( \
				np.subtract(ys, np.multiply(self.Cy, vs, dtype=np.float32), dtype=np.float32), \
				self.Dy, dtype=np.float32)
		denom1 = np.add(np.multiply(self.Ay, vs, dtype=np.float32), self.By, dtype=np.float32)
		num2 = np.subtract( \
				np.subtract(xs, np.multiply(self.Cx, vs, dtype=np.float32), dtype=np.float32), \
				self.Dx, dtype=np.float32)
		denom2 = np.add(np.multiply(self.Ax, vs, dtype=np.float32), self.Bx, dtype=np.float32)
		us = np.full((xs.shape), 0.0, dtype=np.float32)
		np.divide(num1, denom1, where=denom1!=0, out=us)
		np.divide(num2, denom2, where=denom2!=0, out=us)
		return us, vs

	def map(self, x, y):
		((x0,y0),(x1,y1),(x2,y2),(x3,y3)) = self.quad2
		u, v = self.coefficients(x, y)
		x_dest = (1-u) * (1-v) * x0 + u * (1-v) * x1 + u * v * x2 + (1-u) * v * x3
		y_dest = (1-u) * (1-v) * y0 + u * (1-v) * y1 + u * v * y2 + (1-u) * v * y3
		return x_dest, y_dest

	def map_grid_fast(self, grid):
		((x0,y0),(x1,y1),(x2,y2),(x3,y3)) = self.quad2
		us, vs = self.coefficients_grid(grid)
		us_compl = np.subtract(1, us, dtype=np.float32)
		vs_compl = np.subtract(1, vs, dtype=np.float32)
		coef0 = np.multiply(us_compl, vs_compl, dtype=np.float32)
		coef1 = np.multiply(us, vs_compl, dtype=np.float32)
		coef2 = np.multiply(us, vs, dtype=np.float32)
		coef3 = np.multiply(us_compl, vs, dtype=np.float32)
		x_dest0 = np.multiply(coef0, x0, dtype=np.float32)
		x_dest1 = np.multiply(coef1, x1, dtype=np.float32)
		x_dest2 = np.multiply(coef2, x2, dtype=np.float32)
		x_dest3 = np.multiply(coef3, x3, dtype=np.float32)
		y_dest0 = np.multiply(coef0, y0, dtype=np.float32)
		y_dest1 = np.multiply(coef1, y1, dtype=np.float32)
		y_dest2 = np.multiply(coef2, y2, dtype=np.float32)
		y_dest3 = np.multiply(coef3, y3, dtype=np.float32)
		x_dest = np.add(np.add(np.add(x_dest0, x_dest1, dtype=np.float32), x_dest2, dtype=np.float32), \
				x_dest3, dtype=np.float32)
		y_dest = np.add(np.add(np.add(y_dest0, y_dest1, dtype=np.float32), y_dest2, dtype=np.float32), \
				y_dest3, dtype=np.float32)
		return np.dstack((x_dest, y_dest))

	def map_grid_slow(self, grid):
		h, w, _ = grid.shape
		grid_dst = np.empty([h, w, 2], dtype=np.float32)
		grid_dst2 = np.empty([h, w, 2], dtype=np.float32)
		for y in range(h):
			for x in range(w):
				x_src, y_src = grid[y][x]
				x_dst, y_dst = self.map(x_src, y_src)
				grid_dst[y][x] = np.array([x_dst, y_dst], dtype=np.float32)
		return grid_dst

def area(quad):
	# shoelace formula
	((x0,y0),(x1,y1),(x2,y2),(x3,y3)) = quad
	return 0.5 * (x0*y1 - x1*y0 + x1*y2 - x2*y1 + x2*y3 - x3*y2 + x3*y0 - x0*y3)

def clockwise(quad):
	return area(quad) > 0

def reverse(quad):
	(p0,p1,p2,p3) = quad
	return (p0,p3,p2,p1)

if __name__ == '__main__':
	quad1 = ((0,0), (6,0), (7,4), (2,6))
	quad2 = ((2,2), (10,4), (8,10), (0,12))
	bil = BilinearMap(quad1, quad2)
	for x in range(10):
		for y in range(10):
			print(x, y, bil.map(x, y))
