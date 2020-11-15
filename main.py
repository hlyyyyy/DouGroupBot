import sys

from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtCore, QtGui
from PyQt5.Qt import QThread

import dyht
import crawler
from util import DouUtil
#from actions import RespGen
from queue import SimpleQueue, Empty
from datetime import datetime
from actions import RespGen
from mySelectors import NewPostSelector
from util import requestsWrapper
import time
import random

log = DouUtil.log

# 重定向信号
class EmittingStr(QtCore.QObject):
        textWritten = QtCore.pyqtSignal(str)  # 定义一个发送str的信号

        def write(self, text):
            self.textWritten.emit(str(text))
            loop = QEventLoop()
            QTimer.singleShot(1000, loop.quit)
            loop.exec_()

#多线程类
class Thread_reply(QThread):
    def __init__(self, ui, cbstatus = True):
        self.cbstatus = cbstatus
        self.ui = ui
        super().__init__()

    def run(self):
        respGen = RespGen.RespGen()  # 生成回答准备 需要word
        q = SimpleQueue()
        cred = DouUtil.getCred()
        pwd = cred['pwd']  # 账号密码 需要txt
        userName = cred['userName']
        loginReqUrl = 'https://accounts.douban.com/j/mobile/login/basic'

        while True:
            # 计时
            begin_time = datetime.now()

            # s = requests.Session()
            reqWrapper = requestsWrapper.ReqWrapper()
            s = reqWrapper._session
            s.cookies.clear()  # 清除cookies

            if not self.cbstatus:
                if crawler.login(loginReqUrl, pwd, userName, s):
                    DouUtil.flushCookies(s)
                else:
                    time.sleep(180)
                    break

            s.headers.update({
                'Host': 'www.douban.com',
                'Connection': 'keep-alive',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })

            # 输出cookies
            cookies = DouUtil.loadCookies()
            c = ''
            for key, value in cookies.items():
                c += key + '=' + value + '; '
            c += '\n'
            self.ui.textEdit_2.append(c)
            s.cookies.update(DouUtil.loadCookies())  # cookies登录 需要txt

            slctr = NewPostSelector.NewPostSelector(q, reqWrapper)  # 选择需要评论的帖子
            timeToSleep = 5
            combo = 0

            while True:
                loop_time = datetime.now()
                daytime = datetime(loop_time.year, loop_time.month, loop_time.day, 11, 30)  # 白天11.30之前
                nighttime = datetime(loop_time.year, loop_time.month, loop_time.day, 23, 0)  # 晚上23.00之后
                time_gap = (loop_time - begin_time).total_seconds() // 60  # 分钟
                print("programme running time: " + str(time_gap))

                if (loop_time - daytime).total_seconds() > 0 and (loop_time - nighttime).total_seconds() < 0:
                    if time_gap >= 180 + random.randint(0, 10):
                        self.ui.textEdit.append('关闭当前session，开启下一个session\n')
                        s.close()
                        time.sleep(180)
                        break

                q = slctr.select()  # 评论数小于5
                if q.qsize() == 0:
                    # print((loop_time - daytime).total_seconds())
                    # print((loop_time - nighttime).total_seconds())

                    if (loop_time - daytime).total_seconds() > 0 and (loop_time - nighttime).total_seconds() < 0:
                        timeToSleep = random.randint(50, 70)
                    else:
                        timeToSleep = random.randint(600, 900)
                    log.debug("sleep for empty queue: ", timeToSleep)
                    # 输出睡眠时间
                    time.sleep(timeToSleep)

                else:
                    timeToSleep = random.randint(5, 30)
                    # timeToSleep = 5
                log.info("****selection, q size: ", q.qsize(), "timeToSleep: " + str(timeToSleep) + "****")
                try:
                    file = open('resources/record.txt', 'a', encoding='utf-8')
                    recorder = open('resources/histo.txt', "a", encoding='utf-8')

                    while q.qsize() > 0:
                        tup = q.get(timeout=3)
                        question, postUrl, dajie = tup[0], tup[1], tup[2]

                        resp = respGen.getResp(question, dajie)
                        crawler.postCmnt(reqWrapper, postUrl, question, resp)  # 评论
                        # 输出评论
                        self.ui.textEdit.append(question + ' ' + resp + '\n')

                        sleepCmnt = random.randint(20, 30)
                        #
                        time.sleep(sleepCmnt)

                        log.debug("sleep cmnt: ", sleepCmnt)

                        recorder.write(postUrl.split('/')[5] + '\n')
                        record = question + ': ' + resp + '\n'
                        file.write(record)

                except Empty:
                    log.info("Emptied q, one round finished")
                finally:
                    file.close()
                    recorder.close()
                    DouUtil.flushCookies(s)

class DYHT:
    def __init__(self):
        super().__init__()
        self.initUI()
        sys.stdout = EmittingStr(textWritten=self.outputWritten)
        sys.stderr = EmittingStr(textWritten=self.outputWritten)

    def initUI(self):
        self.MainWindow = QMainWindow()
        self.ui = dyht.Ui_MainWindow()
        self.ui.setupUi(self.MainWindow)
        self.MainWindow.show()
        #自动顶贴
        self.ui.pushButton.clicked.connect(self.start_douban)
        #t停止自动顶贴
        self.ui.pushButton_3.clicked.connect(self.stop_douban)
        #更新账号密码
        self.ui.pushButton_2.clicked.connect(self.update_user)

    def outputWritten(self, text):
        # self.textEdit.clear()
        cursor = self.ui.textEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.ui.textEdit.setTextCursor(cursor)
        self.ui.textEdit.ensureCursorVisible()

    def start_douban(self):
        cb = self.ui.checkBox.isChecked()
        self.ui.pushButton.setEnabled(False)
        self.ui.pushButton_2.setEnabled(False)
        self.thread_reply = Thread_reply(self.ui, cbstatus=cb)
        self.thread_reply.start()

    def stop_douban(self):
        self.ui.pushButton.setEnabled(True)
        self.ui.pushButton_2.setEnabled(True)
        self.thread_reply.terminate()


    def update_user(self):
        userName = self.ui.lineEdit.text()
        pwd = self.ui.lineEdit_2.text()
        line = ""
        with open('confidentials/pwd.txt', "w", encoding='utf-8') as user:
            line += 'userName=' + userName + '\n' + 'pwd=' + pwd
            user.write(line)
        user.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dyht = DYHT()
    sys.exit(app.exec_())