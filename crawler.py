import requests
from lxml import etree
import time
import random
from queue import SimpleQueue, Empty
from datetime import datetime

from util import DouUtil
from actions import RespGen
from mySelectors import NewPostSelector
from util import requestsWrapper
import re

import chaojiying

log = DouUtil.log


def get_headers(fileName=None):
    name = 'headers.txt'
    if (fileName is not None):
        name = fileName
    name = 'resources/' + name
    headers = {}
    with open(name, "r", encoding='utf-8') as f_headers:
        hdrs = f_headers.readlines()
    for line in hdrs:
        key, value = line.split(": ")
        headers[key] = value.strip()
    return headers


def login(url, pwd, userName, session):
    loginData = {'ck': '', 'name': userName,
                 'password': pwd, 'remember': 'true', 'ticket': ''}

    loginHeaders = get_headers('login_headers.txt')
    l0 = session.get(url, headers=loginHeaders)
    l = session.post(url, data=loginData, headers=loginHeaders)

    if l.json()['status'] == 'success':#l.status_code == requests.codes['ok'] or l.status_code == requests.codes['found']:
        print("Login Successfully")
        return True
    else:
        print("Failed to Login")
        log.error("Failed to Login", l.status_code)
        session.close()
        return False


def composeCmnt(session, response):
    #cmntForm = {'ck': '', 'rv_comment': response['ans'],
    #            'start': 0, 'submit_btn': '发送'}
    cmntForm = {'ck': '', 'rv_comment': response,
                'start': 0, 'submit_btn': '发送'}
    cmntForm['ck'] = DouUtil.getCkFromCookies(session)
    return cmntForm


def prepareCaptcha(data, session, postUrl, r=None) -> dict:
    pic_url, pic_id = DouUtil.getCaptchaInfo(session, postUrl, r)
    verifyCode = ''
    pic_path = DouUtil.save_pic_to_disk(pic_url, session)
    log.debug(pic_url, pic_path)
    verifyCode = DouUtil.getTextFromPic(pic_path)
    return data


def postCmnt(session, postUrl, request, response):
    # 设置超级鹰
    CHAOJIYING_USERNAME = 'hly3891935'
    CHAOJIYING_PASSWORD = '3891935.hly'
    CHAOJIYING_SOFT_ID = 907319
    CHAOJIYING_KIND = 3008
    CHAOJIYING = chaojiying.Chaojiying_Client(CHAOJIYING_USERNAME, CHAOJIYING_PASSWORD, CHAOJIYING_SOFT_ID)

    data = composeCmnt(session._session, response)

    html = session.get(postUrl).text #需要评论的帖子
    r1 = re.compile(r'captcha.*?src="(.*?)"')   #验证码
    pic = re.findall(r1, html)
    #有验证码
    if pic:
        dd = pic[0].split('=')[-1]
        data['captcha-id'] = dd#re.findall('id=(.*?)&', pic[0])[0]
        with open('captcha/' + dd.split(':')[0] + '.jpg', 'wb') as f:
            f.write(session.get('https:' + pic[0]).content)
            print("%s下载完成" % pic)
        im = open('captcha/' + dd.split(':')[0] + '.jpg', 'rb').read()
        data['captcha-solution'] = CHAOJIYING.PostPic(im, CHAOJIYING_KIND)['pic_str']

    cmntUrl = postUrl + 'add_comment'
    r = session.post(cmntUrl, data=data, headers={'Referer': postUrl})#, files=response.get('files'))
    # r = session.get(postUrl)
    code = str(r.status_code)
    success = str(r.url).split('/')[-1]

    if (code.startswith('4') or code.startswith('5')) and not code.startswith('404'):
        log.error(r.status_code)
        raise Exception
    else:
        log.info("Success.", request + '  --' + data['rv_comment'])
    '''
    elif success == 'add_comment':
        log.warning(r.status_code)
        data = prepareCaptcha(data, session, postUrl, r)
        r = session.post(cmntUrl, data=data)
        success = str(r.url).split('/')[-1]
        retry = 1
        while success == 'add_comment':
            if retry <= 0:
                retry -= 1
                break
            data = prepareCaptcha(data, session, postUrl, r)
            r = session.post(cmntUrl, data=data)
            success = str(r.url).split('/')[-1]
            retry -= 1

        if retry < 0:
            log.error(r.status_code)
            #DouUtil.alertUser()
            pic_url, pic_id = DouUtil.getCaptchaInfo(session, postUrl, r)
            #code = DouUtil.callAdmin(session, pic_url, postUrl)
            # data.update({'captcha-solution': code, 'captcha-id': pic_id})

            r = session.post(cmntUrl, data=data)
            success = str(r.url).split('/')[-1]
            if success == 'add_comment':
                raise Exception

        log.info("Success.", request + '  --' + data['rv_comment'])
    '''


def main():
    respGen = RespGen.RespGen() #生成回答准备 需要word
    q = SimpleQueue()
    cred = DouUtil.getCred()
    pwd = cred['pwd']#账号密码 需要txt
    userName = cred['userName']
    loginReqUrl = 'https://accounts.douban.com/j/mobile/login/basic'

    while True:
        #计时
        begin_time = datetime.now()

        # s = requests.Session()
        reqWrapper = requestsWrapper.ReqWrapper()
        s = reqWrapper._session
        s.cookies.clear()   #清除cookies

        '''
        if login(loginReqUrl, pwd, userName, s):
            DouUtil.flushCookies(s)
        else:
            time.sleep(180)
            break
        '''

        s.headers.update({
            'Host': 'www.douban.com',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

        s.cookies.update(DouUtil.loadCookies())#cookies登录 需要txt

        slctr = NewPostSelector.NewPostSelector(q, reqWrapper)#选择需要评论的帖子
        timeToSleep = 5
        combo = 0

        while True:
            loop_time = datetime.now()
            daytime = datetime(loop_time.year, loop_time.month, loop_time.day, 11, 30)    #白天11.30之前
            nighttime = datetime(loop_time.year, loop_time.month, loop_time.day, 23, 0)   #晚上23.00之后
            time_gap = (loop_time-begin_time).total_seconds()//60   #分钟
            print("programme running time: " + str(time_gap))

            if (loop_time - daytime).total_seconds() > 0 and (loop_time - nighttime).total_seconds() < 0:
                if time_gap >= 180 + random.randint(0, 10):
                    s.close()
                    time.sleep(180)
                    break

            q = slctr.select()  #评论数小于5
            if q.qsize() == 0:
                #print((loop_time - daytime).total_seconds())
                #print((loop_time - nighttime).total_seconds())
                #w32
                if (loop_time - daytime).total_seconds() > 0 and (loop_time - nighttime).total_seconds() < 0:
                    timeToSleep = random.randint(50, 70)
                else:
                    timeToSleep = random.randint(600, 900)
                log.debug("sleep for empty queue: ", timeToSleep)
                time.sleep(timeToSleep)
            else:
                timeToSleep = random.randint(5, 30)
                #timeToSleep = 5
            log.info("****selection, q size: ", q.qsize(), "timeToSleep: " + str(timeToSleep) + "****")
            try:
                file = open('resources/record.txt', 'a', encoding='utf-8')
                recorder = open('resources/histo.txt', "a", encoding='utf-8')

                while q.qsize() > 0:
                    tup = q.get(timeout=3)
                    question, postUrl, dajie = tup[0], tup[1], tup[2]

                    resp = respGen.getResp(question, dajie)
                    postCmnt(reqWrapper, postUrl, question, resp)   #评论

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


if __name__ == '__main__':
    main()
