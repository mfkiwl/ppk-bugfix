# PPKによりカメラ位置を求めるプログラム (v0.1.1)

# 1. 概要

## 1.1 機能概要

本ソフトでは、

1. (step 1) Drone のGPSアンテナの位置をPPK (後処理キネマティック測位)で求め、
1. (step 2) その測位結果を用いて各写真の撮像位置に変換

を行います。コマンドラインで実行する、Python script から呼び出す、の２通りの方法で使用することができます。

### 1.1.1 入力

各step で必要な情報を入力して使用します。

 入力内容 | 形式 | ファイル拡張子
--- | --- | ---
Drone のGNSS観測値 | RINEX 観測値ファイル |(*.obs)
基準局 のGNSS観測値 | RINEX observation ファイル| (*.obs)
GNSSの衛星軌道情報  | RINEX navigation ファイル |(*.nav)
PPK計算の基準局の座標値 | 緯度、経度、楕円体高 |
各写真のシャッタタイミング |  ファイル | (*.MRK)
各写真の撮像位置とGPSアンテナ位置との相対位置 | ファイル | (*.MRK)

入力データについては、

- RINEXファイルは RINEX format 3 (version3)とします。(RINEX2は対象外)
- 地理学的座標値は、10進方のdegree で与える (度分秒でない。)
- 高度はＷＧＳ８４の楕円体高 (標高ではない)
- アンテナカメラ補正情報ファイルは DJIのPhantom4RTK で用いられている形式

とします。

### 1.1.2 出力

出力されるCSVファイルは、写真名を写真ファイルの名前と一致させることで、metashape で読み込んで使用することができます。
CSVファイルには以下の情報を書いています。

キー | 内容 | 例
--- | ---| ---
name | 写真のファイル名（番号） | 100_0067_0001.JPG
datetime | datetime isoformat | 2020-03-18 03:17:21.743178+00:00
lat | 緯度(十進法) | 35.60321730
lon | 経度(十進法) | 140.08394447
hgt | 楕円体高 (メートル) | 98.7107
north_acc |南北方向の精度(メートル) | 0.0300
east_acc |東西方向の精度(メートル) | 0.0300
up_acc |北方向の精度(メートル) | 0.0300

name は写真のファイル名になることを想定しています。
ファイル名は、PREFIX + XXXX + POSTFIX の形とします。
XXXXはMRKファイルに書かれている番号を０詰目の４桁の数字で書きます。
これはDJIのPhantom4RTKの形式を参考にしています。
DJI Phantom4RTKの場合、PREFIXはフライトの番号に対応していて、RINEXファ
イル、MRKファイルで共通になっています。POSTFIXは ".JPG" となっています。以下は、MRKファイルと出力されるCSVの例です。
PREFIX, POSTFIXは、実行プログラムの引数で与えられます。

出力されるCSVファイルの例:
```
name,datetime,lat,lon,hgt,north_acc,east_acc,up_acc
100_0067_0001.JPG,2020-03-18 03:17:21.743178+00:00,35.60321730,140.08394447,98.7107,0.0300,0.0300,0.0300
100_0067_0002.JPG,2020-03-18 03:17:27.621069+00:00,35.60328483,140.08404823,98.7070,0.0300,0.0300,0.0300
...
```

上記に対応する入力MRKファイル
```
1	271041.743178	[2097]	    -4,N	   -15,E	   194,V	35.60322283,Lat	140.08393996,Lon	100.339,Ellh	1.112569, 1.211863, 2.918694	16,Q
2	271047.621069	[2097]	    32,N	    34,E	   189,V	35.60328401,Lat	140.08404846,Lon	94.992,Ellh	1.101813, 1.190496, 2.934119	16,Q
...
```

## 1.2 内容

入力ファイルをもとに、以下の処理計算を実行します。

(1) RTKLIB を用いて後処理キネマティック処理の測位計算を実行する
(2) 補正情報のファイル(*.MRK)を用いて、撮影時刻に合わせた位置の補間、GPSアンテナからカメラ位置への変換する

# 2. 使用方法

## 2.1 ファイル構成

RTKLIBのソースとpython コードから構成されます。動作確認用のサンプルデータも含めています。

```
├─conf
├─ext
│  └─rtklib_2.4.3_b34
├─sample
└─xgnss
```

## 2.2 動作環境

- python3
- gccなどのCコンパイラ。makefile

