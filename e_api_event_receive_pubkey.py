# -*- coding: utf-8 -*-

# Copyright (c) 2026 Tachibana Securities Co., Ltd. All rights reserved.
# 2022.04.12, yo.

# 2021.07.08,   yo.
# 2023.04.11 reviced, yo.
# 2025.08.09 reviced, yo.
# 2026.02.18 reviced, yo.
# 2026.06.24 reviced,   yo.
#
# 立花証券ｅ支店ＡＰＩ利用のサンプルコード
#
# 動作確認
# Python 3.13.5 / debian13
# API v4r9
#
# 利用方法: 
# 事前に「e_api_login_pubkey.py」を実行して、仮想URL等を取得しておいてください。
# 実行は「e_api_login_pubkey.py」と同じディレクトリで行ってください。
#
# ------------------------------------------------------------------
#
# APIの基本設計について
# 
# 本APIは、プログラミング初心者や非ITエンジニアの方にも
# 利用しやすいよう、URLにJSON形式のパラメーターを付加して
# 送信する独自方式を採用しています。
# 
# 一般的なWeb APIとは異なる構成ですが、
# HTTPヘッダーやPOSTデータなどの知識を最小限に
# 抑えながら利用できることを重視しています。
# 
# このため、本APIは、URLとJSON文字列を組み立てて
# 送信するだけで利用でき、特別な知識を必要とせず、
# 各種スクリプト言語からも実装しやすいことを
# 優先した設計となっています。
#  
# ------------------------------------------------------------------
# 
# 機能: プッシュ送信される時価の取得
#
# == ご注意: ========================================
#   本番環境にに接続した場合、実際に市場に注文が出ます。
#   市場で約定した場合取り消せません。
# ==================================================
#

import urllib3
import datetime
import json
import os
import urllib.parse
from zoneinfo import ZoneInfo

# 必要な設定項目
# 行番号: P_GYOU_NO  （1-120の整数）
# 銘柄コード: S_ISSUE_CODE （通常銘柄は4桁、優先株等は5桁。例、伊藤園'2593'、伊藤園優先株'25935'）
# 市場: S_SIZYOU_C （00:東証   現在(2021/07/01)、東証のみ可能。）

# --- 利用時に変数を設定してください -------------------------------------------------------
# コマンド用パラメーター -------------------    
# 仕様では120銘柄まで指定できますが、負荷が高くなるため、サンプルコードでは1 - 3銘柄を用意。

# 1銘柄で取得の場合のサンプル
#P_GYOU_NO = '1'        # 行を指定する。string型。1-120の整数で、銘柄毎に違う行を指定する。時価取得時の銘柄の識別番号。
#S_ISSUE_CODE = '1234'  # 2.銘柄コード。string型。通常銘柄、4桁。優先株等、5桁。例、伊藤園'2593'、伊藤園優先株'25935'
#S_SIZYOU_C = '00'      # 3.市場。string型。  00:東証   現在(2021/07/01)、東証のみ可能。

# 2銘柄で取得の場合のサンプル
P_GYOU_NO = '1,2'        # 行を指定する。string型。1-120の整数で、銘柄毎に違う行を指定する。時価取得時の銘柄の識別番号。
S_ISSUE_CODE = '6501,9432'  # 2.銘柄コード。通常銘柄、4桁。優先株等、5桁。例、伊藤園'2593'、伊藤園優先株'25935'
S_SIZYOU_C = '00,00'      # 3.市場。  00:東証   現在(2021/07/01)、東証のみ可能。

# 3銘柄で取得の場合のサンプル
##P_GYOU_NO = '1,2,3'        # 行を指定する。string型。1-120の整数で、銘柄毎に違う行を指定する。時価取得時の銘柄の識別番号。
##S_ISSUE_CODE = '1301,1332,1333'  # 2.銘柄コード。通常銘柄、4桁。優先株等、5桁。例、伊藤園'2593'、伊藤園優先株'25935'
##S_SIZYOU_C = '00,00,00'      # 3.市場。  00:東証   現在(2021/07/01)、東証のみ可能。

# --- 以上コマンド用パラメーター-----------------------------------------------

# --- 共通設定項目 ------------------------------------------------------------
FNAME_URL_INFO = "file_url_info.txt"                # API接続情報ファイル
FNAME_PASSWD2 = "./.auth/file_pwd2.txt"              # 第二パスワード保存ファイル
FNAME_LOGIN_RESPONSE = "./.auth/file_login_response.txt"  # ログイン応答保存先
FNAME_INFO_P_NO = "file_info_p_no.txt"              # p_no保存ファイル

