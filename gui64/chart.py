import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt


class ChartWidget(QWidget):
    """PyQt5에 통합된 차트 위젯"""
    
    def __init__(self):
        super().__init__()
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.ax_price = None
        self.ax_rsi = None
        self.ax_volume = None

    def draw_candlestick_chart(self, df, rsi_values=None, signals=None, volume=None):
        """
        캔들차트 + RSI + 거래량 표시
        
        Args:
            df: OHLC 데이터 (columns: open, high, low, close, date)
            rsi_values: RSI 값 리스트
            signals: 매매 신호 리스트 ('buy', 'sell', None)
            volume: 거래량 리스트
        """
        self.figure.clear()
        
        if len(df) == 0:
            return
        
        # 3개 서브플롯 생성
        self.ax_price = self.figure.add_subplot(3, 1, (1, 2))
        self.ax_rsi = self.figure.add_subplot(3, 1, 3)
        
        # 캔들차트 그리기
        self._draw_candlestick(df)
        
        # RSI 그리기
        if rsi_values and len(rsi_values) > 0:
            self._draw_rsi(rsi_values)
        
        # 매매 신호 표시
        if signals:
            self._draw_signals(df, signals)
        
        self.figure.tight_layout()
        self.canvas.draw()

    def _draw_candlestick(self, df):
        """캔들차트 그리기"""
        width = 0.6
        
        for i in range(len(df)):
            open_price = df.iloc[i]['open']
            close_price = df.iloc[i]['close']
            high_price = df.iloc[i]['high']
            low_price = df.iloc[i]['low']
            
            # 상승/하강 색상
            if close_price >= open_price:
                color = '#e41a1c'  # 빨강 (상승)
                body_height = close_price - open_price
                body_bottom = open_price
            else:
                color = '#377eb8'  # 파랑 (하강)
                body_height = open_price - close_price
                body_bottom = close_price
            
            # 몸통 (캔들)
            self.ax_price.bar(i, body_height, width, bottom=body_bottom, 
                             color=color, edgecolor=color, linewidth=0.5)
            
            # 심지 (고가-저가)
            self.ax_price.plot([i, i], [low_price, high_price], 
                              color=color, linewidth=1)
        
        self.ax_price.set_xlabel('시간')
        self.ax_price.set_ylabel('가격')
        self.ax_price.set_title('캔들차트 (4시간봉)')
        self.ax_price.grid(True, alpha=0.3)
        self.ax_price.set_xlim(-1, len(df))

    def _draw_rsi(self, rsi_values):
        """RSI 그리기"""
        self.ax_rsi.plot(range(len(rsi_values)), rsi_values, 
                        color='#984ea3', linewidth=2, label='RSI')
        
        # 기준선
        self.ax_rsi.axhline(y=70, color='#e41a1c', linestyle='--', 
                           linewidth=1.5, alpha=0.7, label='과매수 (70)')
        self.ax_rsi.axhline(y=30, color='#377eb8', linestyle='--', 
                           linewidth=1.5, alpha=0.7, label='과매도 (30)')
        
        # 음영
        self.ax_rsi.fill_between(range(len(rsi_values)), 70, 100, 
                                alpha=0.1, color='#e41a1c')
        self.ax_rsi.fill_between(range(len(rsi_values)), 0, 30, 
                                alpha=0.1, color='#377eb8')
        
        self.ax_rsi.set_ylabel('RSI')
        self.ax_rsi.set_ylim([0, 100])
        self.ax_rsi.set_xlim(-1, len(rsi_values))
        self.ax_rsi.grid(True, alpha=0.3)
        self.ax_rsi.legend(loc='upper left', fontsize=9)

    def _draw_signals(self, df, signals):
        """매매 신호 표시"""
        for i, signal in enumerate(signals):
            if i >= len(df):
                break
            
            if signal == 'buy':
                # 매수 신호 (녹색 위쪽 삼각형)
                self.ax_price.scatter(i, df.iloc[i]['low'] * 0.98, 
                                     color='#4daf4a', marker='^', s=200, 
                                     zorder=5, edgecolors='black', linewidth=1)
                self.ax_price.text(i, df.iloc[i]['low'] * 0.95, 'B', 
                                 ha='center', va='top', fontsize=8, 
                                 fontweight='bold', color='#4daf4a')
            
            elif signal == 'sell':
                # 매도 신호 (빨간색 아래쪽 삼각형)
                self.ax_price.scatter(i, df.iloc[i]['high'] * 1.02, 
                                     color='#e41a1c', marker='v', s=200, 
                                     zorder=5, edgecolors='black', linewidth=1)
                self.ax_price.text(i, df.iloc[i]['high'] * 1.05, 'S', 
                                 ha='center', va='bottom', fontsize=8, 
                                 fontweight='bold', color='#e41a1c')

    def update_chart(self, df, rsi_values=None, signals=None):
        """차트 업데이트"""
        self.draw_candlestick_chart(df, rsi_values, signals)


class SimpleLineChart(QWidget):
    """간단한 라인 차트"""
    
    def __init__(self):
        super().__init__()
        self.figure = Figure(figsize=(12, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def draw(self, data, title="Chart", xlabel="Time", ylabel="Value"):
        """라인 차트 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(data, marker='o', linewidth=2, color='#377eb8')
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    # 테스트
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테스트 데이터
    dates = pd.date_range('2024-01-01', periods=50, freq='4H')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(50) * 2)
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': prices + np.abs(np.random.randn(50)),
        'low': prices - np.abs(np.random.randn(50)),
        'close': prices + np.random.randn(50)
    })
    
    # RSI 계산
    from rsi import RSICalculator
    rsi_calc = RSICalculator()
    rsi_values = [rsi_calc.calculate_rsi(df['close'].iloc[:i+1].values) 
                  for i in range(len(df))]
    
    # 신호 생성
    signals = [rsi_calc.get_signal(rsi) if rsi else None for rsi in rsi_values]
    
    # 차트 표시
    widget = ChartWidget()
    widget.draw_candlestick_chart(df, rsi_values, signals)
    widget.show()
    
    sys.exit(app.exec_())
