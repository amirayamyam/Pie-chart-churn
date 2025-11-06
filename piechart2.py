import sys
import pandas as pd
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QListWidget, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

df = pd.read_csv("Telco-Customer-Churn.csv")

categorical_cols = [
    'gender','SeniorCitizen','Partner','Dependents','PhoneService','MultipleLines',
    'InternetService','OnlineSecurity','OnlineBackup','DeviceProtection','TechSupport',
    'StreamingTV','StreamingMovies','Contract','PaperlessBilling','PaymentMethod'
]

column_mapping = {
    'SeniorCitizen': 'Age Group',
    'Partner': 'Has Partner',
    'Dependents': 'Has Dependents',
    'PaperlessBilling': 'Paperless Billing'
}

value_mapping = {
    "SeniorCitizen": {0: "Young", 1: "Old"},
    "Partner": {"Yes": "Has Partner", "No": "No Partner"},
    "Dependents": {"Yes": "Has Dependents", "No": "No Dependents"},
    "PaperlessBilling": {"Yes": "Paperless", "No": "Paper"}
}

def prettify_value(col, val):
    if col in value_mapping and val in value_mapping[col]:
        return value_mapping[col][val]
    return val

def prettify_labels(index, selected_cols):
    labels = []
    for idx in index:
        if not isinstance(idx, tuple):
            idx = (idx,)
        parts = []
        for col, val in zip(selected_cols, idx):
            col_name = column_mapping.get(col, col)
            parts.append(f"{col_name}={prettify_value(col, val)}")
        labels.append(", ".join(parts))
    return labels

class PieChartApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telco Customer Churn Explorer")
        self.setGeometry(200, 200, 1200, 800)

        layout = QVBoxLayout()

        self.summary_label = QLabel("Summary will appear here")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.summary_label.setFont(font)
        self.summary_label.setStyleSheet("color: navy;")
        layout.addWidget(self.summary_label)

        self.list_widget = QListWidget()
        for col in categorical_cols:
            item = QListWidgetItem(col)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)

        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setWidget(self.list_widget)

        self.listwidget_detail = QListWidget()
        scroll_right = QScrollArea()
        scroll_right.setWidgetResizable(True)
        scroll_right.setWidget(self.listwidget_detail)

        hbox = QHBoxLayout()
        hbox.addWidget(scroll_left, 1)
        hbox.addWidget(scroll_right, 1)

        layout.addWidget(QLabel("Select categorical columns (left) and filter values (right):"))
        layout.addLayout(hbox)

        self.button = QPushButton("Show Pie Charts")
        self.button.clicked.connect(self.plot_pie)
        layout.addWidget(self.button)

        self.canvas = FigureCanvas(plt.figure(figsize=(12,6)))
        layout.addWidget(self.canvas)

        self.table = QTableWidget()
        font = QFont()
        font.setPointSize(12)
        self.table.setFont(font)
        self.table.setMinimumHeight(300)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.wedges_all = []
        self.wedges_churn = []

        self.table.cellClicked.connect(self.highlight_slice)
        self.list_widget.itemChanged.connect(self.update_detail_list)

    def update_detail_list(self):
        self.listwidget_detail.clear()
        selected_cols = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_cols.append(item.text())
        if not selected_cols:
            return
        for col in selected_cols:
            uniques = df[col].unique()
            self.listwidget_detail.addItem(f"--- {col} ---")
            for val in uniques:
                pretty_val = prettify_value(col, val)
                item = QListWidgetItem(f"{col} = {pretty_val}")
                item.setCheckState(Qt.CheckState.Checked)
                self.listwidget_detail.addItem(item)

    def get_selected_filters(self):
        filters = {}
        for i in range(self.listwidget_detail.count()):
            text = self.listwidget_detail.item(i).text()
            if text.startswith("---"):
                continue
            if self.listwidget_detail.item(i).checkState() == Qt.CheckState.Checked:
                col, val = text.split(" = ", 1)
                filters.setdefault(col, []).append(val)
        return filters

    def plot_pie(self):
        filters = self.get_selected_filters()
        if not filters:
            QMessageBox.information(self, "Selection required", "Please select at least one column and value.")
            return
        df_filtered = df.copy()
        for col, vals in filters.items():
            reverse_map = {v: k for k, v in value_mapping.get(col, {}).items()}
            raw_vals = [reverse_map.get(v, v) for v in vals]
            df_filtered = df_filtered[df_filtered[col].isin(raw_vals)]
        selected_cols = list(filters.keys())

        total_customers = df.shape[0]
        total_churned = df[df["Churn"] == "Yes"].shape[0]
        filtered_total = df_filtered.shape[0]
        filtered_churn = df_filtered[df_filtered["Churn"] == "Yes"].shape[0]
        ratio_filtered_to_all = (filtered_total / total_customers) * 100 if total_customers > 0 else 0
        ratio_churn_filtered_to_allchurn = (filtered_churn / total_churned) * 100 if total_churned > 0 else 0

        summary_text = (
            f"📊 Filtered Total: {filtered_total}   |   "
            f"🔥 Filtered Churn: {filtered_churn}   |   "
            f"👥 All Total: {total_customers}   |   "
            f"⚠️ All Churn: {total_churned}\n"
            f"✅ % Filtered/All: {ratio_filtered_to_all:.2f}%   |   "
            f"⚡ % Filtered Churn/All Churn: {ratio_churn_filtered_to_allchurn:.2f}%"
        )
        self.summary_label.setText(summary_text)

        self.canvas.figure.clear()
        ax1, ax2 = self.canvas.figure.subplots(1, 2)
        all_counts = df_filtered.groupby(selected_cols).size()
        churn_counts = df_filtered[df_filtered["Churn"] == "Yes"].groupby(selected_cols).size()
        churn_counts = churn_counts.reindex(all_counts.index, fill_value=0)
        labels = prettify_labels(all_counts.index, selected_cols)
        colors = plt.cm.tab20.colors
        self.wedges_all, _ = ax1.pie(all_counts.values, startangle=90, colors=colors[:len(all_counts)])
        ax1.set_title("Total")
        ax1.axis("equal")
        self.wedges_churn, _ = ax2.pie(churn_counts.values, startangle=90, colors=colors[:len(all_counts)])
        ax2.set_title("Churn")
        ax2.axis("equal")
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        rows = []
        total_customers_f = all_counts.sum()
        churned_customers_f = churn_counts.sum()
        for idx, total_val in zip(all_counts.index, all_counts.values):
            churn_val = churn_counts[idx]
            total_dist = (total_val / total_customers_f) * 100
            churn_dist = (churn_val / churned_customers_f) * 100 if churned_customers_f > 0 else 0
            churn_ratio = (churn_val / total_val) * 100 if total_val > 0 else 0
            label = prettify_labels([idx], selected_cols)[0]
            rows.append([
                label,
                total_val,
                f"{total_dist:.2f}%",
                churn_val,
                f"{churn_dist:.2f}%",
                f"{churn_ratio:.2f}%"
            ])
        stats_df = pd.DataFrame(rows, columns=[
            "Clustering", "Total people", "Total distribution",
            "Churn people", "Churn distribution", "Churn Ratio"
        ]).sort_values(by="Churn Ratio", ascending=False)
        self.table.setRowCount(len(stats_df))
        self.table.setColumnCount(len(stats_df.columns))
        self.table.setHorizontalHeaderLabels(stats_df.columns)
        for r in range(len(stats_df)):
            row_color = colors[r % len(colors)]
            qcolor = QColor(int(row_color[0]*255), int(row_color[1]*255), int(row_color[2]*255))
            for c in range(len(stats_df.columns)):
                item = QTableWidgetItem(str(stats_df.iloc[r, c]))
                item.setBackground(qcolor)
                self.table.setItem(r, c, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def highlight_slice(self, row, col):
            for w in self.wedges_all + self.wedges_churn:
                w.set_radius(1.0)
            if row < len(self.wedges_all):
                self.wedges_all[row].set_radius(1.1)
            if row < len(self.wedges_churn):
                self.wedges_churn[row].set_radius(1.1)
            self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PieChartApp()
    window.show()
    sys.exit(app.exec())