# --- 通信堅牢化のための設定項目 ---
API_TIMEOUT_SECONDS = 15.0  # タイムアウト時間（秒）: 応答がない場合15秒で切り上げる
MAX_RETRY_COUNT = 3         # 最大リトライ回数: 通信エラー時に自動再試行する回数
RETRY_INTERVAL_SECONDS = 5  # リトライ間隔（秒）: 再試行する前に待機する時間
# =========================================================================

# --- 共通ユーティリティ関数 ----------------------------------------------

def func_p_sd_date():
    """
    機能: システム時刻を"p_sd_date"の書式の文字列で返す。
    返値: "p_sd_date"の書式の文字列。 API規定書式 "YYYY.MM.DD-hh:mm:ss.sss"
    引数1: なし
    備考: 
        日本標準時（Japan Standard Time、JST）を利用のこと。
    """
    dt_now = datetime.datetime.now(
        # 日本標準時（Japan Standard Time、JST）を利用
        ZoneInfo("Asia/Tokyo")
    )
    # 年.月.日-時:分:秒 の部分を作成
    str_date = dt_now.strftime("%Y.%m.%d-%H:%M:%S")
    
    # マイクロ秒（6桁ゼロ埋め）から先頭の3桁を切り出してミリ秒を作成
    str_micro = f"{dt_now.microsecond:06d}"
    str_ms = str_micro[0:3]
    
    # ドットで結合してAPI規定書式を完成
    return str_date + "." + str_ms


def func_replace_urlencode(str_input):
    """
    URLエンコードを行う。

    URLでは、スペースや「&」「+」「?」などの記号が
    特別な意味を持つため、そのまま送信できない場合がある。
    そのため、これらの文字を「%xx」形式へ変換する。

    例:
        "A B+C" → "A%20B%2BC"

    本サンプルでは Python標準ライブラリの
    urllib.parse.quote() を利用してURLエンコードを行う。

    他言語へ移植する場合も、自前で変換処理を作成するのではなく、
    各言語が提供する標準のURLエンコード関数を利用することを推奨する。

    主な対応例:
        Python      : urllib.parse.quote()
        Java        : java.net.URLEncoder.encode()
        C#          : Uri.EscapeDataString()
        JavaScript  : encodeURIComponent()
        Go          : url.QueryEscape()

    Parameters
    ----------
    str_input : str
        URLエンコード対象文字列

    Returns
    -------
    str
        URLエンコード後の文字列
    """
    return urllib.parse.quote(str_input, safe='')


def func_read_from_file(str_fname):
    """ファイルから文字情報を一括読み込み（BOMを排除）"""
    str_read = ''
    try:
        # utf-8-sig を指定してBOMを自動的に排除しファイルを開く
        with open(str_fname, 'r', encoding='utf-8-sig') as fin:
            while True:
                line = fin.readline()
                if not line:
                    break
                str_read = str_read + line
        return str_read
    except IOError as e:
        print(f"[エラー] ファイルを読み込めません: {str_fname}")
        raise e


def func_write_to_file(str_fname_output, str_data):
    """ファイルに書き込み、権限を所有者のみ(600)に制限"""
    try:
        # 出力先フォルダの存在を確認し、存在しない場合は自動作成
        str_dir = os.path.dirname(str_fname_output)
        if str_dir and not os.path.exists(str_dir):
            os.makedirs(str_dir, exist_ok=True)

        # データをファイルへ書き込み
        with open(str_fname_output, 'w', encoding='utf-8') as fout:
            fout.write(str_data)
        
        # パーミッションを600（所有者のみ読み書き可能）に制限
        os.chmod(str_fname_output, 0o600)
    except IOError as e:
        print(f"[エラー] ファイルに書き込めません: {str_fname_output}")
        raise e


def func_get_url_info(fname):
    """
    file_url_info.txt からAPI接続設定を取得

    機能: API接続情報をファイルから取得し辞書型で返す
    引数1: 接続先情報を保存したファイル名: fname_url_info

    サポートへの問い合わせは、sJsonOfmt:'5'でお願いします。
    """
    str_url_info = func_read_from_file(fname)
    # JSON形式の文字列を辞書型で取り出す
    return  json.loads(str_url_info)    


