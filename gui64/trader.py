import socket
import json
import threading
import time
from enum import Enum
from rsi import RSICalculator


class OrderType(Enum):
    """주문 타입"""
    BUY = "01"
    SELL = "02"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class AutoTrader:
    """자동매매 엔진"""
    
    def __init__(self, server_host='127.0.0.1', server_port=9999):
        self.server_host = server_host
        self.server_port = server_port
        self.server_socket = None
        self.connected = False
        
        self.rsi_calculator = RSICalculator()
        self.running = False
        
        # 설정
        self.config = {
            'rsi_period': 14,
            'overbought': 70,
            'oversold': 30,
            'buy_qty': 1,  # 매수 수량
            'sell_qty': 1,  # 매도 수량
        }
        
        # 거래 기록
        self.trades = []
        self.orders = {}  # {order_id: order_info}
        
        # 상태
        self.positions = {}  # {stock_code: qty}
        self.account_info = {}

    def connect(self):
        """32비트 서버에 연결"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.server_host, self.server_port))
            self.connected = True
            print("[Trader] 서버 연결 성공")
            return True
        except Exception as e:
            print(f"[Trader] 서버 연결 실패: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """서버 연결 종료"""
        if self.server_socket:
            self.server_socket.close()
        self.connected = False
        print("[Trader] 서버 연결 종료")

    def send_request(self, action, params=None):
        """
        요청 전송
        
        Args:
            action: 요청 액션
            params: 추가 파라미터
        
        Returns:
            응답 데이터
        """
        if not self.connected:
            return {'status': 'error', 'message': '서버 미연결'}
        
        try:
            request = {
                'action': action,
                'params': params or {}
            }
            
            self.server_socket.send(json.dumps(request).encode('utf-8'))
            response = self.server_socket.recv(4096).decode('utf-8')
            
            return json.loads(response)
        
        except Exception as e:
            print(f"[Trader] 요청 실패: {e}")
            return {'status': 'error', 'message': str(e)}

    def buy(self, stock_code, qty, price):
        """
        매수 주문
        
        Args:
            stock_code: 종목코드
            qty: 수량
            price: 가격
        
        Returns:
            주문 정보
        """
        if not self.connected:
            return {'status': 'error', 'message': '서버 미연결'}
        
        order = {
            'type': OrderType.BUY.value,
            'code': stock_code,
            'qty': qty,
            'price': price,
            'timestamp': time.time()
        }
        
        response = self.send_request('place_order', order)
        
        if response.get('status') == 'success':
            order_id = response.get('order_id')
            self.orders[order_id] = order
            self.trades.append({
                'order_id': order_id,
                'type': 'buy',
                'code': stock_code,
                'qty': qty,
                'price': price,
                'timestamp': time.time()
            })
            print(f"[Trader] 매수 주문 성공: {stock_code} {qty}주 @ {price}원")
        else:
            print(f"[Trader] 매수 주문 실패: {response.get('message')}")
        
        return response

    def sell(self, stock_code, qty, price):
        """
        매도 주문
        
        Args:
            stock_code: 종목코드
            qty: 수량
            price: 가격
        
        Returns:
            주문 정보
        """
        if not self.connected:
            return {'status': 'error', 'message': '서버 미연결'}
        
        order = {
            'type': OrderType.SELL.value,
            'code': stock_code,
            'qty': qty,
            'price': price,
            'timestamp': time.time()
        }
        
        response = self.send_request('place_order', order)
        
        if response.get('status') == 'success':
            order_id = response.get('order_id')
            self.orders[order_id] = order
            self.trades.append({
                'order_id': order_id,
                'type': 'sell',
                'code': stock_code,
                'qty': qty,
                'price': price,
                'timestamp': time.time()
            })
            print(f"[Trader] 매도 주문 성공: {stock_code} {qty}주 @ {price}원")
        else:
            print(f"[Trader] 매도 주문 실패: {response.get('message')}")
        
        return response

    def analyze_rsi(self, prices):
        """
        RSI 분석
        
        Args:
            prices: 가격 데이터 (리스트)
        
        Returns:
            {'rsi': float, 'signal': str}
        """
        rsi = self.rsi_calculator.calculate_rsi(
            prices,
            period=self.config['rsi_period']
        )
        
        signal = self.rsi_calculator.get_signal(
            rsi,
            overbought=self.config['overbought'],
            oversold=self.config['oversold']
        )
        
        return {
            'rsi': rsi,
            'signal': signal
        }

    def execute_trade(self, stock_code, prices, current_price):
        """
        자동매매 실행
        
        Args:
            stock_code: 종목코드
            prices: 가격 히스토리 (리스트)
            current_price: 현재 가격
        
        Returns:
            주문 정보 또는 None
        """
        if len(prices) < self.config['rsi_period']:
            return None
        
        # RSI 분석
        analysis = self.analyze_rsi(prices)
        rsi = analysis['rsi']
        signal = analysis['signal']
        
        if signal == 'buy':
            # 현재 포지션이 없을 때만 매수
            if self.positions.get(stock_code, 0) == 0:
                return self.buy(
                    stock_code,
                    self.config['buy_qty'],
                    current_price
                )
        
        elif signal == 'sell':
            # 현재 포지션이 있을 때만 매도
            if self.positions.get(stock_code, 0) > 0:
                return self.sell(
                    stock_code,
                    self.config['sell_qty'],
                    current_price
                )
        
        return None

    def update_position(self, stock_code, qty, operation='add'):
        """
        포지션 업데이트
        
        Args:
            stock_code: 종목코드
            qty: 수량
            operation: 'add' 또는 'subtract'
        """
        current_qty = self.positions.get(stock_code, 0)
        
        if operation == 'add':
            self.positions[stock_code] = current_qty + qty
        elif operation == 'subtract':
            self.positions[stock_code] = max(0, current_qty - qty)
        
        print(f"[Position] {stock_code}: {self.positions[stock_code]}주")

    def get_trade_history(self):
        """거래 기록 반환"""
        return self.trades

    def get_orders(self):
        """주문 정보 반환"""
        return self.orders

    def update_config(self, config_dict):
        """
        설정 업데이트
        
        Args:
            config_dict: 설정 딕셔너리
        """
        self.config.update(config_dict)
        print(f"[Trader] 설정 업데이트: {self.config}")

    def start(self):
        """자동매매 시작"""
        self.running = True
        print("[Trader] 자동매매 시작")

    def stop(self):
        """자동매매 중지"""
        self.running = False
        print("[Trader] 자동매매 중지")


if __name__ == "__main__":
    trader = AutoTrader()
    
    # 테스트 데이터
    test_prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113]
    
    # RSI 분석
    analysis = trader.analyze_rsi(test_prices)
    print(f"RSI: {analysis['rsi']:.2f}")
    print(f"Signal: {analysis['signal']}")
