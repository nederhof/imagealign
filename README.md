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

Make sure that packages numpy, cv2, PIL are available. Installing is typically by:

```
pip install numpy
pip install opencv-python
pip install pillow
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

| *Item* | *Shortcut* | *Meaning* |
| :----------- | :----------- | :----------- |
| Save | Ctrl+S | Save distorted image and point pairs |
| Exit | Alt+F4 | Leave tool |
| View 1 | 1 | Show first image |
| View 2 | 2 | Show second image |
| View both | 3 | Show both images superimposed |
| Maximize | F11 | Toggle full screen |
| Default view | F5 | Reset view to default |

### Further keyboard functionality

| *Key* | *Meaning* |
| :----------- | :----------- |
| **Spacebar** | Create new point (pair) linking the two images |
| **Delete** | Remove the point (pair) linking the two images that is closest to the mouse pointer |
| **<** | Zoom in |
| **>** | Zoom out |
| *arrow keys* | Move up/down/left/right

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