def func_get_login_response(str_fname):
    '''
    ログインレスポンスを取得
    '''
    str_login_response = func_read_from_file(str_fname)
    dic_login_response = json.loads(str_login_response)
    return dic_login_response
    

def func_get_p_no(fname):
    """ 
    機能: p_noをファイルから取得する
    引数1: p_noを保存したファイル名（fname_info_p_no = "e_api_info_p_no.txt"）
    """
    str_p_no_info = func_read_from_file(fname)
    # JSON形式の文字列を辞書型で取り出す
    json_p_no_info = json.loads(str_p_no_info)
    int_p_no = int(json_p_no_info.get('p_no'))
    return int_p_no


def func_save_p_no(str_fname_output, int_p_no):
    """p_noを保存するためのJSONファイルを生成"""
    p_no_dict = {"p_no": str(int_p_no)}
    json_data = json.dumps(p_no_dict, indent=4)
    func_write_to_file(str_fname_output, json_data)
    print(f'現在の "p_no" を保存しました。 p_no = {int_p_no} -> {str_fname_output}')


def func_make_url_request_from_dic(
                                    auth_flg,       # ログインFlag。    login:true   login以外:false
                                    url_target,     # 接続先URL
                                    work_dic_req    # API要求項目
):
    '''
    API問合せ用完全URL（クエリパラメータ付）を作成
    
    ------------------------------------------------------------------

    APIの基本設計について

    本APIは、プログラミング初心者や非ITエンジニアの方にも
    利用しやすいよう、URLにJSON形式のパラメーターを付加して
    送信する独自方式を採用しています。

    一般的なWeb APIとは異なる構成ですが、
    HTTPヘッダーやPOSTデータなどの知識を最小限に
    抑えながら利用できることを重視しています。

    このため、本APIは、URLとJSON文字列を組み立てて
    送信するだけで利用でき、特別な知識を必要とせず、
    各種スクリプト言語からも実装しやすいことを
    優先した設計となっています。
    
    ------------------------------------------------------------------
    JSONをHTTPボディではなくURLに付加して送信します。
    詳細はAPIマニュアル参照。
    備考：
        サポートへの問い合わせを考慮し、項目ごとの改行とタブを入れてあります。
    '''
    str_url = url_target
    if auth_flg:
        str_url = urllib.parse.urljoin(str_url, 'auth/')
    json_param = json.dumps(work_dic_req, indent=4, ensure_ascii=False)
    return f"{str_url}?{json_param}"


def func_api_req(str_request_method, str_url): 
    """
    APIリクエストの送信と、Shift-JIS応答のデコード（リトライ・タイムアウト対応版）
    """
    # HTTP通信ライブラリ urllib3 を利用します。
    #
    # requests ライブラリでも同様の処理は可能ですが、
    # 本サンプルでは APIサーバーへの接続処理が分かりやすいよう、
    # より基本的な urllib3 を利用しています。
    #
    # 他言語へ移植する場合も、
    # 「HTTPクライアント生成 → リクエスト送信 → レスポンス受信」
    # の流れを対応するライブラリへ置き換えてください。

    print('--- 送信電文 -------------------------------------------')
    print(str_url)

    # 接続および読み込みのタイムアウト時間を設定
    timeout_config = urllib3.Timeout(connect=API_TIMEOUT_SECONDS, read=API_TIMEOUT_SECONDS)
    http = urllib3.PoolManager()
    
    response_data = None
    status_code = None

    # 最大試行回数に達するまで通信をリトライ
    for attempt in range(1, MAX_RETRY_COUNT + 1):
        try:
            # 2回目以降の試行（再接続）の前に、指定されたインターバル時間待機
            if attempt > 1:
                print(f"[{attempt}/{MAX_RETRY_COUNT} 回目] 再接続を試みます...（{RETRY_INTERVAL_SECONDS}秒待機）")
                time.sleep(RETRY_INTERVAL_SECONDS)

            req = http.request(str_request_method, str_url, timeout=timeout_config)
            status_code = req.status
            response_data = req.data
            break  # 正常に通信できた場合はループを抜ける

        except (TimeoutError, MaxRetryError) as ce:
            print(f"\n[警告] 通信エラーが発生しました (試行: {attempt}/{MAX_RETRY_COUNT})")
            print(f"エラー詳細: {ce}")
            
            # 最大リトライ回数を超えて失敗した場合はConnectionErrorを発生
            if attempt == MAX_RETRY_COUNT:
                raise ConnectionError(
                    f"APIサーバーへの接続に規定回数失敗しました。サーバーがメンテナンス中か、停止している可能性があります。\n"
                    f"設定されたタイムアウト時間: {API_TIMEOUT_SECONDS}秒"
                )
        except Exception as ex:
            print(f"\n[警告] 予期せぬネットワーク例外が発生しました: {ex}")
            if attempt == MAX_RETRY_COUNT:
                raise ex

    print(f"HTTP Status: {status_code}")

    # 受信した電文をShift-JISからUTF-8へデコード（不正なバイトは無視）
    str_response = response_data.decode("shift-jis", errors="ignore")
    print('--- 受信電文 -------------------------------------------')
    print(str_response)
    print('--------------------------------------------------------')

    return str_response


