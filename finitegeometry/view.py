import copy
import os

from PyQt5.QtCore import QPointF, QRectF, Qt, QLineF, QMimeData, QPoint, \
    pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QDrag, QPixmap, \
    QDropEvent, QDragLeaveEvent, QResizeEvent, QImageWriter, QImage, QIcon, \
    QDragEnterEvent
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow, \
    QGraphicsItem, QStyleOptionGraphicsItem, QGraphicsScene, QListWidget, \
    QLineEdit, QComboBox, QLabel, QDockWidget, QListWidgetItem, QVBoxLayout, \
    QPushButton, QHBoxLayout, QWidget, QSpinBox, QMenu, QMenuBar, QStatusBar, \
    QFileDialog, QMessageBox, QColorDialog, QDialog

from finitegeometry.lang import Interpreter
from finitegeometry.model import Grid, SE, SW, NE, NW
import finitegeometry.constants as constants

def pf(vertices):
    def fnk(pai: QPainter, sogi: QStyleOptionGraphicsItem, wi=None,
            offset=(0, 0)):
        pen = QPen(constants.FOREGROUND_COLOR)
        bru = QBrush(constants.FOREGROUND_COLOR)
        pai.setBrush(bru)
        pai.setPen(pen)
        verts = [QPointF(x + offset[0], y + offset[1]) for (x, y) in vertices]
        pai.drawConvexPolygon(*verts)

    return fnk


class Tile(QGraphicsItem):
    paintFuncs = {
        str(SE): pf([(0, 50), (50, 50), (50, 0)]),
        str(NW): pf([(0, 0), (0, 50), (50, 0)]),
        str(SW): pf([(0, 0), (0, 50), (50, 50)]),
        str(NE): pf([(0, 0), (50, 50), (50, 0)])
    }

    def __init__(self, indexi, indexj, frag, par=None):
        super(Tile, self).__init__(par)
        self.row = indexi
        self.col = indexj
        self.hovered = False
        self.paintFun = self.paintFuncs[str(frag)]
        self.setAcceptDrops(True)

    def paint(self, pai: QPainter, sty, wi=None):
        if self.isSelected():
            pai.fillRect(self.boundingRect(), constants.SELECTION_COLOR)
        elif self.hovered:
            pai.fillRect(self.boundingRect(), constants.SELECTION_COLOR)
        self.paintFun(pai, sty, wi)

    def boundingRect(self):
        return QRectF(0, 0, 50, 50)

    def itemChange(self, change, val):
        if change == QGraphicsItem.ItemPositionHasChanged:
            pass

        return super().itemChange(change, val);

    def mousePressEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.isSelected():
            self.setCursor(Qt.ClosedHandCursor)
        else:
            super(Tile, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if QLineF(QPointF(event.screenPos()), QPointF(event.buttonDownScreenPos(
                Qt.LeftButton))).length() < QApplication.startDragDistance():
            return

        drag = QDrag(event.widget())
        mime = QMimeData()
        drag.setMimeData(mime)
        view = self.scene().views()[0]
        ll = "%s%d" % view.lastSelection
        mime.setText(ll)
        f = self.boundingRect().toRect()
        width = f.width()
        height = f.height()
        num = int(ll[1])
        if ll[0] == 'r':
            offsets = [(0, 0), (width, 0), (2 * width, 0), (3 * width, 0)]
            width *= 4
        elif ll[0] == 'c':
            offsets = [(0, 0), (0, height), (0, 2 * height), (0, 3 * height)]
            height *= 4
        else:
            offsets = [(0, 0), (width, 0), (0, height), (height, width)]
            height *= 2
            width *= 2
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.darkYellow)
        pai = QPainter()

        pai.begin(pixmap)
        for it, off in zip(view.lastPhysicalSelection, offsets):
            # it.hide()
            it.paintFun(pai, None, None, offset=off)
        pai.end()
        drag.setPixmap(pixmap)

        drag.exec_(Qt.MoveAction | Qt.CopyAction, Qt.CopyAction)


    def mouseReleaseEvent(self, e):
        if self.isSelected():
            self.scene().views()[0].decideSelection((self.row, 1),
                                                    (self.col, 1), 1)
        else:
            pass
            # super(Tile, self).mouseReleaseEvent(e)

    def dropEvent(self, e):
        # for x in self.scene().views()[0].targetedItems(e.pos()):
        #     x.hovered = False
        #     x.update()
        super(Tile, self).dropEvent(e)
        pass

    def dragEnterEvent(self, e):
        # for x in self.scene().views()[0].targetedItems(e.pos()):
        #     x.hovered = True
        #     x.update()
        super(Tile, self).dragEnterEvent(e)
        pass

    def dragMoveEvent(self, e):
        super(Tile, self).dragMoveEvent(e)
        pass

    def dragLeaveEvent(self, e):
        # for x in self.scene().views()[0].targetedItems(e.pos()):
        #     x.hovered = True
        #     x.update()
        super(Tile, self).dragLeaveEvent(e)
        pass