python スクリプトの動作実績は3.6.9, 3.9.6 で行いました。python 3.7以上で動作するように実装しています。また、このスクリプトでは、内部で別の実行ファイルを呼び出します。この実行ファイルはC言語のプログラムをコンパイルして作成する必要があるので、Cコンパイラが必要です。依存関係などは複雑ではありませんが、make を使ってコンパイルすることもできます。

(1) RTKLIBの測位計算プログラムのコンパイルを行います。rnx2rtkp が下記フォルダに生成されます。make build でも同じ内容を実行できます。

```
$ tar xfvz  ppk_camera_geotagging_20210629_0000000.tar.gz
$ pushd ext/rtklib_2.4.3_b34/app/consapp/rnx2rtkp/gcc/
$ make
$ popd
```

(2) python の環境設定を行います。このディレクトリにあるxgnss 以下にあるファイルを利用します。python3 でnumpy と pandas を利用します。

```
$ python3 -m pip install -r requirementx.txt
$ export PYTHONPATH=`pwd`:$PYTHONPATH
```

## 2.2 実行方法

python scriptで、python ppk_camera_geotagging.py で実行できます。

```
$ python ppk_camera_geotagging.py --help
```
で使い方を表示できます。

```
usage: ppk_camera_geotagging.py

positional arguments:
  rnx_obs               RINEX observation file (*.obs)
  rnx_nav               RINEX navigation file (*.nav)
  ref_rnx_obs           RINEX observation file of reference station (*.obs)
  timestamp_file        Camera offset file in DJI PPK file format (*.MRK)
  refpos                Reference station position (e.g., 35.657204659,140.048099674,43.7597)
```

サンプルは以下のように実行できます。

```
$ tar xfvz <コード一式>.tar.gz
$ python3 -m pip install requirementx.txt
$ python3 ppk_camera_geotagging.py ¥
    sample/100_0067_Rinex.obs ¥
    sample/02250780.20o ¥
    sample/02250780.20n ¥
    sample/100_0067_Timestamp.MRK ¥
    35.657204659,140.048099674,43.7597 ¥
    --rtklib_template_file=./conf/template-rnx2rtkp-conf.txt
```

実行すると、metashape で参照することができるカメラの位置情報のCSVファイルが生成されます。(camera_ref.csv)
また、中間ファイルは ./ppk_proc/ に生成されます。

同じ内容は make test で実行できます。

# 捕捉

## GPSアンテナ - カメラ位置の補正ファイル(*.MRK)

別資料にPPK files の説明書かれています。また、DJIに問い合わせをし、下記の回答を得ています。時刻と、補正情報をグローバル座標系(North-East-Down)で記録しています。

```
Column 1: Photo number.
Column 2: UTC exposure duration of each photo, with seconds expressed in GPS time format.
Column 3: UTC time of exposure of each photo, with GPS week expressed in GPS time format.
Column 4: Deviation (in mm) of the antenna phase center to camera CMOS sensor center in the north (N) direction at the time of exposure of each photo in North East Down system.
Column 5: Deviation (in mm) of the antenna phase center to camera CMOS sensor center in the east (E) direction at the time of exposure of each photo in North East Down system.
Column 6: Deviation (in mm) of the antenna phase center to camera CMOS sensor center in the vertical (V) direction at the time of exposure of each photo in North East Down system.
Column 7: Real-time location latitude (Lat) of CMOS center obtained at exposure time, which is in degrees.
Column 8: Real-time position longitude (Lon) of CMOS center obtained at exposure time, which is in degrees.
Column 9: Real-time height of CMOS center obtained at exposure time, which is in meters as a unit. 
Columns 10 to 12: The standard deviation of the result of positioning in the three directions of north, east and antenna phase center. Which represents the relative accuracy of positioning in the three directions. The unit is meter.
Column 13: RTKflag value, 0- no positioning, 16- single point positioning mode, 34-RTK floating-point solution, 50-RTK  FIX. It is not recommended to use a photo to directly create a picture when the RTKflag value is not 50.
```

## 参考情報

- RTKLIB: https://github.com/tomojitakasu/RTKLIB/tree/rtklib_2.4.3
- RINEX format: http://acc.igs.org/misc/rinex304.pdf

## 更新履歴
version | 日付 | 内容
--- | --- | ---
0.1.0 | 2021/06/29 | draft作成
0.1.1 | 2021/09/13 | CSVファイルの記述を追加