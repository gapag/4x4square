from PyQt5.QtCore import QPointF, QRectF, Qt, QLineF, QMimeData, QPoint, \
    pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QDrag, QPixmap, \
    QDropEvent, QDragLeaveEvent, QResizeEvent, QImageWriter, QImage, QIcon
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow, \
    QGraphicsItem, QStyleOptionGraphicsItem, QGraphicsScene, QListWidget, \
    QLineEdit, QComboBox, QLabel, QDockWidget, QListWidgetItem, QVBoxLayout, \
    QPushButton, QHBoxLayout, QWidget, QSpinBox

from finitegeometry.lang import Interpreter
from finitegeometry.model import Grid, SE, SW, NE, NW

def pf(vertices):
    def fnk(pai:QPainter, sogi:QStyleOptionGraphicsItem, wi=None, offset=(0,0)):
        bru = QBrush(Qt.black)
        pai.setBrush(bru)
        verts = [QPointF(x+offset[0],y+offset[1]) for (x,y) in vertices]
        pai.drawConvexPolygon(*verts)
    return fnk
        
class Tile(QGraphicsItem):
    
    paintFuncs = {
        SE : pf([(0,50),(50,50),(50,0)]),
        NW : pf([(0,0),(0,50),(50,0)]),
        SW : pf([(0,0),(0,50),(50,50)]),
        NE : pf([(0,0),(50,50),(50,0)])
    }
    
    def __init__(self, indexi, indexj, frag, par=None):
        super(Tile, self).__init__(par)
        self.row = indexi
        self.col = indexj
        self.hovered = False
        self.paintFun = self.paintFuncs[frag]
        self.setAcceptDrops(True)
        
    def paint(self, pai:QPainter, sty, wi=None):
        if self.isSelected():
            pai.fillRect(self.boundingRect(), Qt.yellow)
        elif self.hovered:
            pai.fillRect(self.boundingRect(), Qt.yellow)
        self.paintFun(pai, sty, wi)
        
    
    def boundingRect(self):
        return QRectF(0,0,50,50)
    
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
        if QLineF(QPointF(event.screenPos()), QPointF(event.buttonDownScreenPos(Qt.LeftButton))).length() < QApplication.startDragDistance():
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
            offsets = [(0,0), (width,0), (2*width,0), (3*width,0)]
            width *= 4
        elif ll[0] == 'c':            
            offsets = [(0,0), (0,height), (0,2*height), (0,3*height)]
            height *= 4
        else :
            offsets = [(0,0), (width,0), (0, height), (height, width)]
            height *=2
            width *=2
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.darkYellow)
        pai = QPainter()
        
        pai.begin(pixmap)
        for it, off in zip(view.lastPhysicalSelection, offsets):
            #it.hide()
            it.paintFun(pai,None, None, offset=off)
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
            self.scene().views()[0].decideSelection((self.row, 1),(self.col, 1),1)
        else:
            pass
        #super(Tile, self).mouseReleaseEvent(e)

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
    
    interpretMove = pyqtSignal(str)
    
    def __init__(self, grid, timer, par=None):
        super(Canvas, self).__init__(par)
        self.timer = timer
        self.rbRect = None
        self.targets = []
        self.lastSelection = ('r',0)
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
        self.grid = grid # this is the model
        self.placeInScene()
        
    def resizeEvent(self, e:QResizeEvent):
        #self.fitInView(QRectF(0, 0, e.size().height(), e.size().width()), Qt.IgnoreAspectRatio)
        os = e.oldSize()
        ns = e.size()
        if (os.height(), os.width()) == (-1,-1):
            os = ns
        self.scale(ns.width()/os.width(), ns.height()/os.height())
    
    
        
    def resetGrid(self):
        self.grid = Grid()
        
    def placeInScene(self):
        x = 0
        y = 0
        for indexi , r in enumerate(self.grid.grid):
            for indexj, i in enumerate(r):
                t = Tile(indexi, indexj, i)
                self.physicalGrid[(indexi, indexj)] = t
                #t.setFlag(QGraphicsItem.ItemIsMovable)
                t.setFlag(QGraphicsItem.ItemIsSelectable)
                t.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                t.setPos(x,y)
                self.scene().addItem(t)
                x += t.boundingRect().width()
            y += t.boundingRect().height()
            x = 0
            
    def createSelection(self,a,b,c):
        if not a and not b and not c:
            histo_r = {}
            histo_c = {}
            wereSelected = 0
            for x in self.items(self.rbRect):
                # build histogram to understand who's selected
                histo_r[x.row] = histo_r.get(x.row, 0)+1
                histo_c[x.col] = histo_c.get(x.col, 0)+1
                #x.setFlag(QGraphicsItem.ItemIsSelectable)
                x.setSelected(False)
                wereSelected += 1
            mr = self.__highest(histo_r)
            mc = self.__highest(histo_c)
            self.decideSelection(mr, mc, wereSelected)
            
            self.rbRect = None
        else :
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
                self.decideSelection((mr[0],100), mc)
            elif self.lastSelection[0] == 'c':
                self.decideSelection(mr, (mc[0],100))
            else:
                self.blockSelect(mr[0],mc[0])
        else:
            c = mc[0]
            r = mr[0]
            bd = self.blockSelect(r,c)
            self.lastSelection = ('b', bd[2])
            pass
    
    def whichBlock(self,r,c):
        if c < 2 and r < 2:
            s = 0
            return ((0,2), (0,2), s)
        elif c >=2 and r < 2:
            s = 1
            return ((0,2), (2,4), s)
        elif c < 2 and r >=2:
            s = 2
            return ((2,4), (0,2), s)
        else:
            s = 3
            return ((2,4), (2,4), s)

    def select(self, gi):
        gi.setSelected(True)
        self.lastPhysicalSelection.append(gi)
        
    def blockSelect(self, r, c):
        (r,c,bid)= self.whichBlock(r,c)
        self.doOnBlock(r,c,self.select)
        return (r,c,bid)
        
    
    def doOnBlock(self, r, c, fun):
        for i in range(*r):
            for j in range(*c):
                gi = self.physicalGrid[(i,j)]
                fun(gi)

    def rowSelect(self, r):
        self.doOnRow(r, self.select)
    
    def doOnRow(self,r, fun):
        for x in range(0,4):
            gi = self.physicalGrid[(r, x)]
            fun(gi)

    def columnSelect(self, c):
        self.doOnColumn(c, self.select)
    
    def doOnColumn(self, c, fun):
        for x in range(0,4):
            gi = self.physicalGrid[(x, c)]
            fun(gi)
    
    def __highest(self, ha):
        mm = (None, 0)
        for i, v in ha.items():
            if mm[1] < v:
                mm = (i, v)
        return mm
    
    
    def listReset(self, l):
        self.grid = Grid()
        for s in l:
            mo = self.interpreter.interpret(s)
            #lit = QListWidgetItem(s,self.parent().acts)
            #lit.setFlags(lit.flags()| Qt.ItemIsUserCheckable)
            mo(self.grid)
            #self.setItemIcon(lit)
            #lit.setCheckState(False)
            
        self.scene().clear()
        self.placeInScene()
    
    #moveAccepted = pyqtSignal()
    
    def textFromInterpreter(self, s):
        mo = self.interpreter.interpret(s)
        if mo :
            mo(self.grid)
            self.scene().clear()
            self.placeInScene()
            if not self.timer.isActive():
                lit = QListWidgetItem(s,self.parent().acts)
                lit.setFlags(lit.flags()| Qt.ItemIsUserCheckable)
                lit.setCheckState(False)
                self.setItemIcon(lit)
            #self.moveAccepted.emit()
            
    def setItemIcon(self, lit):
        pim = QPixmap(50, 50)
        pai = QPainter()
        pim.fill(Qt.white)
        self.scene().clearSelection()
        pai.begin(pim)
        pai.setRenderHint(QPainter.Antialiasing)
        self.scene().render(pai)
        pai.end()
        #pim.scaled(QSize(50,50), Qt.IgnoreAspectRatio,Qt.FastTransformation)
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
            self.doOnBlock(rs,cs, self.collect)
        return self.targets
    
    def dropEvent(self, e:QDropEvent):
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
            s = s% (self.lastSelection[0], self.lastSelection[1]+1,d+1)
            self.interpretMove.emit(s)
            e.setAccepted(True)
        super(Canvas, self).dropEvent(e)
        pass
    
    def dragEnterEvent(self, e):
        super(Canvas, self).dragEnterEvent(e)
        pass
    
    def dragMoveEvent(self, e):
        super(Canvas, self).dragMoveEvent(e)
        pass
    
    def dragLeaveEvent(self, e:QDragLeaveEvent):
        super(Canvas, self).dragLeaveEvent(e)
        pass

