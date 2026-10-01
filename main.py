import datetime
import os
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import DEFAULT_FONT, LabelBase
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.resources import resource_add_path
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import escape_markup, platform

# Android APIのインポート（Linux上ではエラーになるため、try-exceptで囲む）
try:
    from android.broadcast import BroadcastReceiver  # type: ignore
    from android.permissions import Permission, request_permissions  # type: ignore
    from jnius import PythonJavaClass, autoclass, java_method  # type: ignore

    # Javaクラスのインポート
    String = autoclass('java.lang.String')
    # Androidクラスのインポート
    Intent = autoclass('android.content.Intent')
    IntentFilter = autoclass('android.content.IntentFilter')
    Context = autoclass('android.content.Context')
    Handler = autoclass('android.os.Handler')
    ContextCompat = autoclass('androidx.core.content.ContextCompat')
    # kivyクラスのインポート
    Service = autoclass('org.kivy.android.PythonService')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    currentActivity = PythonActivity.mActivity

except ImportError:
    # Linux環境用のダミー
    class Dummy:
        def __getattr__(self, name): return self
    Intent, LocalBroadcastManager, PythonActivity, currentActivity, Service, IntentFilter = [Dummy()] * 6
    print("Running in desktop environment. Android APIs are mocked.")

# --- UIの定義 ---
class MainScreen(BoxLayout):
    
    # 画面表示用のプロパティを定義
    start_time_str = StringProperty("待機中...")
    counter_str = StringProperty("0")
    expected_time_str = StringProperty("待機中...")
    current_time_str = StringProperty("待機中...")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.broadcast_receiver = None
        self.service_intent = None
        Clock.schedule_once(self.setup_android_and_start_service, 0)

    # データの受け取りとUIの更新
    def update_ui(self, context, intent):
        """ブロードキャストを受信したときに呼び出される"""
        self.log('update_ui START')

        # 届いているすべてのExtra（データ）のキーを確認する
        bundle = intent.getExtras()
        if bundle:
           keys = bundle.keySet().toArray()
           # 型を無視して中身を文字列として強制表示してみる
           for key in keys:
               value = bundle.get(key)
               self.log(f"{key} = {value} {type(value)}")
        else:
           self.log("No extras found in intent")

        # サービスからデータを受け取る
        # 文字列として取り出し、Pythonのintに戻す
        start_time_str = intent.getStringExtra('start_time')
        counter_str = intent.getStringExtra('counter')

        start_time_ts = int(start_time_str) if start_time_str else 0
        counter = int(counter_str) if counter_str else 0

        # 現在時刻を取得
        current_time_ts = int(time.time())

        # 期待される時刻を計算 (サービス開始時刻 + 秒カウンター)
        expected_time_ts = start_time_ts + counter

        # 画面プロパティを更新
        self.start_time_str = time.strftime('%H:%M:%S', time.localtime(start_time_ts))
        self.counter_str = str(counter)
        self.expected_time_str = time.strftime('%H:%M:%S', time.localtime(expected_time_ts))
        self.current_time_str = time.strftime('%H:%M:%S', time.localtime(current_time_ts))

        self.log('update_ui END')

    def start_service(self):
        if platform == 'android':

            # クラス名はマニフェストと完全に一致させる
            service_class_name = 'org.kitagw.my_broadcast_app.ServiceMyservice'
            service_class = autoclass(service_class_name)
            service_intent = Intent(currentActivity, service_class)

            # --- 重要：KivyのPythonService(Java)が内部で必要とする全パス情報を取得 ---
            app_root = currentActivity.getFilesDir().getAbsolutePath() + "/app"
            
            # --- JNIエラー(NULL jstring)を防ぐための7つの必須Extra ---
            service_intent.putExtra(String('androidPrivate'), String(app_root))
            service_intent.putExtra(String('androidArgument'), String(app_root))
            service_intent.putExtra(String('serviceEntrypoint'), String('service/main.py'))
            service_intent.putExtra(String('pythonName'), String('myservice'))
            service_intent.putExtra(String('pythonHome'), String(app_root))
            service_intent.putExtra(String('pythonPath'), String(app_root))
            service_intent.putExtra(String('pythonServiceArgument'), String('')) # 空文字でOK

            # --- ForegroundServiceを動かすための設定 ---
            service_intent.putExtra(String('serviceStartAsForeground'), String('true'))
            service_intent.putExtra(String('serviceTitle'), String('My Service'))
            service_intent.putExtra(String('serviceDescription'), String('Service is running...'))

            # サービスの開始
            currentActivity.startForegroundService(service_intent)

            self.log("Started service with all required JNI extras.")
        else:
            self.log('テスト1')
            self.log('テスト2')
            self.log('テスト3')

    def setup_android_and_start_service(self, dt):
         # すでに起動済みならスキップ
        if not hasattr(self, 'service_started'):
            self.start_service()
            self.service_started = True

        """Android環境でレシーバーを登録し、サービスを開始"""
        if platform == 'android':
            
            # 権限リクエスト (Android 9以降はFOREGROUND_SERVICEが必要)
            request_permissions([Permission.INTERNET, Permission.WAKE_LOCK, Permission.FOREGROUND_SERVICE])
            self.log("Permissions requested.") # 追加

            # BroadcastReceiverのインスタンス化 (start()は呼ばない)
            self.br = BroadcastReceiver(
                self.on_broadcast_received, 
                actions=['jp.co.example.UPLOAD_PROGRESS_UPDATE']
            )
            
            if hasattr(self.br, 'receiver'):
                # フィルタの設定
                intent_filter = IntentFilter()
                intent_filter.addAction('jp.co.example.UPLOAD_PROGRESS_UPDATE')
                
                # Android 14対応のフラグ付き登録
                currentActivity.registerReceiver(self.br.receiver, intent_filter, ContextCompat.RECEIVER_NOT_EXPORTED)
                
            # サービスの開始
            self.start_service()
            self.log("Service start attempted.") # 追加

    def on_broadcast_received(self, context, intent):
        """ブロードキャストを受信した時のコールバック"""
        # intent からデータを取り出してUIを更新
        # android.broadcast が自動的にメインスレッドを考慮してくれるため
        # Clock.schedule_once を使わなくても安全な場合が多いです
        self.update_ui(context, intent)

    def on_stop(self):
        # アプリ終了時にレシーバーを停止（重要）
        if platform == 'android' and hasattr(self, 'br'):
            self.br.stop()
        super().on_stop()

    def log(self, text):
        # UI スレッド外から呼ばれた場合は UI スレッドで実行する
        if threading.current_thread() is not threading.main_thread():
            Clock.schedule_once(lambda dt: self.log(text), 0)
            return

        date_str = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        self.ids.rv.data.append({'text': f'[color=#00FFFF]{date_str}[/color]\n{text}'})