def func_api_request_from_dic(
                                flg_login,          # ログインFlag。    login:true   login以外:false
                                destination_url,    # 接続先URL。
                                                    #   ログイン時は、FNAME_URL_INFOから取得する接続先。
                                                    #   それ以外はログインレスポンスで指定される仮想URL。
                                dic_req_item        # API要求項目
):
    '''
    APIへの問い合わせを実行する。
    '''
    # URL文字列の作成
    str_url = func_make_url_request_from_dic(
                                                flg_login,          # ログインFlag。    login:true   login以外:false
                                                destination_url,    # 接続先URL
                                                dic_req_item        # API要求項目
    )

    # APIへの問い合わせ。
    # リクエストメソッドの指定('GET'、'POST'どちらでも動作します。)
    str_api_response = func_api_req('POST', str_url)

    # apiの返り値（JSON形式の文字列）を辞書型で取り出す
    dic_api_response = json.loads(str_api_response)
    
    return dic_api_response

# --- 共通ユーティリティ関数 ----------------------------------------------





# Event
# 資料は、API専用ページ
# ５．マニュアル、
# １．共通説明
# （５）注文約定通知（仮想ＵＲＬ（EVENT））
# 別紙「立花証券・ｅ支店・ＡＰＩ、EVENT I/F 利用方法、データ仕様」参照。
# (api_event_if.xlsx)
#
# 問合せの例
# 2. 利用方法 p2/26
#「
# 仮想URL                     ※e支店・APIでの利用時の例。
# ?p_rid=0                      ※3.(3)【株価ボード・アプリケーション機能毎引数設定値表】参照。
# &p_board_no=1000              ※3.(3)【株価ボード・アプリケーション機能毎引数設定値表】参照。
# [&p_gyou_no=N[,N]]            ※必要時のみ設定。
# [&p_issue_code=NNNN[,NNNN]]   ※必要時のみ設定。
# [&p_mkt_code=NN[,NN]]         ※必要時のみ設定。
# &p_eno=0  ※1
# &p_evt_cmd=ST,KP,EC,SS,US ※2
# 」
#
# eventで時価情報(FD)を取得する場合、アプリケーション機能のNo2を利用する。
# 3. 通知データ仕様
# (3)FD     p5/26
# 【株価ボード・アプリケーション機能毎引数設定値表】
# No: 2
# 株価ボード・アプリケーション: e支店・API、時価配信機能あり
# p_rid: 22
# p_board_no: 1000
# p_gyou_no: 1-120
# p_issue_code: 銘柄コード[120]
# p_mkt_code: 市場コード[120]
#
# ----------------------
# 注意点:
# EVENTの場合、送信のURL内に'\n'や'\t'を入れないこと。
# 余計な制御文字を入れるとエラーになる。
# ----------------------

# p_evt_cmdは、以下の値をカンマ区切りで列挙する。
# p3/26
#No 値 説明                        備考
# 1 ST エラーステータス情報配信指定   発生時通知
# 2 KP キープアライブ情報配信指定    発生時通知(5秒間通知未送信時通知)
# 3 FD 時価情報配信指定             初回はメモリ内スナップショット(全データ)、以降は変化分のみ通知
# 4 EC 注文約定通知イベント配信指定   初回は当日営業日内の通知削除機能で削除していない全通知を接続毎に再送、以降は発生時通知
# 5 NS ニュース通知イベント配信指定   初回は当日営業日内の通知削除機能で削除していない全通知を接続毎に再送、以降は発生時通知
# 6 RR 画面リフレッシュ通知配信指定   現時点で不使用
# 7 SS システムステータス配信指定    初回は当日営業日内の通知削除機能で削除していない全通知を接続毎に再送、以降は発生時通知
# 8 US 運用ステータス配信指定      初回は当日営業日内の通知削除機能で削除していない全通知を接続毎に再送、以降は発生時通知


