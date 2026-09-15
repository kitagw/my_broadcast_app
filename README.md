# 概要
Androidアプリのバックグラウンドサービスプロセスの動作テストアプリ

### 処理内容
1. アプリを起動すると、バックグラウンドサービスプロセスが自動起動する
2. サービスプロセス内で、サービスプロセスが起動した時刻を保持しておき、また秒カウンターを開始する
3. サービスプロセスから、メインプロセスに、サービス開始時刻と経過秒（秒カウンターの値）を通知する
4. メインプロセスで通知された、サービス開始時刻に経過秒を加算して、現在時刻とのズレを見て、サービスの動作状況を見る

###

# ビルド

### 仮想環境作成
pythonのバージョンは、kivyの相性の良い 3.11 とする。
```
python3.11 -m venv .venv
```
仮想環境の切り替え
```
source .venv/bin/activate
```

### pip整備
必要パッケージのインストール
```
pip install --upgrade pip
pip install --upgrade kivy cython python-for-android
pip install --upgrade buildozer
```

### buildozer
debugビルド（自分用アプリはこれで十分）
```
buildozer -v android debug
```

2回目以降のビルドで失敗するときは、build-arm64-v8a 配下の仮想環境を削除すると成功するかもしれない
```
rm -rf .buildozer/android/platform/build-arm64-v8a/build/venv
```
