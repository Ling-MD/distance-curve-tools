#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Curve Editor (Full v1.2)
- Fix: uses Qt eventFilter to capture mouse press/move/release reliably on all pyqtgraph versions.
- Drag a point; neighbors deform via Gaussian/Cosine kernel.
- Open/Save CSV & XVG; Undo/Redo; Y clamp; controls panel.
Dependencies:
    pip install PyQt5 pyqtgraph numpy pandas
Run:
    python curve_editor_full_v1_2.py
"""

import sys, os
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QEvent
import pyqtgraph as pg


def read_xvg(path):
    headers = []
    x, y = [], []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith(("#", "@")):
                headers.append(line.rstrip("\n"))
            else:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        x.append(float(parts[0])); y.append(float(parts[1]))
                    except:
                        pass
    if not x:
        raise ValueError("No numeric data found in XVG.")
    return np.array(x, dtype=float), np.array(y, dtype=float), headers


def write_xvg(path, x, y, headers=None, title="edited"):
    with open(path, "w", encoding="utf-8") as f:
        if headers:
            for h in headers:
                f.write(h + "\n")
        else:
            f.write(f"@    title \"{title}\"\n@TYPE xy\n")
        for xi, yi in zip(x, y):
            f.write(f"{xi:.6f} {yi:.6f}\n")


def read_csv_xy(path):
    df = pd.read_csv(path)
    cols = list(df.columns)
    if {"Time_ns", "Distance_A"}.issubset(cols):
        x = df["Time_ns"].to_numpy(dtype=float)
        y = df["Distance_A"].to_numpy(dtype=float)
    else:
        num_cols = [c for c in cols if np.issubdtype(df[c].dtype, np.number)]
        if len(num_cols) < 2:
            raise ValueError("CSV requires at least two numeric columns.")
        x = df[num_cols[0]].to_numpy(dtype=float)
        y = df[num_cols[1]].to_numpy(dtype=float)
    return x, y


def write_csv_xy(path, x, y):
    pd.DataFrame({"Time_ns": x, "Distance_A": y}).to_csv(path, index=False)


def gaussian_kernel(n_points, sigma):
    idx = np.arange(n_points)
    c = (n_points - 1) / 2.0
    w = np.exp(-0.5 * ((idx - c) / max(sigma, 1e-6)) ** 2)
    w /= (np.max(w) + 1e-12)
    return w


def cosine_kernel(n_points):
    idx = np.arange(n_points)
    w = 0.5 * (1 - np.cos(2 * np.pi * idx / max(n_points - 1, 1)))
    w /= (np.max(w) + 1e-12)
    return w


class CurveEditor(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Curve Editor – drag points with neighborhood influence (v1.2)")
        self.resize(1180, 760)

        # data
        self.x = None
        self.y = None
        self.headers = None
        self.file_path = None

        # drag state
        self.drag_active = False
        self.drag_index = None
        self.drag_y0 = None
        self.y_at_drag_start = None

        # undo/redo
        self.undo_stack = []
        self.redo_stack = []

        # params
        self.neighbor_count = 100
        self.kernel_type = "Gaussian"
        self.kernel_sigma = 20
        self.strength = 1.0
        self.ymin = 0.0
        self.ymax = 30.0
        self.snap_x = True
        self.show_markers = True
        self.pick_radius_px = 12  # picking threshold in pixels

        self._init_ui()

    def _init_ui(self):
        cw = QtWidgets.QWidget(); self.setCentralWidget(cw)
        vbox = QtWidgets.QVBoxLayout(cw)

        # toolbar
        tb = QtWidgets.QToolBar(); self.addToolBar(tb)
        act_open = QtWidgets.QAction("Open", self); act_open.triggered.connect(self.on_open)
        act_save = QtWidgets.QAction("Save As", self); act_save.triggered.connect(self.on_save_as)
        act_undo = QtWidgets.QAction("Undo", self); act_undo.triggered.connect(self.on_undo)
        act_redo = QtWidgets.QAction("Redo", self); act_redo.triggered.connect(self.on_redo)
        tb.addAction(act_open); tb.addAction(act_save); tb.addSeparator(); tb.addAction(act_undo); tb.addAction(act_redo)

        # controls
        ctrl = QtWidgets.QHBoxLayout()
        def add(label, w): ctrl.addWidget(QtWidgets.QLabel(label)); ctrl.addWidget(w)

        self.sb_neighbors = QtWidgets.QSpinBox(); self.sb_neighbors.setRange(1, 200000); self.sb_neighbors.setValue(self.neighbor_count); self.sb_neighbors.valueChanged.connect(self.on_param_change)
        self.cb_kernel = QtWidgets.QComboBox(); self.cb_kernel.addItems(["Gaussian","Cosine"]); self.cb_kernel.currentTextChanged.connect(self.on_param_change)
        self.sb_sigma = QtWidgets.QDoubleSpinBox(); self.sb_sigma.setDecimals(1); self.sb_sigma.setRange(1.0, 1e6); self.sb_sigma.setValue(self.kernel_sigma); self.sb_sigma.valueChanged.connect(self.on_param_change)
        self.sb_strength = QtWidgets.QDoubleSpinBox(); self.sb_strength.setDecimals(2); self.sb_strength.setRange(0.01, 10.0); self.sb_strength.setValue(self.strength); self.sb_strength.valueChanged.connect(self.on_param_change)
        self.sb_ymin = QtWidgets.QDoubleSpinBox(); self.sb_ymin.setDecimals(2); self.sb_ymin.setRange(-1e9,1e9); self.sb_ymin.setValue(self.ymin); self.sb_ymin.setPrefix("Ymin="); self.sb_ymin.valueChanged.connect(self.on_param_change)
        self.sb_ymax = QtWidgets.QDoubleSpinBox(); self.sb_ymax.setDecimals(2); self.sb_ymax.setRange(-1e9,1e9); self.sb_ymax.setValue(self.ymax); self.sb_ymax.setPrefix("Ymax="); self.sb_ymax.valueChanged.connect(self.on_param_change)
        self.cb_snapx = QtWidgets.QCheckBox("Snap X"); self.cb_snapx.setChecked(self.snap_x); self.cb_snapx.stateChanged.connect(self.on_param_change)
        self.cb_markers = QtWidgets.QCheckBox("Show points"); self.cb_markers.setChecked(self.show_markers); self.cb_markers.stateChanged.connect(self.on_param_change)

        add("Neighbors", self.sb_neighbors); add("Kernel", self.cb_kernel); add("Sigma", self.sb_sigma); add("Strength", self.sb_strength)
        ctrl.addSpacing(16); ctrl.addWidget(self.cb_snapx); ctrl.addWidget(self.cb_markers); ctrl.addSpacing(16); ctrl.addWidget(self.sb_ymin); ctrl.addWidget(self.sb_ymax); ctrl.addStretch(1)
        vbox.addLayout(ctrl)

        # plot
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setLabel("bottom", "Time (ns)")
        self.plot.setLabel("left", "Distance (Å)")
        vbox.addWidget(self.plot)

        # disable default pan/menu
        vb = self.plot.getViewBox()
        vb.setMouseEnabled(x=False, y=False)
        vb.setMenuEnabled(False)

        # items
        self.curve = self.plot.plot(pen=pg.mkPen((10,10,10), width=2))
        self.scatter = pg.ScatterPlotItem(size=7, pen=pg.mkPen(None), brush=pg.mkBrush(50,120,200,200))
        self.scatter.setZValue(10)
        self.plot.addItem(self.scatter)

        # Install Qt event filter to capture press/move/release robustly
        self.plot.scene().installEventFilter(self)

        # shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self, activated=self.on_undo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self, activated=self.on_redo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self.on_save_as)
        QtWidgets.QShortcut(QtGui.QKeySequence("O"), self, activated=self.on_open)

        pg.setConfigOptions(antialias=True)
        self.update_plot()

    # ---------- file ops ----------
    def on_open(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open CSV or XVG", "", "Data Files (*.csv *.xvg);;All Files (*)")
        if not path: return
        try:
            if path.lower().endswith(".xvg"):
                x, y, headers = read_xvg(path); self.headers = headers
            else:
                x, y = read_csv_xy(path); self.headers = None
            order = np.argsort(x)
            self.x = x[order]; self.y = y[order]
            self.file_path = path
            self.undo_stack.clear(); self.redo_stack.clear()
            self.update_plot(rescale=True)
            self.statusBar().showMessage(f"Loaded: {os.path.basename(path)} (N={len(self.x)})", 6000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open Error", str(e))

    def on_save_as(self):
        if self.x is None: return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As", "", "XVG (*.xvg);;CSV (*.csv)")
        if not path: return
        try:
            if path.lower().endswith(".xvg"):
                write_xvg(path, self.x, self.y, headers=self.headers)
            else:
                write_csv_xy(path, self.x, self.y)
            self.statusBar().showMessage(f"Saved: {os.path.basename(path)}", 6000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Error", str(e))

    # ---------- undo/redo ----------
    def push_undo(self):
        if self.x is None: return
        self.undo_stack.append(self.y.copy())
        if len(self.undo_stack) > 200: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def on_undo(self):
        if not self.undo_stack or self.x is None: return
        self.redo_stack.append(self.y.copy())
        self.y = self.undo_stack.pop()
        self.update_plot()

    def on_redo(self):
        if not self.redo_stack or self.x is None: return
        self.undo_stack.append(self.y.copy())
        self.y = self.redo_stack.pop()
        self.update_plot()

    # ---------- params ----------
    def on_param_change(self):
        self.neighbor_count = int(self.sb_neighbors.value())
        self.kernel_type = self.cb_kernel.currentText()
        self.kernel_sigma = float(self.sb_sigma.value())
        self.strength = float(self.sb_strength.value())
        self.ymin = float(self.sb_ymin.value())
        self.ymax = float(self.sb_ymax.value())
        self.snap_x = self.cb_snapx.isChecked()
        self.show_markers = self.cb_markers.isChecked()
        self.update_plot()

    # ---------- plot ----------
    def update_plot(self, rescale=False):
        if self.x is None:
            self.curve.setData([], []); self.scatter.setData([]); return
        self.curve.setData(self.x, self.y)
        if self.show_markers:
            self.scatter.setData(self.x, self.y); self.scatter.setVisible(True)
        else:
            self.scatter.setVisible(False)
        if rescale:
            self.plot.enableAutoRange()
        self.plot.setYRange(self.ymin, self.ymax, padding=0.05)

    # ---------- utils ----------
    def scene_to_data(self, scene_pos):
        vb = self.plot.getViewBox()
        return vb.mapSceneToView(scene_pos)

    def nearest_index(self, mx, my, pixel_tol=12):
        """Find nearest point by X first; ensure within pixel tolerance from cursor."""
        if self.x is None: return None
        vb = self.plot.getViewBox()
        # compute pixel distance to candidate points (only x-nearest triplet)
        idx = np.searchsorted(self.x, mx)
        cand = [j for j in (idx-1, idx, idx+1) if 0 <= j < len(self.x)]
        if not cand: return None
        best, best_pix = None, 1e9
        for j in cand:
            p = QtCore.QPointF(self.x[j], self.y[j])
            sp = vb.mapViewToScene(p)
            dist = (sp.x() - self.last_scene_pos.x())**2 + (sp.y() - self.last_scene_pos.y())**2
            if dist < best_pix:
                best_pix = dist; best = j
        if (best_pix**0.5) <= pixel_tol:
            return best
        return None

    # ---------- event filter (core fix) ----------
    def eventFilter(self, obj, ev):
        if obj is self.plot.scene():
            if ev.type() == QEvent.GraphicsSceneMousePress:
                # record position for pixel-distance pick
                self.last_scene_pos = ev.scenePos()
                if self.x is None: return True
                v = self.scene_to_data(self.last_scene_pos)
                idx = self.nearest_index(v.x(), v.y(), pixel_tol=self.pick_radius_px)
                if idx is None:
                    self.drag_active = False
                    return True  # eat event to avoid panning
                # start drag on left button only
                if ev.button() == QtCore.Qt.LeftButton:
                    self.drag_active = True
                    self.drag_index = idx
                    self.drag_y0 = float(self.y[idx])
                    self.y_at_drag_start = self.y.copy()
                    self.push_undo()
                return True  # eat event

            elif ev.type() == QEvent.GraphicsSceneMouseMove:
                self.last_scene_pos = ev.scenePos()
                if not self.drag_active or self.x is None:
                    return True
                v = self.scene_to_data(self.last_scene_pos)
                idx0 = self.drag_index
                if idx0 is None: return True
                target_y = float(np.clip(v.y(), self.ymin, self.ymax))
                delta = (target_y - self.drag_y0) * self.strength

                y_new = self.y_at_drag_start.copy()
                n = max(1, int(self.neighbor_count))
                half = n // 2
                i0 = max(0, idx0 - half)
                i1 = min(len(y_new), idx0 + half + 1)
                m = i1 - i0
                if m > 0:
                    if self.kernel_type == "Gaussian":
                        w = gaussian_kernel(m, sigma=self.kernel_sigma)
                    else:
                        w = cosine_kernel(m)
                    y_new[i0:i1] = y_new[i0:i1] + delta * w
                    y_new[i0:i1] = np.clip(y_new[i0:i1], self.ymin, self.ymax)
                    self.y = y_new
                    self.update_plot()
                return True  # eat event

            elif ev.type() == QEvent.GraphicsSceneMouseRelease:
                self.last_scene_pos = ev.scenePos()
                # end drag
                self.drag_active = False
                self.drag_index = None
                self.drag_y0 = None
                self.y_at_drag_start = None
                return True  # eat event
        return super().eventFilter(obj, ev)


def main():
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    w = CurveEditor()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