# 機能： 受信データを区切り文字で分割し辞書型で返す。
# 引数1：str_url string
# 返値： 辞書型データ
# 備考:
# 受信データは、
#       websocket: string型
#       event: byte型
 
# 仕様の解説は、API専用ページ
# ５．マニュアル、
# １．共通説明
# （５）注文約定通知（仮想ＵＲＬ（EVENT））
# 別紙「立花証券・ｅ支店・ＡＰＩ、EVENT I/F 利用方法、データ仕様」参照。
# (api_event_if.xlsx)
# 3. 通知データ仕様 p4/26
# 通知データは「^A」「^B」「^C」を区切り子とし文字列の羅列で送信する。
# 通知データ中の値として「^A^B^C」は使わない。
# 項目A1=値B1;項目A2=値B21,B22,B23;・・・を送信する場合、
# 項目A1^B値B1^A項目A2^B値B21^CB22^CB23^A・・・と送信する。
# ※区切り子「^A」は1項目値、「^B」は項目と値、「^C」は値と値の各区切り。
#
# 「型_行番号_情報コード」で、情報コードで示す値を設定する。
# 例、b'p_1_DPP^B3757' の場合、「p_1_DPP」は、p:プレーン文字列、_1:行番号、_DPP:現在値
#
def func_punctuate_message(chunk):
    dict_message = {}
    str_message = ''
    flg_p_date = False      # 取得した情報がp_dateの場合、Trueに設定し時刻を取得する。
    flg_end = False         # p_dateが指定時間を超えたら、Trueに設定し終了する。
    
    chunk_ctrl = ""         # 元電文で制御コードとなっている区切子^A,^B,^Cを文字列"^A","^B","^C"に置き換えた電文を格納する。

    for i in range(len(chunk)):
        if chunk[i:i+1] != '\x01' and chunk[i:i+1] != '\n' :
            # 項目と値の区切り'^B'が来た場合、':'に置き換え（置き換え文字は任意）。
            if chunk[i:i+1] == '\x02' :
                str_key = str_message
                str_message = ''
                chunk_ctrl = chunk_ctrl + '^B'
            # 値区切り文字'^C'が来た場合、','に置き換え（置き換え文字は任意）。
            elif chunk[i:i+1] == '\x03' :
                str_message = str_message + ','
                chunk_ctrl = chunk_ctrl + '^C'
            else :                        
                str_message = str_message + chunk[i:i+1]
                chunk_ctrl = chunk_ctrl + chunk[i:i+1]

        # 項目区切り'^A'と改行が来た場合
        else:   # if chunk[i:i+1] == '\x01' or chunk[i:i+1] == '\n' :
            dict_message[str_key] = str_message
            str_message = ''
            if chunk[i:i+1] == '\x01' :
                chunk_ctrl = chunk_ctrl + '^A'
            if chunk[i:i+1] == '\n' :
                chunk_ctrl = chunk_ctrl + '\\n'
    
    print("受信電文　区切子^A^B^Cは非表示：")
    print(chunk)
    print("区切子^A^B^Cを文字列'^A','^B','^C'に置換。改行\\nを文字列'\\n'に置換。：")
    print(chunk_ctrl)
    print()
    return dict_message


# 機能： event用のurlを作成する。
# 引数1：行番号 string
# 引数2：銘柄コード string
# 引数3：市場 string
# 引数4: class_login_property（口座属性クラス）
# 返値： url string
# 備考: NS（ニュース）は重いため注意が必要。
def func_make_event_url(str_p_gyou_no, str_sIssueCode, str_sSizyouC, str_sUrlEvent):
    str_url = ''
    str_url = str_url + str_sUrlEvent
    str_url = str_url + '?'
#    str_url = str_url + 'p_evt_cmd=ST,KP,FD'
    str_url = str_url + 'p_evt_cmd=ST,KP,EC,SS,US,FD'
    str_url = str_url + '&' + 'p_eno=0'     # 配信開始したいイベント通知番号(ユニーク番号)、指定番号の次から送信する(0なら全て)。
    str_url = str_url + '&' + 'p_rid=22'    # 固定値
    str_url = str_url + '&' + 'p_board_no=1000'    # 固定値
    str_url = str_url + '&' + 'p_gyou_no=' + str_p_gyou_no      # 行番号。1-120で指定。
    str_url = str_url + '&' + 'p_issue_code=' + str_sIssueCode  # 銘柄コード
    str_url = str_url + '&' + 'p_mkt_code=' + str_sSizyouC      # 市場

    print('print(str_url):')
    print(str_url)
    return str_url
    