class Canvas(QGraphicsView):
    
    def __init__(self, grid, timer, par=None):
        super(Canvas, self).__init__(par)
        self.timer = timer
        self.rbRect = None
        self.targets = []
        self.lastSelection = ('r', 0)
        self.lastPhysicalSelection = []
        self.interpreter = Interpreter()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scene = QGraphicsScene(self)
        scene.setItemIndexMethod(QGraphicsScene.NoIndex)
        scene.setSceneRect(0, 0, 200, 200)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        #        self.setRubberBandSelectionMode()
        self.setAcceptDrops(True)
        self.physicalGrid = {}
        
        self.setScene(scene)
        self.rubberBandChanged.connect(self.createSelection)
        self.setCacheMode(QGraphicsView.CacheBackground)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.grid = grid  # this is the model
        self.placeInScene()

    def resizeEvent(self, e: QResizeEvent):
        # self.fitInView(QRectF(0, 0, e.size().height(), e.size().width()), Qt.IgnoreAspectRatio)
        os = e.oldSize()
        ns = e.size()
        if (os.height(), os.width()) == (-1, -1):
            os = ns
        self.scale(ns.width() / os.width(), ns.height() / os.height())

    def resetGrid(self, grid = None):
        if grid:
            self.grid = grid
        else:
            self.grid = Grid()

    def placeInScene(self):
        x = 0
        y = 0
        for indexi, r in enumerate(self.grid.grid):
            for indexj, i in enumerate(r):
                t = Tile(indexi, indexj, i)
                self.physicalGrid[(indexi, indexj)] = t
                # t.setFlag(QGraphicsItem.ItemIsMovable)
                t.setFlag(QGraphicsItem.ItemIsSelectable)
                t.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                t.setPos(x, y)
                self.scene().addItem(t)
                x += t.boundingRect().width()
            y += t.boundingRect().height()
            x = 0

    def createSelection(self, a, b, c):
        if not a and not b and not c:
            histo_r = {}
            histo_c = {}
            wereSelected = 0
            for x in self.items(self.rbRect):
                # build histogram to understand who's selected
                histo_r[x.row] = histo_r.get(x.row, 0) + 1
                histo_c[x.col] = histo_c.get(x.col, 0) + 1
                # x.setFlag(QGraphicsItem.ItemIsSelectable)
                x.setSelected(False)
                wereSelected += 1
            mr = self.__highest(histo_r)
            mc = self.__highest(histo_c)
            self.decideSelection(mr, mc, wereSelected)

            self.rbRect = None
        else:
            self.rbRect = a

    def decideSelection(self, mr, mc, wereSelected=1):
        self.lastPhysicalSelection.clear()
        if mc[1] > mr[1]:
            self.columnSelect(mc[0])
            self.lastSelection = ('c', mc[0])
        elif mc[1] < mr[1]:
            self.rowSelect(mr[0])
            self.lastSelection = ('r', mr[0])
        elif wereSelected == 1:
            if self.lastSelection[0] == 'r':
                self.decideSelection((mr[0], 100), mc)
            elif self.lastSelection[0] == 'c':
                self.decideSelection(mr, (mc[0], 100))
            else:
                self.blockSelect(mr[0], mc[0])
        else:
            c = mc[0]
            r = mr[0]
            bd = self.blockSelect(r, c)
            self.lastSelection = ('b', bd[2])
            pass

    def whichBlock(self, r, c):
        if c < 2 and r < 2:
            s = 0
            return ((0, 2), (0, 2), s)
        elif c >= 2 and r < 2:
            s = 1
            return ((0, 2), (2, 4), s)
        elif c < 2 and r >= 2:
            s = 2
            return ((2, 4), (0, 2), s)
        else:
            s = 3
            return ((2, 4), (2, 4), s)

    def select(self, gi):
        gi.setSelected(True)
        self.lastPhysicalSelection.append(gi)

    def blockSelect(self, r, c):
        (r, c, bid) = self.whichBlock(r, c)
        self.doOnBlock(r, c, self.select)
        return (r, c, bid)

    def doOnBlock(self, r, c, fun):
        for i in range(*r):
            for j in range(*c):
                gi = self.physicalGrid[(i, j)]
                fun(gi)

    def rowSelect(self, r):
        self.doOnRow(r, self.select)

    def doOnRow(self, r, fun):
        for x in range(0, 4):
            gi = self.physicalGrid[(r, x)]
            fun(gi)

    def columnSelect(self, c):
        self.doOnColumn(c, self.select)

    def doOnColumn(self, c, fun):
        for x in range(0, 4):
            gi = self.physicalGrid[(x, c)]
            fun(gi)

    def __highest(self, ha):
        mm = (None, 0)
        for i, v in ha.items():
            if mm[1] < v:
                mm = (i, v)
        return mm
    
    request_update_symmetries = pyqtSignal(list)

    def redrawScene(self):
        self.scene().clear()
        self.placeInScene()
        syms = self.grid.symmetries()
        self.request_update_symmetries.emit(syms)

    moveAccepted = pyqtSignal()
    select_last = pyqtSignal()

    def enterEvent(self, QEvent):
        self.select_last.emit()

    def textFromInterpreter(self, s):
        mo = self.interpreter.interpret(s)
        if mo:
            self.grid = mo(self.grid)
            self.redrawScene()
            if not self.timer.isActive():
                self.parent().insert_action_item_in_list(s,self.grid)
                self.moveAccepted.emit()
                
    def setItemIcon(self, lit):
        pim = QPixmap(50, 50)
        pai = QPainter()
        pim.fill(constants.BACKGROUND_COLOR)
        self.scene().clearSelection()
        pai.begin(pim)
        pai.setRenderHint(QPainter.Antialiasing)
        self.scene().render(pai)
        pai.end()
        ico = QIcon(pim)
        lit.setIcon(ico)

    def collect(self, gi):
        self.targets.append(gi)

    def targetedItems(self, pos):
        self.targets = []
        drop_tile = self.itemAt(pos)
        if not drop_tile:
            return self.targets
        elif self.lastSelection[0] == 'r':
            self.doOnRow(drop_tile.row, self.collect)
        elif self.lastSelection[0] == 'c':
            self.doOnColumn(drop_tile.col, self.collect)
        else:
            (rs, cs, bid) = self.whichBlock(drop_tile.row, drop_tile.col)
            self.doOnBlock(rs, cs, self.collect)
        return self.targets

    def dropEvent(self, e: QDropEvent):
        targets = self.targetedItems(e.pos())
        if len(targets) > 0:
            s = "%s%d%d"
            it = targets[0]
            act = self.lastSelection[0]
            if act == 'r':
                d = it.row
            elif act == 'c':
                d = it.col
            elif act == 'b':
                d = self.whichBlock(it.row, it.col)[2]
            s = s % (self.lastSelection[0], self.lastSelection[1] + 1, d + 1)
            self.textFromInterpreter(s)
            e.setAccepted(True)
        super(Canvas, self).dropEvent(e)
        pass

    def dragEnterEvent(self, e):
        super(Canvas, self).dragEnterEvent(e)
        pass

    def dragMoveEvent(self, e):
        super(Canvas, self).dragMoveEvent(e)
        pass

    def dragLeaveEvent(self, e: QDragLeaveEvent):
        super(Canvas, self).dragLeaveEvent(e)
        pass


