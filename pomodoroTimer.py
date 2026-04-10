# インストールした discord.py を読み込む
import discord
import math
import time
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone

#
====================================================================
# ロギング設定
#
====================================================================
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger('discord').setLevel(logging.INFO)
logger = logging.getLogger('pomodoro')
#
====================================================================

#TOKENは最下部のRUNで環境変数から取得しているので不要
#TOKEN = 'NTc1NjE5NDM5MjQwNjc1MzY5.XiCBmA.syP4iBbp5NmlkWPeCUFksEDhKSo'

# 接続に必要なオブジェクトを生成
client = discord.Client()

# 起動時に動作する処理
@client.event
async def on_ready():
    logger.info('ポモドーロタイマー：秘書部ログインしました
(user=%s)', client.user)

@client.event
async def on_disconnect():
    logger.warning('Discord から切断されました')

@client.event
async def on_resumed():
    logger.info('Discord に再接続しました')

@client.event
async def on_error(event, *args, **kwargs):
    logger.exception('未処理の例外が発生しました (event=%s)', event)

@client.event
async def on_message(message):

    #初期宣言
    sendchannelId = os.environ['SEND_CHANNEL']

    #送信するチャンネルをインスタンス化
    Sendchannel = client.get_channel(int(sendchannelId))

    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return

    logger.info('message received: author=%s content=%s',message.author, message.content)

    # 「/yaruzo」と発言したら、wave開始
    if message.content.startswith('/yaruzo'):

        logger.info('/yaruzo command triggered by %s', message.author)

        #回数は３回とする
        pomodoroRunCount = 3

        # 5分刻みでの開始時間を算出する
        # [実装メモ]
        #   1.現在日時取得
        #   2.分を取得
        #   3.5分間隔に修正・・・Roundup(分/5,0)*5
        #   4.現在時間＋丸めた分を組合せて時間作成

        # 現在日時を取得する
        JST = timezone(timedelta(hours=+9), 'JST')
        dt_now = datetime.now(JST)

        # 分を5分単位で切り上げる(00秒からスタートするため、割り切れる場合において繰り上がるように0.1を加算する)
        renewMinite = math.ceil(dt_now.minute / 5 + 0.1) * 5
        diffMinite = renewMinite - dt_now.minute

        # 開始時間を取得
        dtPomodoroStartTime = dt_now.replace(second=0, microsecond=0)   + timedelta(minutes=diffMinite)

        # Waveで表示する文章を作成する
        strWaveTemplate = ('{}ポモ目 {} - {}')
        strBreakTemplate = ('{}休憩  {} - {}')
        strWaveTexts = []

        for i in range(pomodoroRunCount):
            # Wave時間を作成する
            dtWaveStartTime = dtPomodoroStartTime + timedelta(minutes=30*i)
            dtWaveEndTime = dtPomodoroStartTime + timedelta(minutes=30*i) + timedelta(minutes=25)
            strWaveText = strWaveTemplate.format(i+1, "{0:%H:%M}".format(dtWaveStartTime), "{0:%H:%M}".format(dtWaveEndTime))
            strWaveTexts.append(strWaveText)

            # 休憩時間を作成する
            dtBreakStartTime = dtPomodoroStartTime + timedelta(minutes=30*i) + timedelta(minutes=25)

            #１，２回目は小休憩、３回目は大休憩とする
            if i < 2:
                strBreakText = "小"
                dtBrakeEndTime = dtPomodoroStartTime + timedelta(minutes=30*i) + timedelta(minutes=30)
            else:
                strBreakText = "大"
                dtBrakeEndTime = dtPomodoroStartTime + timedelta(minutes=30*i) + timedelta(minutes=40)

            strWaveText = strBreakTemplate.format(strBreakText, "{0:%H:%M}".format(dtBreakStartTime), "{0:%H:%M}".format(dtBrakeEndTime))
            strWaveTexts.append(strWaveText)

        # Wave時間を作成し表示する
        outputWaveText = 'まもなく作業ソンをはじめます！心の準備をお願いします！\r\n\r\n'
        for i in range(pomodoroRunCount*2):
            outputWaveText = outputWaveText + strWaveTexts[i] +'\r\n'
        logger.info('ポモドーロセッション開始予定: %s', dtPomodoroStartTime)
        await Sendchannel.send(outputWaveText)

        # 開始時間まで待つ
        dtDiff = dtPomodoroStartTime - dt_now
        time.sleep(dtDiff.seconds)

        # 3回実行する
        for i in range(pomodoroRunCount):

            logger.info('ポモ %d/%d 開始', i+1, pomodoroRunCount)

            # テキストエリア初期化
            outputWaveText = ''
            outputWaveText = outputWaveText + '【' + str(i+1) + 'ポモ目 開始】\r\n\r\n'

            # waveのテキスト作成
            for j in range(pomodoroRunCount*2):

                outputWaveText = outputWaveText + strWaveTexts[j]
                if i == j // 2 and j % 2 == 0 :
                    outputWaveText = outputWaveText +'  ← いまここ'

                outputWaveText = outputWaveText +'\r\n'

            await Sendchannel.send(outputWaveText)

            time.sleep(25*60)

            logger.info('ポモ %d/%d 終了', i+1, pomodoroRunCount)

            if i == 0:
                await Sendchannel.send('1ポモ目終了です。お疲れさまでした！少し休んでくださいね。ストレッチがおすすめです！\r\n\r\n')
                strBreakText = "小"

            elif i == 1:
                await Sendchannel.send('2ポモ目終了です。お疲れさまでした！猫背になってませんか？次おわれば大休憩です！\r\n\r\n')
                strBreakText = "小"

            else:
                await Sendchannel.send('3ポモ目終了です。お疲れさまでした！大休憩です！\r\n\r\n')
                strBreakText = "大"

            outputWaveText = ''
            outputWaveText = '【' + outputWaveText + strBreakText + '休憩 開始】\r\n\r\n'

            # 休憩のテキスト作成
            for j in range(pomodoroRunCount*2):

                outputWaveText = outputWaveText + strWaveTexts[j]
                if i == j // 2 and j % 2 == 1 :
                    outputWaveText = outputWaveText +'  ← いまここ'

                outputWaveText = outputWaveText +'\r\n'

            await Sendchannel.send(outputWaveText)

            if i < pomodoroRunCount - 1:
                time.sleep(5*60)

        logger.info('/yaruzo command completed')


# Botの起動とDiscordサーバーへの接続
try:
    client.run(os.environ['TOKEN'])
except Exception:
    logger.exception('client.run で致命的エラー')
    raise
#client.run(TOKEN)
