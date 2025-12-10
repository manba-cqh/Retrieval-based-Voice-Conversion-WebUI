"""用户协议弹窗"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class AgreementDialog(QDialog):
    """用户协议对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.countdown_seconds = 1
        self.init_ui()
        self.start_countdown()
    
    def init_ui(self):
        """初始化UI"""
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(40, 40, 40, 250);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("使用协议")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 协议内容
        agreement_text = QTextEdit()
        agreement_text.setReadOnly(True)
        agreement_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: #cccccc;
                font-size: 12px;
                padding: 10px;
            }
        """)
        
        # 设置协议内容
        content = """
1. 引言
欢迎使用布丁Ai变声软件!在使用本软件前,请您仔细阅读并理解本用户协议。一旦您下载、安装或使用本软件,即表示您同意遵守本协议的所有条款。

2. 软件使用许可
(1)本软件授予您非独占、不可转让的使用许可,仅供个人非商业用途。
(2)您不得对软件进行反向工程、反编译或试图以任何方式发现软件的源代码。

3. 用户行为规范
(1)用户不得利用本软件进行任何违法或不当行为,包括但不限于传播非法、诈骗、侵犯他人版权或其他知识产权的内容。
(2)用户应当遵守所有适用的本地、国家及国际法律法规。对于用户通过软件进行的任何行为及其结果,用户应当独立承担全部责任。

4. 免责声明
(1)用户明确同意其使用本软件所存在的风险将完全由其自己承担;因其使用软件而产生的一切后果也由其自己承担。
(2)本软件不对用户使用软件的行为及其结果承担责任。若用户的行为导致第三方损害的,用户应当独立承担责任;若因此给软件开发者或其关联方造成损失的,用户还应负责赔偿。
        """
        agreement_text.setPlainText(content.strip())
        layout.addWidget(agreement_text)
        
        # 关闭按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("1s后可关闭")
        self.close_btn.setEnabled(False)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #cccccc;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-size: 14px;
            }
            QPushButton:enabled {
                background-color: #8b5cf6;
                color: white;
            }
            QPushButton:enabled:hover {
                background-color: #7c3aed;
            }
            QPushButton:enabled:pressed {
                background-color: #6d28d9;
            }
        """)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def start_countdown(self):
        """开始倒计时"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)  # 每秒更新一次
        self.update_countdown()
    
    def update_countdown(self):
        """更新倒计时"""
        if self.countdown_seconds > 0:
            self.close_btn.setText(f"{self.countdown_seconds}s后可关闭")
            self.countdown_seconds -= 1
        else:
            self.timer.stop()
            self.close_btn.setText("关闭")
            self.close_btn.setEnabled(True)