class SymmetryList(QListWidget):
    def update_symmetries(self, li):
        self.clear()
        self.addItems(li)


class ActionList(QListWidget):

    def __init__(self, par = None):
        super(ActionList, self).__init__(par)
        self.setDragEnabled(True)
        
    resetAllAndRerun = pyqtSignal(list)
    
    def mouseDoubleClickEvent(self, QMouseEvent):
        it = self.selectedItems()[0]
        ss = self.row(it) + 1
        li = []
        for x in range(0, ss):
            li.append(self.item(x).data(Qt.DisplayRole))
        for x in range(self.row(it), self.count()):
            self.takeItem(ss)

        # emit reset of model + rerun of the present items in the list
        # self.clear()
        #self.resetAllAndRerun.emit(li)
        pass

class PlayList(QListWidget):
    
    def __init__(self, par = None):
        super(PlayList, self).__init__(par)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.model().rowsInserted.connect(self.check_duplicate)
        
    """ 
    Should allow drag-drop of items to reorder them.
    """
    def enqueue(self, item):
        self.addItem(item.data(Qt.DisplayRole))
        it = self.item(self.count()-1)
        it.setData(Qt.UserRole, item.data(Qt.UserRole))

        
    def dropEvent(self, de):
        super(PlayList, self).dropEvent(de)
    
    def check_duplicate(self, a, b, c):
        pass


