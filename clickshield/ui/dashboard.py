from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from clickshield.core.history import HistoryStore, ScanRecord
from clickshield.core.scoring import ThreatLevel, classify_severity

logger = logging.getLogger(__name__)

_SEVERITY_COLORS = {
    ThreatLevel.CLEAN:  "#2e7d32",   # green
    ThreatLevel.LOW:    "#f9a825",   # amber
    ThreatLevel.MEDIUM: "#e65100",   # deep orange
    ThreatLevel.HIGH:   "#b71c1c",   # red
}

_COLUMN_HEADERS = ["Time", "Browser", "Severity", "Threat", "URL"]
_COL_TIME, _COL_BROWSER, _COL_SEVERITY, _COL_THREAT, _COL_URL = range(5)


class DashboardWindow(QMainWindow):
    """
    Standalone window showing all scan history.
    Left panel: filterable table of records.
    Right panel: screenshot + full analysis detail for the selected record.
    """

    closed = pyqtSignal()

    def __init__(self, store: HistoryStore, parent: QWidget | None = None):
        super().__init__(parent)
        self._store = store
        self._records: list[ScanRecord] = []
        self._selected: Optional[ScanRecord] = None

        self.setWindowTitle("ClickShield — Scan History")
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)

        self._build_ui()
        self._refresh_table()

        # Auto-refresh every 10 s while open
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_table)
        self._refresh_timer.start(10_000)

    # ------------------------------------------------------------------
    # Build UI

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 4)
        root_layout.setSpacing(6)

        # --- toolbar row ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        title_lbl = QLabel("Scan History")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        toolbar.addWidget(title_lbl)
        toolbar.addStretch()

        filter_lbl = QLabel("Filter:")
        toolbar.addWidget(filter_lbl)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All scans", "Threats only", "High (7–10)", "Medium (4–6)", "Low (1–3)", "Clean (0)"])
        self._filter_combo.currentIndexChanged.connect(self._refresh_table)
        toolbar.addWidget(self._filter_combo)

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self._refresh_table)
        toolbar.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedWidth(90)
        clear_btn.setStyleSheet("color: #b71c1c;")
        clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(clear_btn)

        root_layout.addLayout(toolbar)

        # --- splitter: table | detail ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(_COLUMN_HEADERS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(_COL_TIME, 130)
        self._table.setColumnWidth(_COL_BROWSER, 110)
        self._table.setColumnWidth(_COL_SEVERITY, 75)
        self._table.setColumnWidth(_COL_THREAT, 160)
        self._table.currentCellChanged.connect(self._on_row_selected)
        self._table.setStyleSheet("""
            QTableWidget { font-size: 12px; }
            QHeaderView::section { font-weight: bold; padding: 4px; }
        """)
        splitter.addWidget(self._table)

        # Right: detail panel
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(8, 0, 0, 0)
        detail_layout.setSpacing(8)

        detail_title = QLabel("Scan Detail")
        detail_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        detail_layout.addWidget(detail_title)

        # Screenshot
        self._screenshot_lbl = QLabel()
        self._screenshot_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._screenshot_lbl.setMinimumHeight(200)
        self._screenshot_lbl.setMaximumHeight(280)
        self._screenshot_lbl.setStyleSheet("background: #111; border: 1px solid #333;")
        self._screenshot_lbl.setText("Select a scan to view screenshot")
        self._screenshot_lbl.setStyleSheet(
            "background: #1a1a2e; color: #555; border: 1px solid #333; font-size: 12px;"
        )
        detail_layout.addWidget(self._screenshot_lbl)

        # Metadata labels
        meta_frame = QFrame()
        meta_frame.setStyleSheet("background: #1a1a2e; border: 1px solid #333; border-radius: 4px;")
        meta_layout = QVBoxLayout(meta_frame)
        meta_layout.setContentsMargins(10, 8, 10, 8)
        meta_layout.setSpacing(4)

        self._meta_severity = QLabel("Severity: —")
        self._meta_severity.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        meta_layout.addWidget(self._meta_severity)

        self._meta_url = QLabel("URL: —")
        self._meta_url.setWordWrap(True)
        self._meta_url.setStyleSheet("color: #90caf9; font-size: 11px;")
        meta_layout.addWidget(self._meta_url)

        self._meta_browser = QLabel("Browser: —")
        self._meta_browser.setStyleSheet("color: #b0bec5; font-size: 11px;")
        meta_layout.addWidget(self._meta_browser)

        self._meta_time = QLabel("Time: —")
        self._meta_time.setStyleSheet("color: #b0bec5; font-size: 11px;")
        meta_layout.addWidget(self._meta_time)

        detail_layout.addWidget(meta_frame)

        # Explanation
        expl_lbl = QLabel("Explanation:")
        expl_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        detail_layout.addWidget(expl_lbl)

        self._explanation_edit = QTextEdit()
        self._explanation_edit.setReadOnly(True)
        self._explanation_edit.setMaximumHeight(90)
        self._explanation_edit.setStyleSheet("background: #1a1a2e; color: #e0e0e0; font-size: 12px;")
        detail_layout.addWidget(self._explanation_edit)

        # Indicators
        ind_lbl = QLabel("Indicators:")
        ind_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        detail_layout.addWidget(ind_lbl)

        self._indicators_edit = QTextEdit()
        self._indicators_edit.setReadOnly(True)
        self._indicators_edit.setMaximumHeight(80)
        self._indicators_edit.setStyleSheet("background: #1a1a2e; color: #ffcc80; font-size: 12px;")
        detail_layout.addWidget(self._indicators_edit)

        # Raw model response (collapsed)
        raw_lbl = QLabel("Raw model response:")
        raw_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        detail_layout.addWidget(raw_lbl)

        self._raw_edit = QTextEdit()
        self._raw_edit.setReadOnly(True)
        self._raw_edit.setMaximumHeight(70)
        self._raw_edit.setStyleSheet("background: #111; color: #888; font-family: Consolas; font-size: 10px;")
        detail_layout.addWidget(self._raw_edit)

        detail_layout.addStretch()
        splitter.addWidget(detail_widget)
        splitter.setSizes([600, 500])

        root_layout.addWidget(splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status_bar()

    # ------------------------------------------------------------------
    # Data

    def _filtered_records(self) -> list[ScanRecord]:
        idx = self._filter_combo.currentIndex()
        records = self._store.all()
        if idx == 0:
            return records
        elif idx == 1:   # threats only
            return [r for r in records if r.severity > 0]
        elif idx == 2:   # high
            return [r for r in records if r.severity >= 7]
        elif idx == 3:   # medium
            return [r for r in records if 4 <= r.severity <= 6]
        elif idx == 4:   # low
            return [r for r in records if 1 <= r.severity <= 3]
        else:            # clean
            return [r for r in records if r.severity == 0]

    def _refresh_table(self) -> None:
        self._records = self._filtered_records()

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._records))

        for row, rec in enumerate(self._records):
            level = classify_severity(rec.severity)
            color = _SEVERITY_COLORS.get(level, "#ffffff")

            # Time
            time_item = QTableWidgetItem(rec.datetime_obj.strftime("%m/%d %H:%M:%S"))
            time_item.setData(Qt.ItemDataRole.UserRole, rec)
            self._table.setItem(row, _COL_TIME, time_item)

            # Browser
            self._table.setItem(row, _COL_BROWSER, QTableWidgetItem(rec.browser_name or "—"))

            # Severity
            sev_item = QTableWidgetItem(str(rec.severity))
            sev_item.setForeground(QColor(color))
            sev_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self._table.setItem(row, _COL_SEVERITY, sev_item)

            # Threat type
            threat_item = QTableWidgetItem(rec.threat_type.replace("_", " ").title())
            threat_item.setForeground(QColor(color))
            self._table.setItem(row, _COL_THREAT, threat_item)

            # URL
            self._table.setItem(row, _COL_URL, QTableWidgetItem(rec.url or "—"))

        self._table.setSortingEnabled(True)
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        total = self._store.total_scans
        today = self._store.threats_today
        shown = len(self._records)
        self._status_bar.showMessage(
            f"  Showing {shown} of {total} scans  |  Threats detected today: {today}"
        )

    # ------------------------------------------------------------------
    # Selection

    def _on_row_selected(self, current_row: int, *_) -> None:
        if current_row < 0 or current_row >= len(self._records):
            return
        self._selected = self._records[current_row]
        self._show_detail(self._selected)

    def _show_detail(self, rec: ScanRecord) -> None:
        level = classify_severity(rec.severity)
        color = _SEVERITY_COLORS.get(level, "#ffffff")
        level_name = level.name.capitalize()

        self._meta_severity.setText(f"Severity: {rec.severity}/10  —  {level_name}  ({rec.threat_type.replace('_', ' ').title()})")
        self._meta_severity.setStyleSheet(f"color: {color}; font-size: 13px;")
        self._meta_url.setText(f"URL: {rec.url or 'N/A'}")
        self._meta_browser.setText(f"Browser: {rec.browser_name or 'Unknown'}")
        self._meta_time.setText(f"Time: {rec.datetime_obj.strftime('%Y-%m-%d %H:%M:%S')}")

        self._explanation_edit.setPlainText(rec.explanation)

        if rec.indicators:
            self._indicators_edit.setPlainText("\n".join(f"• {i}" for i in rec.indicators))
        else:
            self._indicators_edit.setPlainText("No specific indicators.")

        self._raw_edit.setPlainText(rec.raw_response or "(none)")

        # Screenshot
        self._load_screenshot(rec)

    def _load_screenshot(self, rec: ScanRecord) -> None:
        path = rec.screenshot_full_path
        if path and path.exists():
            pix = QPixmap(str(path))
            scaled = pix.scaled(
                self._screenshot_lbl.width() - 4,
                self._screenshot_lbl.maximumHeight() - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._screenshot_lbl.setPixmap(scaled)
        else:
            self._screenshot_lbl.setText("No screenshot saved for this scan.")

    # ------------------------------------------------------------------
    # Actions

    def _on_clear(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Delete all scan history and screenshots?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._store.clear()
            self._refresh_table()
            self._screenshot_lbl.setText("No screenshot saved for this scan.")
            self._explanation_edit.clear()
            self._indicators_edit.clear()
            self._raw_edit.clear()

    def add_record(self, record: ScanRecord) -> None:
        """Called from the tray app when a new scan completes."""
        self._refresh_table()

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self.closed.emit()
        super().closeEvent(event)
