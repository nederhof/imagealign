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
		(x0,y0) = quad1[0]
		(x1,y1) = quad1[1]
		(x2,y2) = quad1[2]
		(x3,y3) = quad1[3]
		self.Ax = x0-x1+x2-x3
		self.Bx = -x0+x1
		self.Cx = -x0+x3
		self.Dx = x0
		self.Ay = y0-y1+y2-y3
		self.By = -y0+y1
		self.Cy = -y0+y3
		self.Dy = y0
		self.E = self.Ax * self.Cy - self.Ay * self.Cx
		self.F1 = self.Ax * self.Dy - self.Ay * self.Dx + self.Bx * self.Cy - self.By * self.Cx
		self.G1 = self.Bx * self.Dy - self.By * self.Dx
		self.quad2 = quad2

	def coefficients(self, x, y):
		F = self.Ay * x - self.Ax * y + self.F1
		G = self.By * x - self.Bx * y + self.G1
		if self.E == 0:
			v = -G / F
		else:
			sqrt_arg = F * F - 4 * self.E * G
			if sqrt_arg <= 0:
				v = -F / (2 * self.E)
			else:
				v = (-F + math.sqrt(sqrt_arg)) / (2 * self.E)
				if v < 0 or 1 < v:
					v = (-F - math.sqrt(sqrt_arg)) / (2 * self.E)
		if self.Ax * v + self.Bx == 0:
			u = (y - self.Cy * v - self.Dy) / (self.Ay * v + self.By)
		else:
			u = (x - self.Cx * v - self.Dx) / (self.Ax * v + self.Bx)
		return u, v

	def map(self, x, y):
		u, v = self.coefficients(x, y)
		print("UV", u, v)
		(x0,y0) = self.quad2[0]
		(x1,y1) = self.quad2[1]
		(x2,y2) = self.quad2[2]
		(x3,y3) = self.quad2[3]
		x = (1-u) * (1-v) * x0 + u * (1-v) * x1 + u * v * x2 + (1-u) * v * x3
		y = (1-u) * (1-v) * y0 + u * (1-v) * y1 + u * v * y2 + (1-u) * v * y3
		return x, y

	def map_grid(self, grid):
		h, w, _ = grid.shape
		grid_dst = np.empty([h, w, 2], dtype=np.float32)
		for y in range(h):
			for x in range(w):
				x_src, y_src = grid[y][x]
				x_dst, y_dst = self.map(x_src, y_src)
				grid_dst[y,x] = np.array([x_dst, y_dst], dtype=np.float32)
		return grid_dst

if __name__ == '__main__':
	quad1 = [(0,0), (6,0), (7,4), (2,6)]
	# quad1 = [(1,1), (5,2), (4,5), (0,6)]
	quad2 = [(2,2), (10,4), (8,10), (0,12)]
	bil = BilinearMap(quad1, quad2)
	for x in range(10):
		for y in range(10):
			print(x, y, bil.map(x, y))
