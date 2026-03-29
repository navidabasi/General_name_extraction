"""
Advanced output column selection widget.

Features:
- Collapsible "Advanced Options" section (collapsed by default)
- Tag-style selection (no checkboxes)
- Drag-and-drop ordering for selected tags
- Responsive layout (horizontal on wide windows, vertical on narrow)
- Scrollable content for small window heights
- Local persistence for selected tag order
"""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from utils.output_columns import (
    canonicalize_column_name,
    dedupe_preserve_order,
    PURPLE_HIGHLIGHT_OUTPUT_COLUMNS,
    reconcile_selected_columns,
)


class AdvancedColumnSelectorWidget(QWidget):
    """
    Collapsible advanced widget to select and order output columns.

    External contract:
    - `expand_requested` is emitted when user tries to expand.
      Parent should validate prerequisites, then call `set_expanded(True)`.
    - `set_available_columns(...)` injects dynamic selectable columns.
    - `set_selected_columns(...)` sets selected order.
    - `get_selected_columns_in_ui_order()` returns strict selected order.
    """

    expand_requested = pyqtSignal()
    selection_changed = pyqtSignal(list)

    SETTINGS_SELECTED_COLUMNS_KEY = "advanced_output_columns/selected_columns"

    STACK_THRESHOLD_WIDTH = 680

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self._available_columns: list[str] = []
        self._saved_selected_columns: list[str] = []
        self._expanded = False
        self._building_ui = False
        self._init_ui()
        self._restore_saved_selection_only()
        self._set_expanded(False)

    def _init_ui(self):
        self._building_ui = True

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.toggle_button = QToolButton()
        self.toggle_button.setText("Advanced Options")
        self.toggle_button.setCheckable(False)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.clicked.connect(self._on_toggle_clicked)
        self.toggle_button.setStyleSheet(
            """
            QToolButton {
                border: none;
                background: transparent;
                color: #9CA3AF;
                font-size: 12px;
                font-weight: 500;
                padding: 2px 0px;
                text-align: left;
            }
            QToolButton:hover {
                color: #6B7280;
            }
            """
        )
        layout.addWidget(self.toggle_button)

        self.content_container = QWidget()
        self.content_container.setObjectName("advancedContentContainer")
        self.content_container.setVisible(False)
        self.content_container.setStyleSheet(
            """
            QWidget#advancedContentContainer {
                background-color: #F9FAFB;
                border: none;
            }
            """
        )

        content_container_layout = QVBoxLayout()
        content_container_layout.setContentsMargins(0, 0, 0, 0)
        content_container_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        self.helper_text = QLabel(
            "Select tags to include in the extracted file. "
            "Drag selected tags to reorder output columns."
        )
        self.helper_text.setWordWrap(True)
        self.helper_text.setStyleSheet(
            """
            QLabel {
                color: #6B7280;
                font-size: 11px;
                background-color: transparent;
                border: none;
            }
            """
        )
        content_layout.addWidget(self.helper_text)

        self.lists_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.lists_layout.setSpacing(10)

        self.available_container = QWidget()
        self.available_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        available_layout = QVBoxLayout()
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.setSpacing(6)

        available_label = QLabel("Available Tags")
        available_label.setStyleSheet(
            """
            QLabel {
                color: #4B5563;
                font-size: 12px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }
            """
        )
        available_layout.addWidget(available_label)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.available_list.setMinimumHeight(150)
        self.available_list.itemClicked.connect(self._on_available_item_clicked)
        self.available_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_tag_list_style(self.available_list)
        available_layout.addWidget(self.available_list)
        self.available_container.setLayout(available_layout)

        self.selected_container = QWidget()
        self.selected_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        selected_layout = QVBoxLayout()
        selected_layout.setContentsMargins(0, 0, 0, 0)
        selected_layout.setSpacing(6)

        selected_label = QLabel("Selected Tags (Drag To Reorder)")
        selected_label.setStyleSheet(
            """
            QLabel {
                color: #4B5563;
                font-size: 12px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }
            """
        )
        selected_layout.addWidget(selected_label)

        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.selected_list.setMinimumHeight(150)
        self.selected_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.selected_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.selected_list.setDragEnabled(True)
        self.selected_list.setAcceptDrops(True)
        self.selected_list.setDropIndicatorShown(True)
        self.selected_list.itemDoubleClicked.connect(self._on_selected_item_double_clicked)
        self.selected_list.model().rowsMoved.connect(self._on_selected_rows_moved)
        self.selected_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_tag_list_style(self.selected_list)
        selected_layout.addWidget(self.selected_list)
        self.selected_container.setLayout(selected_layout)

        self.lists_layout.addWidget(self.available_container)
        self.lists_layout.addWidget(self.selected_container)
        content_layout.addLayout(self.lists_layout)

        self.secondary_help = QLabel("Tip: Double-click a selected tag to remove it.")
        self.secondary_help.setStyleSheet(
            """
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                background-color: transparent;
                border: none;
            }
            """
        )
        content_layout.addWidget(self.secondary_help)

        self.content_widget.setLayout(content_layout)
        self.scroll_area.setWidget(self.content_widget)
        content_container_layout.addWidget(self.scroll_area)
        self.content_container.setLayout(content_container_layout)
        layout.addWidget(self.content_container)
        self.setLayout(layout)

        self._building_ui = False
        self._refresh_layout_direction()

    @staticmethod
    def _apply_tag_list_style(list_widget: QListWidget):
        list_widget.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background: #FFFFFF;
                padding: 4px;
                font-size: 12px;
                color: #1F2937;
            }
            QListWidget::item {
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                background: #F3F4F6;
                padding: 6px 8px;
                margin: 3px;
            }
            QListWidget::item:selected {
                background: #EEEAFE;
                border-color: #C7B8F5;
                color: #4B3C9A;
            }
            """
        )

    def _restore_saved_selection_only(self):
        saved_selected = self.settings.value(self.SETTINGS_SELECTED_COLUMNS_KEY, [])
        self._saved_selected_columns = self._coerce_settings_columns(saved_selected)
        # Available columns are unknown until a Ventrata file is loaded.
        self._populate_lists([], [])

    @staticmethod
    def _coerce_settings_columns(raw_value) -> list[str]:
        if isinstance(raw_value, list):
            values = raw_value
        elif isinstance(raw_value, tuple):
            values = list(raw_value)
        elif isinstance(raw_value, str):
            stripped = raw_value.strip()
            if not stripped:
                return []
            values = [part.strip() for part in stripped.split(",") if part.strip()]
        else:
            values = []

        canonical = []
        for value in values:
            canonical_name = canonicalize_column_name(str(value))
            if canonical_name:
                canonical.append(canonical_name)
        return dedupe_preserve_order(canonical)

    def _on_toggle_clicked(self):
        if self._expanded:
            self._set_expanded(False)
        else:
            self.expand_requested.emit()

    def set_expanded(self, expanded: bool):
        self._set_expanded(bool(expanded))

    def _set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        self.content_container.setVisible(self._expanded)
        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if self._expanded else Qt.ArrowType.RightArrow
        )

    def is_expanded(self) -> bool:
        return self._expanded

    def set_available_columns(
        self,
        available_columns: Iterable[str],
        preserve_user_order: bool = True,
        persist: bool = True,
    ):
        canonical_available = []
        for column_name in available_columns:
            canonical_name = canonicalize_column_name(column_name)
            if canonical_name:
                canonical_available.append(canonical_name)
        canonical_available = dedupe_preserve_order(canonical_available)
        self._available_columns = canonical_available

        current_selected = self.get_selected_columns_in_ui_order()
        if not current_selected and self._saved_selected_columns:
            current_selected = list(self._saved_selected_columns)
        if preserve_user_order:
            reconciled = reconcile_selected_columns(current_selected, self._available_columns)
        else:
            reconciled = list(self._available_columns)
        self.set_selected_columns(reconciled, persist=persist)

    def get_available_columns(self) -> list[str]:
        return list(self._available_columns)

    def set_selected_columns(self, selected_columns: Iterable[str], persist: bool = True):
        canonical_selected = []
        for column_name in selected_columns:
            canonical_name = canonicalize_column_name(column_name)
            if canonical_name:
                canonical_selected.append(canonical_name)
        canonical_selected = dedupe_preserve_order(canonical_selected)
        self._saved_selected_columns = list(canonical_selected)

        if self._available_columns:
            selected_set = set(canonical_selected)
            selected_in_available = [col for col in canonical_selected if col in self._available_columns]
            remaining_available = [col for col in self._available_columns if col not in selected_set]
            if not selected_in_available:
                selected_in_available = list(self._available_columns)
                remaining_available = []
            selected_columns_final = selected_in_available
            available_columns_final = remaining_available
        else:
            selected_columns_final = []
            available_columns_final = []

        self._populate_lists(available_columns_final, selected_columns_final)
        if persist:
            self._persist_selected()
            self.selection_changed.emit(self.get_selected_columns_in_ui_order())

    def _populate_lists(self, available_columns: Iterable[str], selected_columns: Iterable[str]):
        self.available_list.clear()
        for column_name in available_columns:
            self.available_list.addItem(self._build_item(column_name))

        self.selected_list.clear()
        for column_name in selected_columns:
            self.selected_list.addItem(self._build_item(column_name))

    @staticmethod
    def _build_item(column_name: str) -> QListWidgetItem:
        item = QListWidgetItem(column_name)
        item.setData(Qt.ItemDataRole.UserRole, column_name)
        if column_name in PURPLE_HIGHLIGHT_OUTPUT_COLUMNS:
            item.setForeground(QColor("#5B5FC7"))
            item.setToolTip("Core extracted/mandatory column")
        return item

    def _on_available_item_clicked(self, item: QListWidgetItem):
        column_name = item.data(Qt.ItemDataRole.UserRole)
        if not column_name:
            return

        current_selected = self.get_selected_columns_in_ui_order()
        if column_name in current_selected:
            return
        current_selected.append(column_name)
        self.set_selected_columns(current_selected, persist=True)

    def _on_selected_item_double_clicked(self, item: QListWidgetItem):
        column_name = item.data(Qt.ItemDataRole.UserRole)
        if not column_name:
            return

        current_selected = self.get_selected_columns_in_ui_order()
        if column_name not in current_selected:
            return
        current_selected.remove(column_name)
        self.set_selected_columns(current_selected, persist=True)

    def _on_selected_rows_moved(self, *_):
        if self._building_ui:
            return
        self._persist_selected()
        self.selection_changed.emit(self.get_selected_columns_in_ui_order())

    def _persist_selected(self):
        selected_columns = self.get_selected_columns_in_ui_order()
        self._saved_selected_columns = list(selected_columns)
        self.settings.setValue(self.SETTINGS_SELECTED_COLUMNS_KEY, selected_columns)

    def get_selected_columns_in_ui_order(self) -> list[str]:
        columns = []
        for index in range(self.selected_list.count()):
            item = self.selected_list.item(index)
            column_name = item.data(Qt.ItemDataRole.UserRole) or item.text()
            canonical_name = canonicalize_column_name(str(column_name))
            if canonical_name:
                columns.append(canonical_name)
        return dedupe_preserve_order(columns)

    # Backward-compatible alias for callers that still use old method name.
    def get_selected_columns(self) -> list[str]:
        return self.get_selected_columns_in_ui_order()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_layout_direction()

    def _refresh_layout_direction(self):
        direction = (
            QBoxLayout.Direction.TopToBottom
            if self.width() < self.STACK_THRESHOLD_WIDTH
            else QBoxLayout.Direction.LeftToRight
        )
        if self.lists_layout.direction() != direction:
            self.lists_layout.setDirection(direction)
