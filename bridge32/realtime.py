import threading
import time
import json
from collections import deque
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop


class RealtimeDataManager(QObject):
    """실시간 데이터 수신 관리"""
    
    # 신호
    data_updated = pyqtSignal(dict)  # 실시간 데이터 업데이트
    chart_data_updated = pyqtSignal(dict)  # 차트 데이터 업데이트
    
    def __init__(self, kiwoom):
        super().__init__()
        self.kiwoom = kiwoom
        self.running = False
        
        # 실시간 데이터 저장소
        self.realtime_data = {}
        self.chart_data = {}
        self.data_lock = threading.Lock()
        
        # 캔들 데이터 (4시간봉)
        self.candle_data = deque(maxlen=100)
        
        # 이벤트 루프 (블로킹 호출용)
        self.tr_loop = QEventLoop()
        
        # 키움증권 API 신호 연결
        self.kiwoom.OnReceiveRealData.connect(self.on_receive_realtime)
        self.kiwoom.OnReceiveChejanData.connect(self.on_receive_chejan)

    def subscribe_realtime(self, stock_code):
        """
        실시간 시세 구독
        
        Args:
            stock_code: 종목코드 (예: "005930")
        """
        screen_no = "2000"
        
        # 실시간 시세 신청
        self.kiwoom.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            screen_no,
            stock_code,
            "10;11;12;13;14;15;16;27;28;29;30",  # 요청 데이터
            "1"
        )
        
        print(f"[Realtime] {stock_code} 실시간 구독 시작")

    def unsubscribe_realtime(self, stock_code):
        """
        실시간 시세 구독 해제
        
        Args:
            stock_code: 종목코드
        """
        screen_no = "2000"
        
        self.kiwoom.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            screen_no,
            stock_code,
            "",
            "2"
        )
        
        print(f"[Realtime] {stock_code} 실시간 구독 해제")

    def on_receive_realtime(self, code, real_type, real_data):
        """
        실시간 시세 수신
        
        Args:
            code: 종목코드
            real_type: 시세 타입 (HOLOSESQUE, REALTIME, etc)
            real_data: 실시간 데이터
        """
        try:
            # 현재가
            current_price = int(
                self.kiwoom.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    real_type,
                    code,
                    0,
                    "현재가"
                ) or 0
            )
            
            # 거래량
            volume = int(
                self.kiwoom.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    real_type,
                    code,
                    0,
                    "거래량"
                ) or 0
            )
            
            # 고가
            high_price = int(
                self.kiwoom.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    real_type,
                    code,
                    0,
                    "고가"
                ) or 0
            )
            
            # 저가
            low_price = int(
                self.kiwoom.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    real_type,
                    code,
                    0,
                    "저가"
                ) or 0
            )
            
            with self.data_lock:
                self.realtime_data[code] = {
                    'price': current_price,
                    'volume': volume,
                    'high': high_price,
                    'low': low_price,
                    'timestamp': time.time()
                }
            
            # 신호 발신
            self.data_updated.emit({
                'code': code,
                'price': current_price,
                'volume': volume,
                'high': high_price,
                'low': low_price
            })
            
            print(f"[Realtime] {code}: {current_price}원, 거래량: {volume}")
            
        except Exception as e:
            print(f"[Realtime] 데이터 처리 에러: {e}")

    def on_receive_chejan(self, gubun, item_cnt, fid_list):
        """
        체잔 데이터 수신 (주문/잔고 변동)
        
        Args:
            gubun: 구분 (0: 주문, 1: 잔고)
            item_cnt: 아이템 개수
            fid_list: FID 리스트
        """
        if gubun == "0":  # 주문
            self._process_order_data()
        elif gubun == "1":  # 잔고
            self._process_balance_data()

    def _process_order_data(self):
        """주문 데이터 처리"""
        try:
            order_status = self.kiwoom.dynamicCall("GetChejanData(int)", 9203)
            order_qty = self.kiwoom.dynamicCall("GetChejanData(int)", 901)
            order_price = self.kiwoom.dynamicCall("GetChejanData(int)", 902)
            
            print(f"[Order] 상태: {order_status}, 수량: {order_qty}, 가격: {order_price}")
            
        except Exception as e:
            print(f"[Order] 처리 에러: {e}")

    def _process_balance_data(self):
        """잔고 데이터 처리"""
        try:
            account = self.kiwoom.dynamicCall("GetChejanData(int)", 9001)
            qty = self.kiwoom.dynamicCall("GetChejanData(int)", 930)
            price = self.kiwoom.dynamicCall("GetChejanData(int)", 931)
            
            print(f"[Balance] 종목: {account}, 수량: {qty}, 가격: {price}")
            
        except Exception as e:
            print(f"[Balance] 처리 에러: {e}")

    def request_minute_data(self, stock_code, minutes=5):
        """
        분봉 데이터 요청
        
        Args:
            stock_code: 종목코드
            minutes: 분 단위 (1, 5, 10, 15, 30, 60, 240 등)
        """
        screen_no = "3000"
        
        # 입력값 설정
        self.kiwoom.dynamicCall(
            "SetInputValue(QString, QString)",
            "종목코드",
            stock_code
        )
        
        self.kiwoom.dynamicCall(
            "SetInputValue(QString, QString)",
            "틱범위",
            str(minutes)
        )
        
        # 요청
        self.kiwoom.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            f"분봉조회_{stock_code}",
            "opt10080",
            0,
            screen_no
        )

    def get_realtime_price(self, stock_code):
        """
        현재 실시간 가격 조회
        
        Args:
            stock_code: 종목코드
        
        Returns:
            {'price': int, 'volume': int, ...} or None
        """
        with self.data_lock:
            return self.realtime_data.get(stock_code)

    def start(self):
        """데이터 수집 시작"""
        self.running = True
        print("[Realtime] 실시간 데이터 수집 시작")

    def stop(self):
        """데이터 수집 중지"""
        self.running = False
        print("[Realtime] 실시간 데이터 수집 중지")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from kiwoom import Kiwoom
    import sys
    
    app = QApplication(sys.argv)
    
    kiwoom = Kiwoom()
    manager = RealtimeDataManager(kiwoom)
    
    kiwoom.login()
    kiwoom.get_account()
    
    # 삼성전자 실시간 구독
    manager.subscribe_realtime("005930")
    manager.start()
    
    # 10초 후 종료
    import time
    time.sleep(10)
    
    manager.stop()
    manager.unsubscribe_realtime("005930")
    
    sys.exit(app.exec_())
