import csv
import os
import sys
import math
import tkinter as tk
from getopt import getopt, GetoptError
from PIL import Image, ImageTk

from imagedistortion import point_pairs_to_triangle_pairs, distort_image, undistort_point, \
		read_point_pairs, write_point_pairs

DELAY = 1
KEY_ZOOM_STEP = 1.2
MOUSE_ZOOM_STEP = 1.1
MIN_PIXELS_IN_CANVAS = 10
ARROW_STEP = 0.7
DEFAULT_GEOMETRY = '800x800'
MARGIN = 20
TOP_CANVAS = 30
CIRC = 5
POINT_COLOR = 'red'
ARROW_COLOR = 'red'
DRAGGED_COLOR = 'gray'

def complete_point_pairs(point_pairs, image1, image2):
	w1, h1 = image1.size
	w2, h2 = image2.size
	top_left1 = (0, 0)
	top_left2 = (0, 0)
	top_right1 = (w1-1, 0)
	top_right2 = (w2-1, 0)
	bottom_left1 = (0, h1-1)
	bottom_left2 = (0, h2-1)
	bottom_right1 = (w1-1, h1-1)
	bottom_right2 = (w2-1, h2-1)
	points1 = [p1 for (_,p1) in point_pairs]
	points2 = [p2 for (p2,_) in point_pairs]
	completed = point_pairs[:]
	if top_left1 not in points1 and top_left2 not in points2:
		completed.append((top_left2, top_left1))
	if top_right1 not in points1 and top_right2 not in points2:
		completed.append((top_right2, top_right1))
	if bottom_left1 not in points1 and bottom_left2 not in points2:
		completed.append((bottom_left2, bottom_left1))
	if bottom_right1 not in points1 and bottom_right2 not in points2:
		completed.append((bottom_right2, bottom_right1))
	return completed

class AlignImageMenu(tk.Menu):
	def __init__(self, parent, item_set):
		tk.Menu.__init__(self, parent.master)
		for (label, items) in item_set:
			submenu = tk.Menu(self, tearoff=False)
			for (sublabel, command, accelerator, acc_display) in items:
				parent.master.bind(accelerator, (lambda f: lambda event: f())(command))
				submenu.add_command(label=sublabel, command=command, accelerator=acc_display)
			self.add_cascade(label=label, menu=submenu)

