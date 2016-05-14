import copy
import os

from PyQt5.QtCore import QPointF, QRectF, Qt, QLineF, QMimeData, QPoint, \
    pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QDrag, QPixmap, \
    QDropEvent, QDragLeaveEvent, QResizeEvent, QImageWriter, QImage, QIcon
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
        bru = QBrush(constants.FOREGROUND_COLOR)
        pai.setBrush(bru)
        verts = [QPointF(x + offset[0], y + offset[1]) for (x, y) in vertices]
        pai.drawConvexPolygon(*verts)

    return fnk


class Tile(QGraphicsItem):
    paintFuncs = {
        SE: pf([(0, 50), (50, 50), (50, 0)]),
        NW: pf([(0, 0), (0, 50), (50, 0)]),
        SW: pf([(0, 0), (0, 50), (50, 50)]),
        NE: pf([(0, 0), (50, 50), (50, 0)])
    }

    def __init__(self, indexi, indexj, frag, par=None):
        super(Tile, self).__init__(par)
        self.row = indexi
        self.col = indexj
        self.hovered = False
        self.paintFun = self.paintFuncs[frag]
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


        # pixmap = QPixmap(34, 34)
        # pixmap.fill(Qt.white)
        # 
        # painter = QPainter(pixmap)
        # painter.translate(15, 15)
        # painter.setRenderHint(QPainter.Antialiasing)
        # self.paint(painter, None, None)
        # painter.end()
        # 
        # pixmap.setMask(pixmap.createHeuristicMask())
        # 
        # drag.setPixmap(pixmap)
        # drag.setHotSpot(QPoint(15, 20))
        # 
        # drag.exec_()
        # self.setCursor(Qt.OpenHandCursor)

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
        self.setAcceptDrops(True)
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

    def redrawScene(self):
        self.scene().clear()
        self.placeInScene()

    moveAccepted = pyqtSignal()

    def textFromInterpreter(self, s):
        mo = self.interpreter.interpret(s)
        if mo:
            mo(self.grid)
            self.redrawScene()
            if not self.timer.isActive():
                self.parent().insert_action_item_in_list(s)
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
        # pim.scaled(QSize(50,50), Qt.IgnoreAspectRatio,Qt.FastTransformation)
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
    pass


class ActionList(QListWidget):
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
        self.resetAllAndRerun.emit(li)
        pass


class DeclarationLabel(QLabel):
    pass


class InterpreterWidget(QComboBox):
    pass


