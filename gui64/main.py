import sys
import os
import json
import socket
import threading
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTextEdit,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont

from rsi import RSICalculator
from chart import ChartDrawer


class ServerConnector(QObject):
    """서버 통신 클래스"""
    
    status_changed = pyqtSignal(str)
    data_received = pyqtSignal(dict)
    
    def __init__(self, host='127.0.0.1', port=9999):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

    def connect(self):
        """32비트 서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.status_changed.emit("✓ 서버 연결됨")
            return True
        except Exception as e:
            self.connected = False
            self.status_changed.emit(f"✗ 연결 실패: {e}")
            return False

    def send_request(self, action):
        """요청 전송"""
        if not self.connected:
            return False
        
        try:
            request = json.dumps({"action": action})
            self.socket.send(request.encode('utf-8'))
            
            # 응답 수신
            response = self.socket.recv(1024).decode('utf-8')
            data = json.loads(response)
            self.data_received.emit(data)
            return True
        except Exception as e:
            self.status_changed.emit(f"✗ 요청 실패: {e}")
            return False

    def disconnect(self):
        """연결 종료"""
        if self.socket:
            self.socket.close()
        self.connected = False


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Kiwoom 자동매매 - Dirk Hartig RSI")
        self.resize(1600, 1000)
        
        self.server = ServerConnector()
        self.server.status_changed.connect(self.on_status_changed)
        self.server.data_received.connect(self.on_data_received)
        
        self.rsi_calculator = RSICalculator()
        self.chart_drawer = ChartDrawer()

        # 메인 레이아웃
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()

        # ========== 좌측 패널 ==========
        left_layout = QVBoxLayout()
        
        # 상태 표시
        status_group = QGroupBox("연결 상태")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("✗ 연결 안됨")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)
        
        # 계좌 정보
        account_group = QGroupBox("계좌 정보")
        account_layout = QGridLayout()
        
        self.account_label = QLabel("계좌: 없음")
        self.total_assets_label = QLabel("총자산: 0원")
        self.total_profit_label = QLabel("총손익: 0원")
        self.profit_rate_label = QLabel("수익률: 0%")
        
        for label in [self.account_label, self.total_assets_label, self.total_profit_label, self.profit_rate_label]:
            label.setFont(QFont("Arial", 10))
        
        account_layout.addWidget(self.account_label, 0, 0)
        account_layout.addWidget(self.total_assets_label, 1, 0)
        account_layout.addWidget(self.total_profit_label, 2, 0)
        account_layout.addWidget(self.profit_rate_label, 3, 0)
        
        account_group.setLayout(account_layout)
        left_layout.addWidget(account_group)
        
        # RSI 설정
        rsi_group = QGroupBox("RSI 설정")
        rsi_layout = QGridLayout()
        
        rsi_layout.addWidget(QLabel("기간:"), 0, 0)
        self.rsi_period_spinbox = QSpinBox()
        self.rsi_period_spinbox.setValue(14)
        self.rsi_period_spinbox.setMinimum(1)
        self.rsi_period_spinbox.setMaximum(50)
        rsi_layout.addWidget(self.rsi_period_spinbox, 0, 1)
        
        rsi_layout.addWidget(QLabel("과매수:"), 1, 0)
        self.overbought_spinbox = QSpinBox()
        self.overbought_spinbox.setValue(70)
        self.overbought_spinbox.setMinimum(50)
        self.overbought_spinbox.setMaximum(100)
        rsi_layout.addWidget(self.overbought_spinbox, 1, 1)
        
        rsi_layout.addWidget(QLabel("과매도:"), 2, 0)
        self.oversold_spinbox = QSpinBox()
        self.oversold_spinbox.setValue(30)
        self.oversold_spinbox.setMinimum(0)
        self.oversold_spinbox.setMaximum(50)
        rsi_layout.addWidget(self.oversold_spinbox, 2, 1)
        
        rsi_group.setLayout(rsi_layout)
        left_layout.addWidget(rsi_group)
        
        # 현재 신호
        signal_group = QGroupBox("현재 신호")
        signal_layout = QVBoxLayout()
        
        self.signal_label = QLabel("신호: 대기중")
        self.signal_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.signal_label.setAlignment(Qt.AlignCenter)
        self.signal_label.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        
        self.rsi_value_label = QLabel("RSI: -")
        self.rsi_value_label.setFont(QFont("Arial", 11))
        
        signal_layout.addWidget(self.signal_label)
        signal_layout.addWidget(self.rsi_value_label)
        signal_group.setLayout(signal_layout)
        left_layout.addWidget(signal_group)
        
        # 버튼
        button_layout = QVBoxLayout()
        
        self.connect_button = QPushButton("서버 연결")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        button_layout.addWidget(self.connect_button)
        
        self.start_button = QPushButton("자동매매 시작")
        self.start_button.clicked.connect(self.on_start_clicked)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("자동매매 중지")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        left_layout.addLayout(button_layout)
        left_layout.addStretch()
        
        # ========== 중앙 패널 ==========
        center_layout = QVBoxLayout()
        
        # 차트 (임시 표시)
        self.chart_label = QLabel("차트 영역 (4시간봉)")
        self.chart_label.setStyleSheet("background-color: #e0e0e0; border: 1px solid #999;")
        self.chart_label.setMinimumHeight(600)
        self.chart_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.chart_label)
        
        # ========== 우측 패널 ==========
        right_layout = QVBoxLayout()
        
        # 보유종목
        holdings_group = QGroupBox("보유종목")
        holdings_layout = QVBoxLayout()
        
        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(6)
        self.holdings_table.setHorizontalHeaderLabels([
            "종목명", "수량", "평단", "현재가", "손익", "수익률"
        ])
        self.holdings_table.setMaximumHeight(250)
        holdings_layout.addWidget(self.holdings_table)
        holdings_group.setLayout(holdings_layout)
        right_layout.addWidget(holdings_group)
        
        # 거래 기록
        log_group = QGroupBox("거래 기록")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(350)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # ========== 전체 레이아웃 구성 ==========
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(center_layout, 2)
        main_layout.addLayout(right_layout, 1)
        
        central_widget.setLayout(main_layout)
        
        self.log("프로그램 시작")

    def log(self, msg):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")

    def on_status_changed(self, status):
        """상태 변경"""
        self.status_label.setText(status)

    def on_data_received(self, data):
        """데이터 수신"""
        if data.get('status') == 'success':
            self.log(data.get('message', '성공'))
        else:
            self.log(f"에러: {data.get('message', '알 수 없는 에러')}")

    def on_connect_clicked(self):
        """서버 연결 버튼"""
        if not self.server.connected:
            if self.server.connect():
                self.connect_button.setEnabled(False)
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(True)
                self.log("서버 연결 성공")
                
                # 초기 데이터 요청
                self.server.send_request('login')
                self.server.send_request('get_balance')
        else:
            self.server.disconnect()
            self.connect_button.setEnabled(True)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.log("서버 연결 종료")

    def on_start_clicked(self):
        """자동매매 시작"""
        self.log("자동매매 시작")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_stop_clicked(self):
        """자동매매 중지"""
        self.log("자동매매 중지")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
