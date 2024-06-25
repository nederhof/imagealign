# imagealign

This tool distorts one image to align with another.
Corresponding points are specified by a graphical user interface.
Local affine transforms are applied on triangles between specified points.

Assume in the following examples
that `image1.png` and `image2.png` are two images of the same document that
need to be aligned. For example, `image1.png` is a photograph of a papyrus and 
`image2.png` is a facsimile, possibly prepared from that same photograph, or from another photograph
that may not quite align with the first. Other common image formats such as JPG are also allowable.

## Preparation

Make sure that Python packages numpy, cv2, PIL, webbrowser are available. Installing is typically by:

```
pip install numpy
pip install opencv-python
pip install pillow
pip install webbrowser
```

## Starting

The simplest way of starting the tool is by something like:

```
cd src
python imagealign.py image1.png image2.png
```
The task is now to create a distorted version of `image2.png` 
that aligns with `image1.png`, of the same dimensions as
`image1.png`. The alignment is done by manually specifying
corresponding points of `image1.png` and `image2.png`. By default, the distorted image will
eventually be written to 
`distorted.png`, and the list of corresponding point pairs (with the (x,y) coordinates in `image2.png`
followed by the (x,y) coordinates in `image1.png`) will be written to `pointpairs.csv`.
If other output files are desired, then these can be indicated by flags `-d` and `-p`
as in:

```
python imagealign.py -d mydistorted.png image1.png image2.png
python imagealign.py -p mypointpairs.csv image1.png image2.png
python imagealign.py -d mydistorted.png -p mypointpairs.csv image1.png image2.png
```
If `mypointpairs.csv` already exists, then the tool is initialized with the point pairs
read from that file. In the CSV files, values are separated by spaces.

Given point pairs as above in `mypointpairs.csv`, 
one can convert a list of points in `image2.png` to corresponding points in `image1.png`.
If the input list of points is in `inpoints.csv` 
and the output list of points is to be written to `outpoints.csv`, then do:

```
python imagedistortion.py mypointpairs.csv inpoints.csv outpoints.csv
```
Points in `image2.png` that fall outside the polygon that is mapped to `image1.png` are ignored.

## Interface of imagealign

### Menu

| *Item* | *Shortcut* | *MacOS Shortcut* | *Meaning* |
| :----------- | :----------- | :----------- | :----------- |
| Save | Ctrl+S | Command+S | Save distorted image and point pairs |
| Exit | Alt+F4 | Command+W | Leave tool |
| View 1 | 1 | 1 | Show first image |
| View 2 | 2 | 2 | Show second image |
| View both | 3 | 3 | Show both images superimposed |
| Maximize | F11 | Command+Ctrl+F | Toggle full screen |
| Default view | F5 | Command+R | Reset view to default |
| Triangles | t | t | Use triangles only (default) |
| Quadrilaterals | q | q | Use combination of quadrilaterals and triangles |
| Bilinear | b | b | Use bilinear transform for quadrilaterals |
| Warp | w | w | Do not use polygons |
| Help |   |   | Open web page listing keyboard functionality |

### Further keyboard functionality

| *Key* | *Meaning* |
| :----------- | :----------- |
| **spacebar** | Create new point (pair) underneath the mouse pointer, linking the two images |
| **Backspace** | Remove the point (pair) linking the two images that is closest to the mouse pointer |
| **<** or **+** | Zoom in |
| **>** or **-** | Zoom out |
| *arrow keys* | Move up/down/left/right |
| **a** | Find point pairs automatically |
| **f** | Find four point pairs at corners automatically |
| **d** | Delete all point pairs |

### Mouse

Alignment is typically done by first creating a new point (pair) near a place
where the two images do not yet align, by pressing the spacebar, 
and by then altering the position of that point
in either the first or second image.
To alter a point, set the view to 1 (or 2),
move the mouse to be on top of that point, press the left mouse button, move the mouse to the
desired position in image 1 (or in image 2) and release the mouse button. It may take a few seconds for
the distorted image to be recomputed.

When altering or deleting corner points, the tool may automatically add a new corner point to ensure that
each of the four corners is linked to either the first image or the second image.

Use the mouse wheel to zoom in and out.

To navigate, press the left mouse button (while not being on top of a point linking the two
images), drag, and release the mouse button.

### Polygons

By default, triangles from the second image are mapped to triangles from the first image,
using affine transforms. This is in the **Triangle** mode.

In the **Quadrilaterals** mode, the tool automatically merges
some triangles into quadrilaterals. The quadrilaterals are then mapped using
perspective transforms. The downside is however that seams
between quadrilaterals and other quadrilaterals and triangles will start to appear. 
Therefore this may only be appropriate with say four points selected around a text.

As an attempt to avoid seams at the edges of quadrilaterals in the case of perspective
transforms, also a bilinear transform was implemented.
This **Bilinear** mode is generally preferred over the Quadrilaterals mode if there are many
point pairs, resulting in a combination of triangles and quadrilaterals.

In the **Warp** mode, no polygons are used at all. The image transformation is done using the
non-linear Thin Plate Spline method.

### Manually adding points

A suitable strategy to create points aligning the two images is as follows.
Start with corner points. Choose a position in the first image near one of the corners,
say the top-right corner of the top-most, right-most glyph. Then view the second image and
drag the created point similarly to the top-right corner of the top-most, right-most glyph. 
Repeat, eventually adjusting points closer to the center as well if necessary, but it is best
to try to avoid points too close together.
Alternate between viewing the first image, the second image, and both images together.

### Finding points automatically

By pressing **a**, the existing point pairs are deleted, and
corresponding point pairs are automatically found, using SIFT.
The points are spread out over the images.
This is best used in the Triangles, Bilinear and Warp modes.
There are often a small number of incorrect point pairs, which need to be 
removed manually; this is most conveniently done in the Warp mode.

By pressing **f**,
only four new point pairs are introduced, at the corners of the images,
under the assumption that one image resulted from another by a perspective transform.
This is best used in the Quadrilaterals mode.

## Acknowledgements

Ideas and feedback from Christian Casey have been instrumental in bringing this project forward.
