import sys
import pandas as pd
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Load dataset
df = pd.read_csv("Telco Customer Churn.csv")

# Categorical columns suitable for pie charts
categorical_cols = [
    'gender','SeniorCitizen','Partner','Dependents','PhoneService','MultipleLines',
    'InternetService','OnlineSecurity','OnlineBackup','DeviceProtection','TechSupport',
    'StreamingTV','StreamingMovies','Contract','PaperlessBilling','PaymentMethod'
]

# Prettier column names
column_mapping = {
    'SeniorCitizen': 'Senior Citizen',
    'Partner': 'Has Partner',
    'Dependents': 'Has Dependents',
    'PaperlessBilling': 'Paperless Billing'
}

# Value mapping for prettier labels
value_mapping = {
    'SeniorCitizen': {0: 'Young', 1: 'Old'},
    'Partner': {'Yes': 'Yes', 'No': 'No'},
    'Dependents': {'Yes': 'Yes', 'No': 'No'}
}

def prettify_labels(index, selected_cols):
    """Create human-friendly labels for group combinations."""
    labels = []
    for idx in index:
        if not isinstance(idx, tuple):
            idx = (idx,)
        parts = []
        for col, val in zip(selected_cols, idx):
            col_name = column_mapping.get(col, col)
            if col in value_mapping and val in value_mapping[col]:
                parts.append(f"{col_name}={value_mapping[col][val]}")
            else:
                parts.append(f"{col_name}={val}")
        labels.append(", ".join(parts))
    return labels

class PieChartApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telco Customer Churn Explorer")
        self.setGeometry(200, 200, 1150, 800)

        layout = QVBoxLayout()

        # Multi-select list with checkboxes
        self.list_widget = QListWidget()
        for col in categorical_cols:
            item = QListWidgetItem(col)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
        layout.addWidget(QLabel("Select one or more categorical columns:"))
        layout.addWidget(self.list_widget)

        # Button to show charts
        self.button = QPushButton("Show Pie Charts")
        self.button.clicked.connect(self.plot_pie)
        layout.addWidget(self.button)

        # Matplotlib canvas
        self.canvas = FigureCanvas(plt.Figure(figsize=(12,6)))
        layout.addWidget(self.canvas)

        # Table for stats
        self.table = QTableWidget()
        font = QFont()
        font.setPointSize(12)   # Larger font
        self.table.setFont(font)
        self.table.setMinimumHeight(300)
        layout.addWidget(self.table)

        self.setLayout(layout)

        # Store wedges for highlighting
        self.wedges_all = []
        self.wedges_churn = []

        # Connect table click to highlight
        self.table.cellClicked.connect(self.highlight_slice)

    def plot_pie(self):
        """Generate pie charts and churn statistics table."""
        # Collect selected columns
        selected_cols = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_cols.append(item.text())

        if not selected_cols:
            QMessageBox.information(self, "Selection required", "Please select at least one categorical column.")
            return

        # Clear previous figure
        self.canvas.figure.clear()
        ax1, ax2 = self.canvas.figure.subplots(1, 2)

        # Count all customers
        all_counts = df.groupby(selected_cols).size()

        # Count churned customers and align with all_counts
        churn_counts = df[df['Churn'] == 'Yes'].groupby(selected_cols).size()
        churn_counts = churn_counts.reindex(all_counts.index, fill_value=0)

        # Build prettier labels
        labels = prettify_labels(all_counts.index, selected_cols)

        # Colors (balanced palette)
        colors = plt.cm.tab20.colors

        # Pie chart: All customers
        self.wedges_all, _ = ax1.pie(all_counts.values, startangle=90, colors=colors[:len(all_counts)])
        ax1.set_title("Total")
        ax1.axis('equal')

        # Pie chart: Churned customers
        self.wedges_churn, _ = ax2.pie(churn_counts.values, startangle=90, colors=colors[:len(all_counts)])
        ax2.set_title("Churn")
        ax2.axis('equal')

        self.canvas.figure.tight_layout()
        self.canvas.draw()

        # Build stats table
        rows = []
        total_customers = all_counts.sum()
        churned_customers = churn_counts.sum()
        for idx, total_val in zip(all_counts.index, all_counts.values):
            churn_val = churn_counts[idx]
            total_dist = total_val / total_customers * 100
            churn_dist = churn_val / churned_customers * 100 if churned_customers > 0 else 0
            churn_ratio = churn_val / total_val if total_val > 0 else 0
            label = prettify_labels([idx], selected_cols)[0]
            rows.append([
                label,
                total_val,
                f"{total_dist:.2f}%",
                churn_val,
                f"{churn_dist:.2f}%",
                f"{churn_ratio:.2f}"
            ])

        stats_df = pd.DataFrame(rows, columns=[
            "Clustering", "Total people", "Total distribution",
            "Churn people", "Churn distribution", "Churn Ratio"
        ]).sort_values(by="Total people", ascending=False)

        # Fill QTableWidget with colored rows
        self.table.setRowCount(len(stats_df))
        self.table.setColumnCount(len(stats_df.columns))
        self.table.setHorizontalHeaderLabels(stats_df.columns)

        for r in range(len(stats_df)):
            # Get the same color as the pie slice
            row_color = colors[r % len(colors)]
            qcolor = QColor(int(row_color[0]*255), int(row_color[1]*255), int(row_color[2]*255))

            for c in range(len(stats_df.columns)):
                item = QTableWidgetItem(str(stats_df.iloc[r, c]))
                item.setBackground(qcolor)  # Apply background color
                self.table.setItem(r, c, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def highlight_slice(self, row, col):
        """Highlight the selected slice in both charts when a table row is clicked."""
        # Reset all wedges
        for w in self.wedges_all + self.wedges_churn:
            w.set_radius(1.0)

        # Highlight the selected row's slice
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