# 機能： event用のhttpアクセスを行い、プッシュされた情報を標準出力に出力する。
# 引数1：str_url string
# 返値： 無し
# 備考:
# 仕様の解説は、API専用ページ
# ５．マニュアル、
# １．共通説明
# （５）注文約定通知（仮想ＵＲＬ（EVENT））
# 別紙「立花証券・ｅ支店・ＡＰＩ、EVENT I/F 利用方法、データ仕様」参照。
# (api_event_if.xlsx)
# 3. 通知データ仕様 p4/26
# 通知データは「^A」「^B」「^C」を区切り子とし文字列の羅列で送信する。
# 通知データ中の値として「^A^B^C」は使わない。
# 項目A1=値B1;項目A2=値B21,B22,B23;・・・を送信する場合、
# 項目A1^B値B1^A項目A2^B値B21^CB22^CB23^A・・・と送信する。
# ※区切り子「^A」は1項目値、「^B」は項目と値、「^C」は値と値の各区切り。
#
# 「型_行番号_情報コード」で、情報コードで示す値を設定する。
# 例、b'p_1_DPP^B3757' の場合、「p_1_DPP」は、p:プレーン文字列、_1:行番号、_DPP:現在値
#
def func_event_receive(str_url):
    byte_text = b''
    flg_p_date = False      # 取得した情報がp_dateの場合、Trueに設定し時刻を取得する。
    flg_end = False         # p_dateが指定時間を超えたら、Trueに設定し終了する。
    str_chunk_accum = ''

    # APIに接続
    http = urllib3.PoolManager()

    # ストリーム形式で接続（** 重要 **）
    resp = http.request(
        'GET',
        str_url,
        preload_content=False)
    
    for byte_chunk in resp.stream(2048):
        str_chunk = byte_chunk.decode()
        # dict_my_message = func_punctuate_message(str_chunk)
        str_chunk_accum = str_chunk_accum + str_chunk
        if str_chunk_accum[-1:] ==  '\x01' or str_chunk_accum[-1:] ==  '\n' :
            print()
            print('---------------')
            dict_my_message = func_punctuate_message(str_chunk_accum)
            str_chunk_accum = ''


            for key, value in dict_my_message.items():
                print(key, ': ', value)
                if key == 'p_errno' and value == '2' :
                    print()
                    print(key, ': ', value)
                    print("仮想URLが有効ではありません。")
                    print("電話認証 + e_api_login_tel.py実行")
                    print("を再度行い、新しく仮想URL（1日券）を取得してください。")
                    print()
    
    resp.release_conn()


# ======================================================================================================
#     プログラム始点 
# ======================================================================================================

if __name__ == "__main__":

    # 表示形式を接続情報ファイルから読み込む。
    dic_url_info = func_get_url_info(FNAME_URL_INFO)
    str_sJsonOfmt = dic_url_info.get("sJsonOfmt")

    # ログイン応答を保存した「file_login_response.txt」から、仮想URLと口座情報を取得
    dic_login_property = func_get_login_response(FNAME_LOGIN_RESPONSE)

    # 現在（前回利用した）のp_noをファイルから取得する
    my_p_no = func_get_p_no(FNAME_INFO_P_NO)
    my_p_no = my_p_no + 1
    # 更新した"p_no"を保存する。
    func_save_p_no(FNAME_INFO_P_NO, my_p_no)
    
    print()
    print('-- event 受信 -------------------------------------------------------------')
    # Eventは、仮想URL:'sUrlEvent'
    str_connection_url = dic_login_property.get('sUrlEvent')

    # event用urlの作成
    my_url = func_make_event_url(P_GYOU_NO, S_ISSUE_CODE, S_SIZYOU_C, str_connection_url)
    
    # eventでのプッシュ情報の受信
    try:
        func_event_receive(my_url)
    except	KeyboardInterrupt:
        print	("info, Ctrl^C interrupt.")
    except	Exception as p_exception:
        print   (f'error, exception catched:[{p_exception}]')