class AlignImage(tk.Frame):
	def __init__(self, root):
		self.root = root
		tk.Frame.__init__(self, self.root)
		self.master.title("Image align")
		self.create_menu()
		self.init_layout()

	def create_menu(self):
		items = []
		if sys.platform == 'darwin':
			items.append(('File', 
				[('Save', self.save, '<Meta-s>', 'Command+S'),
					('Exit', self.destroy, '<Meta-w>', 'Command+W')]))
		else:
			items.append(('File', 
				[('Save', self.save, '<Control-s>', 'Ctrl+S'),
					('Exit', self.destroy, '<Alt-Key-F4>', 'Alt+F4')]))
		self.master.protocol('WM_DELETE_WINDOW', self.destroy)
		items.append(('Tools', 
			[('View 1', self.view1, '1', '1'),
				('View 2', self.view2, '2', '2'),
				('View both', self.view_both, '3', '3')]))
		if sys.platform == 'darwin':
			items.append(('View', 
				[('Maximize', self.maximize, '<F11>', 'F11'),
					('Default view', self.default_view, '<F5>', 'F5')]))
		else:
			items.append(('View', 
				[('Maximize', self.maximize, '<Meta-Control-f>', 'Command+Ctrl+F'),
					('Default view', self.default_view, '<Meta-r>', 'Command+R')]))
		self.menu = AlignImageMenu(self, items)
		self.menu_empty = tk.Menu(self.master)

	def menubar_show(self):
		self.master.configure(menu=self.menu)

	def menubar_hide(self):
		self.master.configure(menu=self.menu_empty)

	def init_layout(self):
		self.master.bind('<ButtonPress-1>', lambda event: self.start_drag())
		self.master.bind('<ButtonRelease-1>', lambda event: self.end_drag())
		self.master.bind('<Button-4>', lambda event: self.zoom_mouse(MOUSE_ZOOM_STEP))
		self.master.bind('<Button-5>', lambda event: self.zoom_mouse(1 / MOUSE_ZOOM_STEP))
		self.master.bind('<Configure>', lambda event: self.master.after_idle(self.resize))
		self.master.bind('<Key>', lambda event: self.master.after_idle(self.key, event))
		self.master.bind('<BackSpace>', lambda event: self.master.after_idle(self.unregister_point, event))
		self.master.bind('<Left>', lambda event: self.left())
		self.master.bind('<Right>', lambda event: self.right())
		self.master.bind('<Up>', lambda event: self.up())
		self.master.bind('<Down>', lambda event: self.down())
		self.canvas = tk.Canvas(self.master, bg='gray')
		self.canvas.pack(fill=tk.BOTH, expand=True)
		self.canvas.bind('<Motion>', lambda event: self.motion_canvas())
		self.canvas.bind('<Leave>', lambda event: self.abort_drag())
		self.drag_start = None
		self.mode = 'move'
		self.image1 = None
		self.timer = None
		self.default_view()

	def default_view(self):
		self.master.geometry(DEFAULT_GEOMETRY)
		self.maximize(state=False)

	def maximize(self, state=None):
		if state is not None:
			self.fullscreen = state
		else:
			self.fullscreen = not self.fullscreen
		if self.fullscreen:
			self.menubar_hide()
		else:
			self.menubar_show()
		self.master.wm_attributes('-fullscreen', self.fullscreen)
		self.resize()

	def destroy(self):
		self.quit()

	def set_images(self, image1, image2, point_pairs):
		self.image1 = image1.convert('RGB')
		self.image2 = image2.convert('RGB')
		self.w_image1, self.h_image1 = self.image1.size
		self.w_image2, self.h_image2 = self.image2.size
		self.point_pairs = point_pairs
		self.normalize_point_pairs()
		self.view_mode = 'both'
		self.set_distorted()
		self.scale = 0.000001
		self.center = (0.5, 0.5)
		self.adjust_zoom()

	def normalize_point_pairs(self):
		self.point_pairs = complete_point_pairs(self.point_pairs, self.image1, self.image2)

	def set_distorted(self):
		self.show_wait()
		triangle_pairs = point_pairs_to_triangle_pairs(self.point_pairs)
		self.distorted = distort_image(self.image2, triangle_pairs, self.w_image1, self.h_image1)
		self.normal_cursor()
		self.merged = Image.blend(self.image1, self.distorted, 0.5)
		self.delayed_redraw()

	def view1(self):
		self.view_mode = '1'
		self.delayed_redraw()

	def view2(self):
		self.view_mode = '2'
		self.delayed_redraw()

	def view_both(self):
		self.view_mode = 'both'
		self.delayed_redraw()

	def resize(self):
		self.canvas.update()
		self.x_canvas = -1
		self.y_canvas = -1
		self.w_canvas = self.canvas.winfo_width() - 2 * MARGIN
		self.h_canvas = self.canvas.winfo_height() - 2 * MARGIN
		self.adjust_zoom()

	def delayed_redraw(self):
		if self.timer is not None:
			self.root.after_cancel(self.timer);
		self.timer = self.root.after(DELAY, self.redraw)

	def redraw(self):
		self.timer = None
		if self.image1 is None:
			return
		x_min, y_min, w, h = self.visible_rect()
		x_max = x_min + w
		y_max = y_min + h
		if self.view_mode == '1':
			im = self.image1
		elif self.view_mode == '2':
			im = self.distorted
		else:
			im = self.merged
		cropped = im.crop((x_min, y_min, x_max, y_max))
		resized = cropped.resize((self.w_canvas, self.h_canvas))
		self.im = ImageTk.PhotoImage(resized) # attach to self to avoid garbage collection
		self.canvas.delete('all')
		self.canvas.create_image(MARGIN, MARGIN, anchor=tk.NW, image=self.im)
		self.draw_points()

	def draw_points(self):
		for i, (_, p) in enumerate(self.point_pairs):
			x1, y1 = self.to_canvas(p[0], p[1])
			color = DRAGGED_COLOR if self.mode == 'drag' and i == self.dragged_index \
					else POINT_COLOR
			self.canvas.create_oval(MARGIN+x1-CIRC, MARGIN+y1-CIRC, MARGIN+x1+CIRC, MARGIN+y1+CIRC, \
				outline=color, width=2)
		if self.mode == 'drag':
			(_, (px, py)) = self.point_pairs[self.dragged_index]
			cx, cy = self.to_canvas(px, py)
			arrow = tk.FIRST if self.view_mode == '1' else tk.LAST
			self.canvas.create_line(self.x_canvas+MARGIN, self.y_canvas+MARGIN, 
				cx+MARGIN, cy+MARGIN, fill=ARROW_COLOR, width=2, arrow=arrow)

	def motion_canvas(self):
		if self.image1 is None:
			return
		self.x_canvas = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx() - MARGIN
		self.y_canvas = self.canvas.winfo_pointery() - self.canvas.winfo_rooty() - MARGIN
		if self.fullscreen:
			if self.y_canvas < TOP_CANVAS:
				self.menubar_show()
			else:
				self.menubar_hide()
		if self.drag_start is not None and self.mode == 'move':
			x_diff = (self.x_canvas - self.drag_start[0]) / self.scale / self.w_image1
			y_diff = (self.y_canvas - self.drag_start[1]) / self.scale / self.h_image1
			self.center = (self.center[0] - x_diff, self.center[1] - y_diff)
			self.start_drag()
			self.adjust_pos()
		if self.drag_start is not None and self.mode == 'drag':
			self.delayed_redraw()

	def start_drag(self):
		if self.image1 is None:
			return
		self.drag_start = (self.x_canvas, self.y_canvas)
		if self.view_mode in ['1','2']:
			i, d = self.nearest_point_index(self.x_canvas, self.y_canvas)
			if d < CIRC * 2:
				self.mode = 'drag'
				self.dragged_index = i
				self.delayed_redraw()
				self.show_drag()

	def end_drag(self):
		if self.image1 is None or self.drag_start is None:
			return
		x_from, y_from = self.drag_start
		i, _ = self.nearest_point_index(x_from, y_from)
		if i < 0:
			return
		if self.mode == 'drag':
			if self.view_mode == '1':
				((x2, y2), _) = self.point_pairs[i]
				x, y = self.from_canvas1(self.x_canvas, self.y_canvas)
				if x >= 0 and x < self.w_image1 and y >= 0 and y < self.h_image1:
					self.point_pairs[i] = ((x2, y2), (x, y))
					self.normalize_point_pairs()
					self.set_distorted()
			elif self.view_mode == '2':
				(_, (x2, y2)) = self.point_pairs[i]
				p = self.from_canvas2(self.x_canvas, self.y_canvas)
				if p is not None:
					(x1, y1) = p
					self.point_pairs[i] = ((x1, y1), (x2, y2))
					self.normalize_point_pairs()
					self.set_distorted()
		self.mode = 'move'
		self.drag_start = None
		self.normal_cursor()

	def abort_drag(self):
		self.mode = 'move'
		self.drag_start = None
		self.normal_cursor()

	def left(self):
		if self.image1 is None:
			return
		x, y = self.center
		x -=  self.w_canvas / self.w_image1 / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def right(self):
		if self.image1 is None:
			return
		x, y = self.center
		x +=  self.w_canvas / self.w_image1 / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def up(self):
		if self.image1 is None:
			return
		x, y = self.center
		y -=  self.h_canvas / self.h_image1 / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def down(self):
		if self.image1 is None:
			return
		x, y = self.center
		y +=  self.h_canvas / self.h_image1 / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def zoom_mouse(self, step):
		if self.image1 is None:
			return
		self.normal_cursor()
		if self.x_canvas < 0 or self.y_canvas < 0 or \
				self.x_canvas >= self.w_canvas or self.y_canvas >= self.h_canvas:
			self.zoom(step)
			return
		x_diff = (self.w_canvas / 2 - self.x_canvas) / self.scale
		y_diff = (self.h_canvas / 2 - self.y_canvas) / self.scale
		self.scale *= step
		x = self.center[0] + (1/step-1) * x_diff / self.w_image1
		y = self.center[1] + (1/step-1) * y_diff / self.h_image1
		self.center = (x, y)
		self.adjust_zoom()

	def zoom(self, step):
		if self.image1 is None:
			return
		self.scale *= step
		self.adjust_zoom()

	def adjust_zoom(self):
		if self.image1 is None:
			return
		if self.scale * self.w_image1 < self.w_canvas and self.scale * self.h_image1 < self.h_canvas:
			self.scale = min(self.w_canvas / self.w_image1, self.h_canvas / self.h_image1)
		elif self.scale * MIN_PIXELS_IN_CANVAS > min(self.w_canvas, self.h_canvas):
			self.scale = min(self.w_canvas, self.h_canvas) / MIN_PIXELS_IN_CANVAS
		self.adjust_pos()

	def adjust_pos(self):
		w = self.w_canvas / self.scale / self.w_image1
		h = self.h_canvas / self.scale / self.h_image1
		x = 0.5
		y = 0.5
		if w <= 1:
			x = max(self.center[0], w / 2)
			x = min(x, 1 - w / 2)
		if h <= 1:
			y = max(self.center[1], h / 2)
			y = min(y, 1 - h / 2)
		self.center = (x, y)
		self.delayed_redraw()

	def visible_rect(self):
		x = round(self.center[0] * self.w_image1 - self.w_canvas / 2 / self.scale)
		y = round(self.center[1] * self.h_image1 - self.h_canvas / 2 / self.scale)
		w = round(self.w_canvas / self.scale)
		h = round(self.h_canvas / self.scale)
		if w < 1 or h < 1:
			return (0, 0, 0, 0)
		else:
			return (x, y, w, h)

	def to_canvas(self, px, py):
		x,y,_,_ = self.visible_rect()
		return round((px - x) * self.scale), round((py - y) * self.scale)

	def from_canvas1(self, px, py):
		x,y,_,_ = self.visible_rect()
		return round(px / self.scale + x), round(py / self.scale + y)

	def from_canvas2(self, px, py):
		x, y = self.from_canvas1(self.x_canvas, self.y_canvas)
		triangle_pairs = point_pairs_to_triangle_pairs(self.point_pairs)
		return undistort_point(x, y, triangle_pairs)

	def key(self, event):
		if event.char == ' ':
			self.register_point()
		elif event.char == '<':
			self.zoom(KEY_ZOOM_STEP)
		elif event.char == '>':
			self.zoom(1 / KEY_ZOOM_STEP)
		elif event.char == '+':
			self.zoom(KEY_ZOOM_STEP)
		elif event.char == '-':
			self.zoom(1 / KEY_ZOOM_STEP)

	def register_point(self):
		if self.image1 is None:
			return
		x, y = self.from_canvas1(self.x_canvas, self.y_canvas)
		p = self.from_canvas2(self.x_canvas, self.y_canvas)
		if p is not None:
			self.point_pairs.append((p, (x, y)))
			self.set_distorted()

	def unregister_point(self, event):
		if self.image1 is None:
			return
		i, d = self.nearest_point_index(self.x_canvas, self.y_canvas)
		if i >= 0:
			self.point_pairs.pop(i)
			self.normalize_point_pairs()
			self.set_distorted()

	def nearest_point_index(self, x_canvas, y_canvas):
		best_i = -1
		best_d = math.inf
		for i, (_, (px, py)) in enumerate(self.point_pairs):
			cx, cy = self.to_canvas(px, py)
			d = math.dist((cx, cy), (x_canvas, y_canvas))
			if d < best_d:
				best_d = d
				best_i = i
		return best_i, best_d

	def show_wait(self):
		self.winfo_toplevel().config(cursor='watch')
		self.winfo_toplevel().update()

	def show_drag(self):
		self.winfo_toplevel().config(cursor='crosshair')

	def normal_cursor(self):
		self.winfo_toplevel().config(cursor='')

	def save(self):
		None

