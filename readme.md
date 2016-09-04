# The 4x4 Square #

This Python-PyQT5 application allows to play with the 4x4 square first 
investigated (to my knowledge) by Steven H. Cullinane.

* Links:
http://finitegeometry.org/sc/16/geometry.html

### License ###
MIT licensed.

### Future work ###
* The "Actions performed" list should be a tree, so that 
 a user can develop several different threads of modifications.

### Known bugs ###
* Some problems with drag-drop of blocks, when using the automated recognition
(selecting with left button, after having selected with right button in a previous move)

### Other "problems" ###
* Drag-and-drop between lists is the default one for ListWidgets.
  The data of the list items are copied "ex nihilo" 
  (that is, no constructor is ran upon creation)
  Therefore I had to create `__eq__` and `__hash__` for objects of type Fragment. 

