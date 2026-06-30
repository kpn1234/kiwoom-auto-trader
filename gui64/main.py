import sys
import os
import json
import socket
import threading
import time
from datetime import datetime
from collections import deque

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
    QSpinBox,
    QGridLayout,
    QGroupBox,
    QComboBox,
    QMessageBox,
    QTabWidget,
    QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QColor, QFont, QBrush

from chart import ChartWidget
from rsi import RSICalculator
from trader import AutoTrader


class DataCollector(QThread):
    """실시간 데이터 수집 스레드"""
    
    data_collected = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, trader, stock_codes, interval=1):
        super().__init__()
        self.trader = trader
        self.stock_codes = stock_codes
        self.interval = interval
        self.running = False
        
        # 가격 히스토리 저장소 (최대 100개)
        self.price_history = {code: deque(maxlen=100) for code in stock_codes}

    def run(self):
        """스레드 실행"""
        self.running = True
        
        while self.running:
            try:
                for stock_code in self.stock_codes:
                    # 실제 환경에서는 키움증권 API에서 가격을 받아옴
                    # 여기서는 테스트를 위해 임의의 값 사용
                    price_data = self._fetch_price(stock_code)
                    
                    if price_data:
                        self.price_history[stock_code].append(price_data['price'])
                        
                        self.data_collected.emit({
                            'code': stock_code,
                            'price': price_data['price'],
                            'history': list(self.price_history[stock_code])
                        })
                
                time.sleep(self.interval)
            
            except Exception as e:
                self.error_occurred.emit(f"데이터 수집 에러: {str(e)}")

    def _fetch_price(self, stock_code):
        """가격 데이터 조회 (테스트용)"""
        # 실제로는 키움증권 API 호출
        try:
            # 시뮬레이션 데이터
            import random
            price = 50000 + random.randint(-1000, 1000)
            
            return {
                'code': stock_code,
                'price': price,
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"[DataCollector] 에러: {e}")
            return None

    def stop(self):
        """스레드 종료"""
        self.running = False
        self.wait()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Kiwoom 자동매매 - Dirk Hartig RSI Strategy")
        self.resize(1800, 1000)
        
        self.trader = AutoTrader()
        self.rsi_calculator = RSICalculator()
        self.data_collector = None
        
        # 선택된 종목
        self.selected_stock = "005930"  # 삼성전자
        self.stock_codes = ["005930", "000660", "068270"]  # 삼성전자, SK하이닉스, 셀트리온
        
        # UI 구성
        self.init_ui()
        
        # 타이머 (주기적 업데이트)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1초마다 업데이트

    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()

        # ========== 좌측 패널 ==========
        left_widget = self.create_left_panel()
        
        # ========== 중앙 패널 ==========
        center_widget = self.create_center_panel()
        
        # ========== 우측 패널 ==========
        right_widget = self.create_right_panel()
        
        # 레이아웃 구성
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(center_widget, 2)
        main_layout.addWidget(right_widget, 1)
        
        central_widget.setLayout(main_layout)

    def create_left_panel(self):
        """좌측 패널 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # ===== 연결 상태 =====
        status_group = QGroupBox("연결 상태")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("✗ 서버 미연결")
        self.status_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.status_label.setStyleSheet("color: red;")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # ===== 계좌 정보 =====
        account_group = QGroupBox("계좌 정보")
        account_layout = QGridLayout()
        
        self.account_label = QLabel("계좌: -")
        self.balance_label = QLabel("잔액: 0원")
        self.profit_label = QLabel("손익: 0원")
        self.rate_label = QLabel("수익률: 0%")
        
        for label in [self.account_label, self.balance_label, self.profit_label, self.rate_label]:
            label.setFont(QFont("Arial", 9))
        
        account_layout.addWidget(QLabel("계좌:"), 0, 0)
        account_layout.addWidget(self.account_label, 0, 1)
        account_layout.addWidget(QLabel("잔액:"), 1, 0)
        account_layout.addWidget(self.balance_label, 1, 1)
        account_layout.addWidget(QLabel("손익:"), 2, 0)
        account_layout.addWidget(self.profit_label, 2, 1)
        account_layout.addWidget(QLabel("수익률:"), 3, 0)
        account_layout.addWidget(self.rate_label, 3, 1)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)

        # ===== 종목 선택 =====
        stock_group = QGroupBox("종목 선택")
        stock_layout = QVBoxLayout()
        
        self.stock_combo = QComboBox()
        self.stock_combo.addItems(["005930", "000660", "068270"])
        self.stock_combo.currentTextChanged.connect(self.on_stock_selected)
        stock_layout.addWidget(QLabel("선택 종목:"))
        stock_layout.addWidget(self.stock_combo)
        
        stock_group.setLayout(stock_layout)
        layout.addWidget(stock_group)

        # ===== RSI 설정 =====
        rsi_group = QGroupBox("RSI 설정")
        rsi_layout = QGridLayout()
        
        rsi_layout.addWidget(QLabel("기간:"), 0, 0)
        self.rsi_period = QSpinBox()
        self.rsi_period.setValue(14)
        self.rsi_period.setMinimum(1)
        self.rsi_period.setMaximum(50)
        self.rsi_period.valueChanged.connect(self.on_rsi_config_changed)
        rsi_layout.addWidget(self.rsi_period, 0, 1)
        
        rsi_layout.addWidget(QLabel("과매수:"), 1, 0)
        self.overbought = QSpinBox()
        self.overbought.setValue(70)
        self.overbought.setMinimum(50)
        self.overbought.setMaximum(100)
        self.overbought.valueChanged.connect(self.on_rsi_config_changed)
        rsi_layout.addWidget(self.overbought, 1, 1)
        
        rsi_layout.addWidget(QLabel("과매도:"), 2, 0)
        self.oversold = QSpinBox()
        self.oversold.setValue(30)
        self.oversold.setMinimum(0)
        self.oversold.setMaximum(50)
        self.oversold.valueChanged.connect(self.on_rsi_config_changed)
        rsi_layout.addWidget(self.oversold, 2, 1)
        
        rsi_group.setLayout(rsi_layout)
        layout.addWidget(rsi_group)

        # ===== 현재 신호 =====
        signal_group = QGroupBox("현재 신호")
        signal_layout = QVBoxLayout()
        
        self.signal_label = QLabel("신호: 대기중")
        self.signal_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.signal_label.setAlignment(Qt.AlignCenter)
        self.signal_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        
        self.rsi_value_label = QLabel("RSI: -")
        self.rsi_value_label.setFont(QFont("Arial", 10))
        self.rsi_value_label.setAlignment(Qt.AlignCenter)
        
        self.price_label = QLabel("현재가: -")
        self.price_label.setFont(QFont("Arial", 10))
        self.price_label.setAlignment(Qt.AlignCenter)
        
        signal_layout.addWidget(self.rsi_value_label)
        signal_layout.addWidget(self.price_label)
        signal_layout.addWidget(self.signal_label)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group)

        # ===== 버튼 =====
        button_layout = QVBoxLayout()
        
        self.connect_btn = QPushButton("서버 연결")
        self.connect_btn.clicked.connect(self.on_connect)
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.connect_btn)
        
        self.start_btn = QPushButton("자동매매 시작")
        self.start_btn.clicked.connect(self.on_start_trading)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("자동매매 중지")
        self.stop_btn.clicked.connect(self.on_stop_trading)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_center_panel(self):
        """중앙 패널 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 탭 위젯
        self.tabs = QTabWidget()
        
        # 차트 탭
        self.chart_widget = ChartWidget()
        self.tabs.addTab(self.chart_widget, "차트 (4시간봉)")
        
        # 통계 탭
        stats_widget = self.create_stats_tab()
        self.tabs.addTab(stats_widget, "통계")
        
        layout.addWidget(self.tabs)
        widget.setLayout(layout)
        return widget

    def create_stats_tab(self):
        """통계 탭 생성"""
        widget = QWidget()
        layout = QGridLayout()
        
        layout.addWidget(QLabel("총 거래 횟수:"), 0, 0)
        self.total_trades_label = QLabel("0")
        layout.addWidget(self.total_trades_label, 0, 1)
        
        layout.addWidget(QLabel("승리:"), 1, 0)
        self.win_label = QLabel("0")
        layout.addWidget(self.win_label, 1, 1)
        
        layout.addWidget(QLabel("패배:"), 2, 0)
        self.loss_label = QLabel("0")
        layout.addWidget(self.loss_label, 2, 1)
        
        layout.addWidget(QLabel("승률:"), 3, 0)
        self.winrate_label = QLabel("0%")
        layout.addWidget(self.winrate_label, 3, 1)
        
        layout.addWidget(QLabel("수익:"), 4, 0)
        self.profit_sum_label = QLabel("0원")
        layout.addWidget(self.profit_sum_label, 4, 1)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_right_panel(self):
        """우측 패널 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # ===== 보유종목 =====
        holdings_group = QGroupBox("보유종목")
        holdings_layout = QVBoxLayout()
        
        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(5)
        self.holdings_table.setHorizontalHeaderLabels([
            "종목명", "수량", "매입가", "현재가", "손익"
        ])
        self.holdings_table.setMaximumHeight(200)
        holdings_layout.addWidget(self.holdings_table)
        holdings_group.setLayout(holdings_layout)
        layout.addWidget(holdings_group)

        # ===== 거래 기록 =====
        log_group = QGroupBox("거래 기록")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(400)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        widget.setLayout(layout)
        return widget

    def on_stock_selected(self, stock_code):
        """종목 선택"""
        self.selected_stock = stock_code
        self.log(f"종목 변경: {stock_code}")

    def on_rsi_config_changed(self):
        """RSI 설정 변경"""
        self.trader.update_config({
            'rsi_period': self.rsi_period.value(),
            'overbought': self.overbought.value(),
            'oversold': self.oversold.value()
        })

    def on_connect(self):
        """서버 연결"""
        if not self.trader.connected:
            if self.trader.connect():
                self.status_label.setText("✓ 서버 연결됨")
                self.status_label.setStyleSheet("color: green;")
                self.connect_btn.setEnabled(False)
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                self.log("서버 연결 성공")
                
                # 데이터 수집 시작
                self.start_data_collection()
            else:
                self.log("서버 연결 실패")
                QMessageBox.warning(self, "연결 실패", "서버 연결에 실패했습니다.")
        else:
            self.trader.disconnect()
            self.status_label.setText("✗ 서버 미연결")
            self.status_label.setStyleSheet("color: red;")
            self.connect_btn.setEnabled(True)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.log("서버 연결 종료")
            self.stop_data_collection()

    def on_start_trading(self):
        """자동매매 시작"""
        self.trader.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log("🟢 자동매매 시작")

    def on_stop_trading(self):
        """자동매매 중지"""
        self.trader.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log("🔴 자동매매 중지")

    def start_data_collection(self):
        """데이터 수집 시작"""
        self.data_collector = DataCollector(self.trader, self.stock_codes)
        self.data_collector.data_collected.connect(self.on_data_collected)
        self.data_collector.error_occurred.connect(self.on_collection_error)
        self.data_collector.start()

    def stop_data_collection(self):
        """데이터 수집 중지"""
        if self.data_collector:
            self.data_collector.stop()

    def on_data_collected(self, data):
        """데이터 수집"""
        stock_code = data['code']
        price = data['price']
        history = data['history']
        
        if stock_code == self.selected_stock:
            self.price_label.setText(f"현재가: {price:,}원")
            
            # RSI 계산
            if len(history) >= self.rsi_period.value():
                analysis = self.trader.analyze_rsi(history)
                rsi = analysis['rsi']
                signal = analysis['signal']
                
                self.rsi_value_label.setText(f"RSI: {rsi:.2f}")
                
                # 신호 표시
                if signal == 'buy':
                    self.signal_label.setText("신호: 📈 매수")
                    self.signal_label.setStyleSheet("background-color: #c8e6c9; color: green; padding: 10px; border-radius: 5px; font-weight: bold;")
                    
                    # 자동매매 활성화 시 매수 실행
                    if self.trader.running:
                        self.trader.execute_trade(stock_code, history, price)
                
                elif signal == 'sell':
                    self.signal_label.setText("신호: 📉 매도")
                    self.signal_label.setStyleSheet("background-color: #ffcdd2; color: red; padding: 10px; border-radius: 5px; font-weight: bold;")
                    
                    # 자동매매 활성화 시 매도 실행
                    if self.trader.running:
                        self.trader.execute_trade(stock_code, history, price)
                
                else:
                    self.signal_label.setText("신호: ⏸️ 대기")
                    self.signal_label.setStyleSheet("background-color: #f0f0f0; color: gray; padding: 10px; border-radius: 5px;")

    def on_collection_error(self, error):
        """데이터 수집 에러"""
        self.log(f"⚠️ {error}")

    def update_display(self):
        """주기적으로 디스플레이 업데이트"""
        # 거래 기록 업데이트
        trades = self.trader.get_trade_history()
        self.total_trades_label.setText(str(len(trades)))

    def log(self, msg):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