class DeclarationLabel(QLabel):
    pass


class InterpreterWidget(QComboBox):
    pass


class FiniteGeometryEditor(QMainWindow):
    def applyAction(self, s,k,n):
        mo = self.canv.interpreter.interpret(s)
        if mo:
            self.canv.grid = mo(self.canv.grid)
        
    def collect_grid(self, s, k, n):
        self.canv.grid = self.acts.item(k).data(Qt.UserRole)
        pass
        
    # def replace_precomputed_grid(self, s, k, n):
    #     #s is the precomputed grid...
        

    def resetGrid(self):
        self.canv.resetGrid()

    # def scan_list(self, iterat, get_command, init_state, before_interpret,
    #              after_interpret, after_list):
    #     n = init_state
    #     self.resetGrid()
    #     for k in iterat:
    #         s = get_command(k)
    #         n = before_interpret(s, k, n)
    #         self.applyAction(s)
    #         n = after_interpret(s, k, n)
    #     after_list(n)
        
    
    def scan_list(self, iterat, get_command, init_state, before_interpret,
                  interpret,after_interpret, after_list):
        n = init_state
        self.resetGrid()
        for k in iterat:
            s = get_command(k)
            n = before_interpret(s, k, n)
            interpret(s,k,n)
            n = after_interpret(s, k, n)
        #after_list(n)
        
    
    def scan_list_of_commands(self, iterat, get_command, init_state, before_interpret,
                              after_interpret, after_list):
        self.scan_list(iterat, get_command, init_state, before_interpret,
                         self.applyAction,after_interpret, after_list)

    def save_checked_state(self, s, k, n):
        if self.acts.item(k).checkState() == Qt.Checked:
            n.append((self.acts.item(k), copy.copy(self.canv.grid)))
        return n

    def save_checked_item(self, s, k, n):
        if self.acts.item(k).checkState() == Qt.Checked:
            fn = "%d%s.png" % n
            self.redraw_and_update_canvas()
            sce = self.canv.scene()
            wid = int(sce.width())
            hei = int(sce.height())
            im = QImage(wid, hei, QImage.Format_ARGB32)
            pai = QPainter()
            im.fill(constants.BACKGROUND_COLOR)
            pai.begin(im)
            pai.setRenderHint(QPainter.Antialiasing)
            self.canv.scene().render(pai)
            pai.end()
            im.save(fn)
            n = (n[0]+1, n[1])
        return n

    def get_command_from_listWidget(self, k):
        it = self.acts.item(k)
        return it.data(Qt.DisplayRole)

    def iterator_over_listWidget(self):
        return range(0, self.acts.count())

    def redraw_and_update_canvas(self):
        self.canv.redrawScene()
        self.canv.update()

    def rerun(self, *args):
        self.scan_list_of_commands(self.iterator_over_listWidget(),
                      self.get_command_from_listWidget,
                      init_state=0,
                      before_interpret=lambda x, y, z: z,
                      after_interpret=lambda x, y, z: z,
                      after_list=lambda x: self.redraw_and_update_canvas())

    def printall(self, name=''):
        self.scan_list_of_commands(self.iterator_over_listWidget(),
                      self.get_command_from_listWidget,
                      init_state=(0, name),
                      before_interpret=lambda x, y, z: z,
                      after_interpret=self.save_checked_item,
                      after_list=self.rerun)
        
    def precompute_selected_grids(self):
        self.scan_list_of_commands(self.iterator_over_listWidget(),
                      self.get_command_from_listWidget,
                      init_state=self.precomputed,
                      before_interpret=lambda x, y, z: z,
                      after_interpret=self.save_checked_state,
                      after_list=self.rerun)
        return self.precomputed

    def insert_action_item_in_list(self, s, grid):
        lit = QListWidgetItem(s, self.acts)
        lit.setFlags(lit.flags() | Qt.ItemIsUserCheckable)
        lit.setData(Qt.UserRole, grid)
        lit.setCheckState(False)
        self.canv.setItemIcon(lit)

    def load_sequence_file(self, path):
        commands = self.canv.interpreter.read_file(path)
        self.acts.clear()
        self.insert_action_item_in_list("<init>", self.canv.grid)
        def addItemToList(s,k,n):
            self.redraw_and_update_canvas()
            self.insert_action_item_in_list(s, self.canv.grid)

        self.scan_list_of_commands(iterat=commands,
                      get_command=lambda x : x,
                      init_state=0,
                      before_interpret=lambda x, y, z: z,
                      after_interpret=addItemToList,
                      after_list=lambda x: self.redraw_and_update_canvas()
                      )

        pass
        
    def print_to_file(self):
         
        with open(self.current_file, 'w') as f:
            self.scan_list(self.iterator_over_listWidget(),
                          self.get_command_from_listWidget,
                          init_state=f,
                          interpret=self.collect_grid,
                          before_interpret=lambda x, y, z: f,
                          after_interpret=self.write_comment,
                          after_list=self.rerun)
        self.acts.setCurrentRow(self.acts.count()-1)

    def write_comment(self, x, y, f):
        f.write(x + "\n")
        s = str(self.canv.grid)
        for k in s.split("\n"):
            f.write("# " + k + "\n")

    def selectall(self):
        for k in range(0, self.acts.count()):
            self.acts.item(k).setCheckState(Qt.Checked)

    def unselectall(self):
        for k in range(0, self.acts.count()):
            self.acts.item(k).setCheckState(Qt.Unchecked)

    def enqueue(self):
        for k in range(0, self.acts.count()):
            it = self.acts.item(k)
            if it.checkState() == Qt.Checked:
                self.playlist.enqueue(it)
                
    def clearList(self):
        for x in range(1,self.acts.count()):
            self.acts.takeItem(1)
        self.acts.setCurrentItem(self.acts.item(0)) 
        

    def animation_frame(self):
        if self.frame == self.playlist.count():
            # self.canv.resetGrid()
            # self.canv.redrawScene()
            # self.canv.update()
            # self.acts.clearSelection()
            self.frame = 0
        
        self.frameInList()

    def frameInList(self):
        it = self.playlist.item(self.frame)
        #s = it.data(Qt.DisplayRole)
        #self.canv.textFromInterpreter(s)
        self.playlist.setCurrentItem(self.playlist.item(self.frame))
        self.frame = (self.frame + 1)

    def disable_controls(self):
        self.__enable_controls(False)
        
    def enable_controls(self):
        self.__enable_controls(True)
        
    def __enable_controls(self, bo):
        self.inte.setEnabled(bo)
        self.play.setEnabled(bo)
        self.playlist.setEnabled(bo)
        self.canv.setAcceptDrops(bo)
        self.acts.setEnabled(bo)
    

    def start_playing(self):
        self.playlist.currentItemChanged.connect(self.change_canvas_on_selection(self.playlist))
        
        # and connect self.change_canvas_on_selection to playlist
        if self.playlist.count() > 0:
            self.frame = self.playlist.count()
            self.disable_controls()
            self.animation_timer.timeout.connect(self.animation_frame)
            self.canv.redrawScene()
            self.canv.update()
            self.animation_timer.start(int(self.speed.text()))
        pass

    def stop_playing(self):
        self.playlist.currentItemChanged.disconnect()
        self.animation_timer.timeout.disconnect()
        self.connect_acts()
        self.enable_controls()
        self.animation_timer.stop()
        #self.rerun()
        pass
    
    def start_playing_selected(self):
        self.precomputed = []
        self.precompute_selected_grids()
        # should create items, each of which with 
        # the icon corresponding to its payload 
        
        
        # if len(self.precomputed) > 0:
        #     self.disable_controls()
        #     self.animation_precomputed_iterator = iter(self.precomputed)
        #     self.animation_timer.timeout.connect(self.precomputed_animation_frame)
        #     self.animation_timer.start(int(self.speed.text()))
        #     pass
        
    
    def precomputed_animation_frame(self):
        try:
            (listitem, grid) = next(self.animation_precomputed_iterator)
        except:
            self.animation_precomputed_iterator = iter(self.precomputed)
            (listitem, grid) = next(self.animation_precomputed_iterator)
        self.canv.resetGrid(grid)
        self.canv.redrawScene()
        self.canv.update()
        listitem.setSelected(True)
        pass

    def change_canvas_on_selection(self, lst):
        def _fn():
            it = lst.currentItem()
            self.canv.grid = it.data(Qt.UserRole)
            self.canv.redrawScene()
        return _fn
        

    def connect_acts(self):
        self.acts.resetAllAndRerun.connect(self.rerun)
        self.acts.currentItemChanged.connect(self.change_canvas_on_selection(self.acts))
        
        
    TITLE = "The 4x4 Square[*]"
    def __init__(self):
        super(FiniteGeometryEditor, self).__init__()
        self.frame = 0
        self.will_overwrite = False
        self.current_file = None
        self.precomputed = []
        self.animation_precomputed_iterator = None
        self.animation_timer = QTimer()
        self.canv = Canvas(Grid(), self.animation_timer, self)
        self.setWindowTitle(self.TITLE)
        self.createMenus()
        self.setCentralWidget(self.canv)
        self.symm = SymmetryList()
        self.canv.request_update_symmetries.connect(self.symm.update_symmetries)
        self.acts = ActionList()
        self.insert_action_item_in_list("<init>", self.canv.grid)
        self.playlist = PlayList()
        self.inte = InterpreterWidget()
        self.inte.setEditable(True)
        # use validator to implement the logic that does not require
        # commands to be edited using text area!
        self.inte.currentTextChanged.connect(self.canv.textFromInterpreter)
