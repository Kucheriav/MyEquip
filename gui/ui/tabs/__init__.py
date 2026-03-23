from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout


class BaseTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def create_form_group(self, title):
        group = QGroupBox(title)
        layout = QFormLayout()
        group.setLayout(layout)
        return group