class FiniteGeometryEditor(QMainWindow):
    def applyAction(self, s,k,n):
        mo = self.canv.interpreter.interpret(s)
        mo(self.canv.grid)
        
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
        after_list(n)
        
    
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

    def insert_action_item_in_list(self, s):
        lit = QListWidgetItem(s, self.acts)
        lit.setFlags(lit.flags() | Qt.ItemIsUserCheckable)
        lit.setCheckState(False)
        self.canv.setItemIcon(lit)

    def load_sequence_file(self, path):
        commands = self.canv.interpreter.read_file(path)
        self.acts.clear()
        def addItemToList(s,k,n):
            self.redraw_and_update_canvas()
            self.insert_action_item_in_list(s)

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
            self.scan_list_of_commands(self.iterator_over_listWidget(),
                          self.get_command_from_listWidget,
                          init_state=f,
                          before_interpret=lambda x, y, z: f,
                          after_interpret=self.write_comment,
                          after_list=self.rerun)

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

    def clearList(self):
        self.acts.clear()
        self.rerun()

    def animation_frame(self):
        if self.frame == self.acts.count():
            self.canv.resetGrid()
            self.canv.redrawScene()
            self.canv.update()
            self.acts.clearSelection()
            self.frame = 0
        else:
            self.frameInList()

    def frameInList(self):
        it = self.acts.item(self.frame)
        s = it.data(Qt.DisplayRole)
        self.canv.textFromInterpreter(s)
        self.acts.setCurrentItem(self.acts.item(self.frame))
        self.frame = (self.frame + 1)

    def disable_controls(self):
        self.__enable_controls(False)
        
    def enable_controls(self):
        self.__enable_controls(True)
        
    def __enable_controls(self, bo):
        self.inte.setEnabled(bo)
        self.play.setEnabled(bo)
        self.play_selected.setEnabled(bo)
        self.canv.setAcceptDrops(bo)
        self.acts.setEnabled(bo)
    

    def start_playing(self):
        if self.acts.count() > 0:
            self.frame = self.acts.count()
            self.disable_controls()
            self.animation_timer.timeout.connect(self.animation_frame)
            self.canv.redrawScene()
            self.canv.update()
            self.animation_timer.start(int(self.speed.text()))
        pass

    def stop_playing(self):
        self.animation_timer.timeout.disconnect()
        self.enable_controls()
        self.animation_timer.stop()
        self.rerun()
        pass
    
    def start_playing_selected(self):
        self.precompute_selected_grids()
        
        if len(self.precomputed) > 0:
            self.disable_controls()
            self.animation_precomputed_iterator = iter(self.precomputed)
            self.animation_timer.timeout.connect(self.precomputed_animation_frame)
            self.animation_timer.start(int(self.speed.text()))
            pass
    
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

    TITLE = "The 4x4 Square[*]"
    def __init__(self):
        super(FiniteGeometryEditor, self).__init__()
        self.frame = 0
        self.current_file = None
        self.precomputed = []
        self.animation_precomputed_iterator = None
        self.animation_timer = QTimer()
        self.canv = Canvas(Grid(), self.animation_timer, self)
        self.setWindowTitle(self.TITLE)
        self.createMenus()
        self.setCentralWidget(self.canv)
        self.symm = SymmetryList()
        self.acts = ActionList()
        self.decl = DeclarationLabel()
        self.decl.setText("(here goes the current pattern declaration)")
        self.inte = InterpreterWidget()
        self.inte.setEditable(True)
        # use validator to implement the logic that does not require
        # commands to be edited using text area!
        self.inte.currentTextChanged.connect(self.canv.textFromInterpreter)
#        self.canv.interpretMove.connect(self.canv.textFromInterpreter)
        self.canv.moveAccepted.connect(lambda : self.setWindowModified(True))
        self.acts.resetAllAndRerun.connect(self.rerun)

        la = QVBoxLayout()
        self.clear = QPushButton("Clear")
        self.sel_all = QPushButton("Select all")
        self.unsel_all = QPushButton("Unselect all")
        self.print = QPushButton("Print")
        self.to_file = QPushButton("To file")
        self.print.pressed.connect(self.printall)
        self.sel_all.pressed.connect(self.selectall)
        self.unsel_all.pressed.connect(self.unselectall)
        self.clear.pressed.connect(self.clearList)
        self.to_file.pressed.connect(self.print_to_file)

        bug = QHBoxLayout()
        for k in [self.clear, self.sel_all, self.unsel_all,
                  self.print, self.to_file]:
            bug.addWidget(k)

        ctrls = QHBoxLayout()
        self.play = QPushButton("Play")
        self.play.pressed.connect(self.start_playing)
        self.play_selected = QPushButton("Play selected")
        self.play_selected.pressed.connect(self.start_playing_selected)
        self.stop = QPushButton("Stop")
        self.stop.pressed.connect(self.stop_playing)
        self.speed = QSpinBox()
        self.speed.setSingleStep(100)
        self.speed.setMaximum(10000)
        self.speed.setValue(500)
        for k in [self.play, self.play_selected, self.stop, self.speed]:
            ctrls.addWidget(k)

        la.addWidget(self.acts)
        la.addLayout(ctrls)
        la.addLayout(bug)
        wi = QWidget()
        wi.setLayout(la)
        for title, item, pos in [
            ("Symmetries", self.symm, Qt.LeftDockWidgetArea),
            ("Actions performed", wi, Qt.RightDockWidgetArea),
            ("Initial element", self.decl, Qt.BottomDockWidgetArea),
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
            
    
        
            
    def set_current_file(self, path):
        self.setWindowTitle((self.TITLE+" - %s[*]") % path)
        self.setWindowModified(False)
        self.current_file = path

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
        else:
            self.write_to_disk(self.current_file)
            pass
            
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
                x.paintFun = x.paintFuncs[NE]
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
        self.export = fact("Export")
        self.export.triggered.connect(self.export_sequence)
        self.exportas = fact("Export as")
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