#        self.canv.interpretMove.connect(self.canv.textFromInterpreter)
        self.canv.moveAccepted.connect(lambda : self.setWindowModified(True))
        self.connect_acts()
        self.canv.select_last.connect(lambda : self.acts.setCurrentItem(self.acts.item(self.acts.count()-1)))

        la = QVBoxLayout()
        self.clear = QPushButton("Clear")
        self.sel_all = QPushButton("Select all")
        self.unsel_all = QPushButton("Unselect all")
        self.print = QPushButton("Export selected to PNG")
        self.to_file = QPushButton("Save as .sqs file")
        #self.to_playlist = QPushButton("To playlist")
        self.print.pressed.connect(self.export_sequence)
        self.sel_all.pressed.connect(self.selectall)
        self.unsel_all.pressed.connect(self.unselectall)
        self.clear.pressed.connect(self.clearList)
        #self.to_playlist.pressed.connect(self.enqueue)
        self.to_file.pressed.connect(self.save_file)

        bug = QHBoxLayout()
        for k in [self.clear, self.sel_all, self.unsel_all,
                  self.print, self.to_file]:
            bug.addWidget(k)

        ctrls = QHBoxLayout()
        self.play = QPushButton("Play")
        self.play.pressed.connect(self.start_playing)
        self.stop = QPushButton("Stop")
        self.stop.pressed.connect(self.stop_playing)
        self.speed = QSpinBox()
        self.speed.setSingleStep(100)
        self.speed.setMaximum(10000)
        self.speed.setValue(500)
        for k in [self.play,  self.stop, self.speed]:
            ctrls.addWidget(k)

        la.addWidget(self.acts)
        la.addLayout(ctrls)
        la.addLayout(bug)
        wi = QWidget()
        wi.setLayout(la)
        for title, item, pos in [
            ("Symmetries", self.symm, Qt.LeftDockWidgetArea),
            ("Actions performed", wi, Qt.RightDockWidgetArea),
            ("Playlist", self.playlist, Qt.RightDockWidgetArea),
            ("Interpreter", self.inte, Qt.BottomDockWidgetArea)]:
            dock = QDockWidget(title, self)
            dock.setWidget(item)
            item.setParent(dock)
            dock.setFeatures(
                QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)
            self.addDockWidget(pos, dock)
        self.setStatusBar(QStatusBar())

    def load_file(self):
        sqs = "sequence file (*.sqs)"
        any = "*"
        x4 = "4x4 square file (*.4x4)"
        path, ty = QFileDialog.getOpenFileName(self, "Open File", '',
                                              "%s\n%s\n%s"%(sqs, x4, any))
        if path:
            if ty == sqs:
                path = self.add_extension(path,".sqs")
                self.load_sequence_file(path)
            elif ty == x4:
                path = self.add_extension(path,".4x4")
                self.load_4x4_file(path)
            else:
                return
            self.set_current_file(path)

    def save_file_as(self):
        sqs = "sequence file (*.sqs)"
        any = "*"
        x4 = "4x4 square file (*.4x4)"
        path, ty = QFileDialog.getSaveFileName(self, "Save File", '',
                                               "%s\n%s\n%s"%(sqs, x4, any))
        if path:
            if ty == sqs:
                path = self.add_extension(path,".sqs")
                self.write_sequence_file(path)
            elif ty == x4:
                path = self.add_extension(path,".4x4")
                self.write_4x4_file(path)
            else:
                pass


    def add_extension(self, path, desired):
        if path.endswith(desired):
            return path
        else:
            return path+desired
        
            
    def set_current_file(self, path, prompt_for_save = False):
    
        self.setWindowTitle((self.TITLE+" - %s[*]") % path)
        self.setWindowModified(False)
        self.current_file = path

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
        else:
            self.write_sequence_file(self.current_file)
            pass
            
    
    def write_sequence_file(self, path):
        self.set_current_file(path)
        self.print_to_file()
        
        
    def write_4x4_file(path):
        pass
    
    def export_sequence(self):
        if self.current_file:
            self.printall(name=os.path.basename(self.current_file))
        else:
            self.export_sequence_as()
        pass
        
    def export_sequence_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export as png", '',
                                              "*")
        if path:
            self.printall(name=os.path.basename(path))
            self.set_current_file(path)
        pass
        
    def select_foreground_color(self):
        newColor = QColorDialog.getColor(title="Select foreground color")
        if newColor:
            constants.FOREGROUND_COLOR = newColor
        
    def select_background_color(self):
        newColor = QColorDialog.getColor(title="Select background color")
        if newColor:
            constants.BACKGROUND_COLOR = newColor
            self.canv.scene().setBackgroundBrush(newColor)
            
    def select_selection_color(self):
        newColor = QColorDialog.getColor(title="Select selection color")
        if newColor:
            constants.SELECTION_COLOR = newColor
    
    def select_pattern(self):
        qdia = QDialog(self)
        qdia.setWindowTitle("Select an initial pattern")
        vbox = QVBoxLayout()
        qdia.setLayout(vbox)
        canvas = Canvas(Grid(), None)
        vbox.addWidget(canvas)
        for x in canvas.scene().items():
            def fuu(ev):
                canvas.grid.grid[0][0] = NE
                x.paintFun = x.paintFuncs[str(NE)]
                x.update()
                canvas.update()
            x.mousePressEvent =  fuu
        
        qdia.exec_()
        pass
        
    def about_popup(self):
        QMessageBox.about(self, self.TITLE, "© 2016 Gabriele Paganelli")
        pass
        
    def createMenus(self):
        def adda(a, s):
            return a.addAction(s)

        self.file = QMenu("File")

        def fact(s):
            return adda(self.file, s)

        self.load = fact("Load")
        self.load.triggered.connect(self.load_file)
        self.save = fact("Save")
        self.save.triggered.connect(self.save_file)
        self.saveas = fact("Save as")
        self.saveas.triggered.connect(self.save_file_as)
        self.export = fact("Export selected")
        self.export.triggered.connect(self.export_sequence)
        self.exportas = fact("Export selected as")
        self.exportas.triggered.connect(self.export_sequence_as)
        self.quit = fact("Quit")
        self.quit.triggered.connect(lambda : QApplication.quit())
        self.edit = QMenu("Edit")

        def eact(s):
            return adda(self.edit, s)

        def cact(s):
            return adda(self.colors, s)
        
        self.colors = QMenu("Colors")
        self.edit.addMenu(self.colors)
        
        self.fore = cact("Foreground")
        self.back = cact("Background")
        self.sele = cact("Selection")
        
        self.fore.triggered.connect(self.select_foreground_color)
        self.back.triggered.connect(self.select_background_color)
        self.sele.triggered.connect(self.select_selection_color)
        self.initial = eact("Initial pattern")
        self.initial.triggered.connect(self.select_pattern)
        self.help = QMenu("Help")

        def hact(s):
            return adda(self.help, s)

        self.about = hact("About")
        self.about.triggered.connect(self.about_popup)
        for x in [self.file, self.edit, self.help]:
            self.menuBar().addMenu(x)

        self.menuBar().setNativeMenuBar(False)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    mw = FiniteGeometryEditor()

    mw.show()
    sys.exit(app.exec_())