class BroadcastApp(App):
    def build(self):
        # UIのKv言語定義をここに書くか、.kvファイルを読み込む
        Builder.load_string('''
<Cell@Label>:
    canvas.before:
        Color:
            rgba: (0, 0, 0, 1)  # セルの背景色（黒）
        Rectangle:
            pos: self.pos
            size: self.size

<LogText@Label>:
    canvas.before:
        Color:
            rgba: (0, 0, 0, 1)  # セルの背景色（黒）
        Rectangle:
            pos: self.pos
            size: self.size

    font_name: 'log_font'
    text_size: self.width, None
    size_hint_y: None
    height: self.texture_size[1]
    padding: 5
    markup: True

<MainScreen>:
    orientation: 'vertical'
    
    Label:
        text: 'Android Broadcast Intent Test'
        font_size: 48
        text_size: self.width, None
        size_hint_y: 0.07
        height: self.texture_size[1]

    GridLayout:
        cols: 2
        padding: 2
        spacing: 2
        size_hint_y: None
        height: self.minimum_height

        row_force_default: True
        row_default_height: 50

        canvas.before:
            Color:
                rgba: (0.5, 0.5, 0.5, 1)  # 枠線の色（灰色）
            Rectangle:
                pos: self.pos
                size: self.size

        # 1. サービスの開始時刻
        Cell:
            text: 'サービス開始時刻'
        Cell:
            text: root.start_time_str
            id: start_time_label
    
        # 2. 秒カウンター
        Cell:
            text: '秒カウンター'
        Cell:
            text: root.counter_str
            id: counter_label
            
        # 3. サービスの開始時刻 + 秒カウンター
        Cell:
            text: '期待時刻 (サービス開始+秒)'
        Cell:
            text: root.expected_time_str
            id: expected_time_label
    
        # 4. 現在時刻
        Cell:
            text: '現在時刻 (受信時)'
        Cell:
            text: root.current_time_str
            id: current_time_label
            color: (0, 1, 0, 1) # 緑色で強調

    Label:
        text: 'Log'
        font_size: 48
        text_size: self.width, None
        size_hint_y: 0.07
        height: self.texture_size[1]

    RecycleView:
        id: rv
        viewclass: 'LogText'

        canvas.before:
            Color:
                rgba: (0.5, 0.5, 0.5, 1)  # 枠線の色（灰色）
            Rectangle:
                pos: self.pos
                size: self.size

        RecycleBoxLayout:
            id: rbl
            size_hint: 1, None
            height: self.minimum_height
            default_size_hint: 1, None
            default_size: None, None
            spacing: 2
            padding: 2
            orientation: 'vertical'
        ''')

        return MainScreen()

    def on_stop(self):
        # アプリ終了時にレシーバーの登録解除とサービス停止を推奨
        if self.root.broadcast_receiver:
            LocalBroadcastManager.getInstance(currentActivity).unregisterReceiver(self.root.broadcast_receiver)
        # if self.root.service_intent:
        #     currentActivity.stopService(self.root.service_intent) # サービスを停止したい場合はコメントを外す

# デフォルトフォント指定
default_font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansJP-Regular.ttf')
resource_add_path(os.path.dirname(default_font_path))
LabelBase.register(DEFAULT_FONT, default_font_path)

# ログフォント指定
log_font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'PlemolJPHS-Regular.ttf')
resource_add_path(os.path.dirname(log_font_path))
LabelBase.register('log_font', log_font_path)

if __name__ == '__main__':
    BroadcastApp().run()
