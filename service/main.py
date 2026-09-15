from jnius import autoclass # type: ignore
import time
from time import sleep

# Javaクラスのインポート
Log = autoclass('android.util.Log')
PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
IntentFilter = autoclass('android.content.IntentFilter')
PendingIntent = autoclass('android.app.PendingIntent')
NotificationBuilder = autoclass('android.app.Notification$Builder')
NotificationChannel = autoclass('android.app.NotificationChannel')
NotificationManager = autoclass('android.app.NotificationManager')
PowerManager = autoclass('android.os.PowerManager')
String = autoclass('java.lang.String')

TAG = 'SERVICE_DEBUG'
# カスタムアクション名
ACTION_UPDATE = 'jp.co.example.UPLOAD_PROGRESS_UPDATE'

# 通知IDを定数にしておくと間違いがありません
NOTIFICATION_ID = 1
CHANNEL_ID = 'my_service_channel'

def setup_foreground_service():
    Log.i(TAG, "setup_foreground_service - 1-1")
    # 1. 通知チャンネルの作成 (Android 8.0以上必須)
    channel_id = 'my_service_channel'
    channel_name = 'My Background Service'
    importance = NotificationManager.IMPORTANCE_LOW
    channel = NotificationChannel(channel_id, channel_name, importance)
    
    Log.i(TAG, "setup_foreground_service - 1a-1")
    notification_manager = service.getSystemService(Context.NOTIFICATION_SERVICE)
    notification_manager.createNotificationChannel(channel)

    Log.i(TAG, "setup_foreground_service - 2-1")
    # 2. 通知をタップしたときにアプリを開く設定
    app_context = service.getApplicationContext()
    app_intent = Intent(app_context, autoclass('org.kivy.android.PythonActivity'))
    app_intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_NEW_TASK)
    # アプリ起動時のメインアクションとして設定
    app_intent.setAction(Intent.ACTION_MAIN)
    app_intent.addCategory(Intent.CATEGORY_LAUNCHER)

    pending_intent = PendingIntent.getActivity(app_context, 0, app_intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE)

    Log.i(TAG, "setup_foreground_service - 3-1")
    # 3. 通知の構築
    builder = NotificationBuilder(app_context, channel_id)
    builder.setContentTitle("サービス実行中")
    builder.setContentText("バックグラウンドでデータを集計しています...")
    builder.setSmallIcon(service.getApplicationInfo().icon)
    builder.setContentIntent(pending_intent)
    notification = builder.build()

    Log.i(TAG, "setup_foreground_service - 4-1")
    # 4. フォアグラウンドサービスとして開始
    # 第1引数は通知ID（0以外）、第2引数は通知オブジェクト
    service.startForeground(NOTIFICATION_ID, notification)

def acquire_wakelock():
    # CPUを眠らせない設定
    power_manager = service.getSystemService(Context.POWER_SERVICE)
    wakelock = power_manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MyService:WakeLockTag")
    wakelock.acquire()
    return wakelock

def send_broadcast(start_time, counter):
    """メインアプリへデータをブロードキャストする"""
    try:
        intent = Intent(ACTION_UPDATE)
        # 自分のアプリ内だけに送信することを明示（これが重要！）
        intent.setPackage(service.getPackageName())
        intent.putExtra('start_time', String(str(start_time)))
        intent.putExtra('counter', String(str(counter)))

        # ログ確認用
        Log.i(TAG, f"START Sent start_time={start_time}, counter={counter}")
        # サービス自身のsendBroadcastメソッドを使用
        service.sendBroadcast(intent)
        # ログ確認用
        Log.i(TAG, f"END Sent start_time={start_time}, counter={counter}")
    except Exception as e:
        Log.i(TAG, f"Exception: {e}")

def update_notification(counter):
    """通知の中身を更新する"""
    try:
        app_context = service.getApplicationContext()
        
        # 1. 再度インテントを作成（タップ時にアプリを開くため）
        app_intent = Intent(app_context, autoclass('org.kivy.android.PythonActivity'))
        app_intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_NEW_TASK)
        # アプリ起動時のメインアクションとして設定
        app_intent.setAction(Intent.ACTION_MAIN)
        app_intent.addCategory(Intent.CATEGORY_LAUNCHER)
        pending_intent = PendingIntent.getActivity(app_context, 0, app_intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE)

        # 2. Builderで新しい通知テキストを設定
        builder = NotificationBuilder(app_context, CHANNEL_ID)
        builder.setContentTitle("サービス稼働中")
        # ここでカウンターを表示
        builder.setContentText(f"現在のカウント: {counter} 秒経過") 
        builder.setSmallIcon(service.getApplicationInfo().icon)
        builder.setContentIntent(pending_intent)
        # 通知の音や振動を抑制する（更新のたびに鳴らないように）
        builder.setOnlyAlertOnce(True) 
        # 通知を構築        
        notification = builder.build()

        # 3. NotificationManagerを取得して更新を通知
        notification_manager = service.getSystemService(Context.NOTIFICATION_SERVICE)
        notification_manager.notify(NOTIFICATION_ID, notification)
        
    except Exception as e:
        Log.e(TAG, f"Notification update failed: {e}")

setup_foreground_service()
lock = acquire_wakelock()

Log.i(TAG, "===== Service Python Script is Starting! =====")

try:
    # ここにこれまでのレシーバー登録処理などを記述
    Log.i(TAG, "Initializing Receiver...")
    
    start_time = int(time.time())
    counter = 0

    while True:
        counter += 1
        Log.i(TAG, "Service heartbeat...")
        send_broadcast(start_time, counter)

        if counter % 10 == 0:  # 10秒ごとに通知を更新
            update_notification(counter)

        time.sleep(1)
except Exception as e:
    Log.e(TAG, "Service crashed: " + str(e))
    