class AlignImageStandalone(AlignImage):
	def __init__(self, root):
		AlignImage.__init__(self, root)

	def set_images(self, image1, image2, point_pairs, image_file, point_file):
		super().set_images(image1, image2, point_pairs)
		self.image_file = image_file
		self.point_file = point_file

	def save(self):
		self.distorted.save(self.image_file)
		write_point_pairs(self.point_pairs, self.point_file)

if __name__ == '__main__':
	point_file_in = None
	point_file_out = 'pointpairs.csv'
	image_file = 'distorted.png'
	try:
		opts, vals = getopt(sys.argv[1:], 'p:d:', ['points=', 'distorted='])
	except GetoptError as err:
		print(err)
		sys.exit(1)
	if len(vals) != 2:
		print('Required are two arguments (images)')
		sys.exit(1)
	image1 = Image.open(vals[0])
	image2 = Image.open(vals[1])
	for opt, val in opts:
		if opt in ('-p', '--points'):
			point_file_in = val
		elif opt in ('-d', '--distorted'):
			image_file = val
	point_pairs = read_point_pairs(point_file_in) if point_file_in is not None else []
	root = tk.Tk()
	app = AlignImageStandalone(root)
	app.set_images(image1, image2, point_pairs, image_file, point_file_out)
	app.mainloop()