class SymmetryList(QListWidget):
    pass

class ActionList(QListWidget):
    
    resetAllAndRerun = pyqtSignal(list)
    
    def mouseDoubleClickEvent(self, QMouseEvent):
        it = self.selectedItems()[0]
        ss = self.row(it)+1
        li = []
        for x in range(0, ss):
            li.append(self.item(x).data(Qt.DisplayRole))
        for x in range(self.row(it), self.count()):
            self.takeItem(ss)
        
        # emit reset of model + rerun of the present items in the list
        #self.clear()
        self.resetAllAndRerun.emit(li)
        pass

class DeclarationLabel(QLabel):
    pass

class InterpreterWidget(QComboBox):
    pass


class FiniteGeometryEditor(QMainWindow):
    
    def printall(self):
        num = 0
        self.canv.resetGrid()
        for k in range(0, self.acts.count()):
            it = self.acts.item(k)
            s = it.data(Qt.DisplayRole)
            mo = self.canv.interpreter.interpret(s)
            mo(self.canv.grid)
            if it.checkState() == Qt.Checked:
                fn = "%d.png" % num
                self.canv.scene().clear()
                self.canv.placeInScene()
                self.canv.update()
                sce = self.canv.scene()
                wid = int(sce.width())
                hei = int(sce.height())
                im = QImage(wid, hei,QImage.Format_ARGB32)
                pai = QPainter()
                im.fill(Qt.white)
                pai.begin(im)
                pai.setRenderHint(QPainter.Antialiasing)
                self.canv.scene().render(pai)
                pai.end()
                im.save(fn)
                num += 1
        self.rerun()
        
    def rerun(self):
        self.canv.resetGrid()
        for k in range(0, self.acts.count()):
            it = self.acts.item(k)
            s = it.data(Qt.DisplayRole)
            mo = self.canv.interpreter.interpret(s)
            mo(self.canv.grid)
        self.canv.scene().clear()
        self.canv.placeInScene()
        self.canv.update()
        
    def selectall(self):
        for k in range(0, self.acts.count()):
            self.acts.item(k).setCheckState(Qt.Checked)
        
    def unselectall(self):
        for k in range(0, self.acts.count()):
            self.acts.item(k).setCheckState(Qt.Unchecked)
        
    def clearList(self):
        self.canv.listReset([])
        self.acts.clear()
    
    def animation_frame(self):
        if self.frame == self.acts.count():
            self.canv.resetGrid()
            self.canv.scene().clear()
            self.canv.placeInScene()
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
        self.frame =(self.frame+1)
        
    def start_playing(self):
        if self.acts.count() > 0:
            self.frame = self.acts.count()
            self.inte.setDisabled(True)
            self.canv.setAcceptDrops(False)
            self.play.setDisabled(True)
            self.acts.setDisabled(True)
            self.canv.scene().clear()
            self.canv.placeInScene()
            self.canv.update()
            self.animation_timer.start(int(self.speed.text()))
        pass
    
    def stop_playing(self):
        self.inte.setEnabled(True)
        self.play.setEnabled(True)
        self.canv.setAcceptDrops(True)
        self.acts.setEnabled(True)
        self.animation_timer.stop()
        self.rerun()
        pass
        
    def __init__(self):
        super(FiniteGeometryEditor, self).__init__()
        self.frame = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animation_frame)
        self.canv = Canvas(Grid(),self.animation_timer, self)
        
        self.setWindowTitle("Finite Geometry App")
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
        self.canv.interpretMove.connect(self.canv.textFromInterpreter)
        # self.canv.moveAccepted.connect(lambda : self.play.setEnabled(True))
        self.acts.resetAllAndRerun.connect(self.canv.listReset)
        
        
        la = QVBoxLayout()
        self.clear = QPushButton("Clear")
        self.sel_all = QPushButton("Select all")
        self.unsel_all = QPushButton("Unselect all")
        self.print = QPushButton("Print")
        self.print.pressed.connect(self.printall)
        self.sel_all.pressed.connect(self.selectall)
        self.unsel_all.pressed.connect(self.unselectall)
        self.clear.pressed.connect(self.clearList)
        bug = QHBoxLayout()
        for k in [self.clear, self.sel_all, self.unsel_all, self.print]:
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
        for k in [self.play, self.stop, self.speed]:
            ctrls.addWidget(k)
        
        
        la.addWidget(self.acts)
        la.addLayout(ctrls)
        la.addLayout(bug)
        wi = QWidget()
        wi.setLayout(la)
        for title, item, pos in [
                  ("Symmetries"       , self.symm, Qt.LeftDockWidgetArea),
                  ("Actions performed", wi, Qt.RightDockWidgetArea),
                  ("Initial element"  , self.decl, Qt.BottomDockWidgetArea),
                  ("Interpreter"      , self.inte, Qt.BottomDockWidgetArea)]:
            dock = QDockWidget(title, self)
            dock.setWidget(item)
            item.setParent(dock)
            dock.setFeatures(QDockWidget.DockWidgetFloatable| QDockWidget.DockWidgetMovable)
            self.addDockWidget(pos, dock)
        

if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    mw = FiniteGeometryEditor()
    
    mw.show()
    sys.exit(app.exec_())