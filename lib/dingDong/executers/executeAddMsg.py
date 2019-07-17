# (c) 2017-2019, Tal Shany <tal.shany@biSkilled.com>
#
# This file is part of dingDong
#
# dingDong is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dingDong is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dingDong.  If not, see <http://www.gnu.org/licenses/>.

import time
import os
import smtplib
from collections            import OrderedDict
from email.mime.multipart   import MIMEMultipart
from email.mime.text        import MIMEText

from dingDong.config        import config
from dingDong.misc.logger   import LOGGER_OBJECT,p
from dingDong.executers.executeHTMLReport import eHtml, createHtmlFromList

class msgProp (object):
    STEP_NUM    = "STEP NUMBER"
    DESC        = "DESCRIPTION"
    TS          = "TIME STAMP"
    STEP_TIME   = "TOTAL TIME CURRENT STEP"
    TOTAL_TIME  = "TOTAL TIME"

    MSG_SUBJECT_SUCCESS = "LOADING JOB %s "
    MSG_SUBJECT_FAILURE = "ERROR LOADING JOB %s "
    MSG_LAST_STEP       = "TOTAL EXECUTION  "

    _TIME_FORMAT = "%m/%d/%Y %H:%M:%S"
    _PREFIX_DESC = "STATE_"

class executeAddMsg (object):

    def __init__ (self, timeFormat=msgProp._TIME_FORMAT, sDesc=msgProp._PREFIX_DESC ):
        self.startTime  = time.time()
        self.lastTime   = self.startTime
        self.stateDic   = OrderedDict()
        self.loggClass  = LOGGER_OBJECT
        self.timeFormat = timeFormat
        self.stateCnt   = 0
        self.sDesc      = sDesc
        self.inProcess  = False

    def addState (self, sDesc=None):
        self.stateCnt+=1
        if not sDesc:
            sDesc="%s%s" %(str(self.sDesc),str(self.stateCnt))
        ts = time.time()
        tsStr = time.strftime(self.timeFormat, time.localtime(ts))
        tCntFromStart   = str(round ( ((ts - self.startTime) / 60) , 2))
        tCntFromLaststep= str(round ( ((ts - self.lastTime) / 60) , 2))
        self.lastTime   = ts
        self.stateDic[self.stateCnt] = OrderedDict({msgProp.STEP_NUM   : self.stateCnt,
                                        msgProp.DESC       :sDesc,
                                        msgProp.TS         :tsStr,
                                        msgProp.STEP_TIME  :tCntFromLaststep,
                                        msgProp.TOTAL_TIME :tCntFromStart })

    def deleteOldLogFiles (self, days=5 ):
        logsDir = self.loggClass.getLogsDir()
        if logsDir:
            now = time.time()
            old = now - (days * 24 * 60 * 60)
            for f in os.listdir(logsDir):
                path = os.path.join(logsDir, f)
                if os.path.isfile(path):
                    stat = os.stat(path)
                    if stat.st_mtime < old:
                        self.logg.info("DELETE FILE %s" %(path))
                        os.remove(path)

    def end(self, msg=None,pr=True):
        msg = msg if msg else msgProp.MSG_LAST_STEP
        self.addState(sDesc=msg)

        if pr:
            for col in self.stateDic:
                p (list(self.stateDic[col].values()))

    def sendSMTPmsg (self, msgName, onlyOnErr=False, withErr=True, ):

        okMsg = msgProp.MSG_SUBJECT_SUCCESS %(msgName)
        errMsg= msgProp.MSG_SUBJECT_FAILURE %(msgName)

        errList = self.loggClass.getLogData ()
        errCnt  = len(errList) if errList else 0

        htmlList = []
        msgSubj  = okMsg if errCnt<1 else errMsg

        if onlyOnErr and errCnt>0 or not onlyOnErr:
            # First table - general knowledge
            self.addState(sDesc='')

            headerNames = None
            dicFirstTable = {eHtml.HEADER:[],eHtml.ROWS:[]}


            for st in self.stateDic:
                if not headerNames:
                    headerNames = list(self.stateDic[st].keys())
                    dicFirstTable[eHtml.HEADER] = headerNames

                dicFirstTable[eHtml.ROWS].append ( list(self.stateDic[st].values()) )

            htmlList.append (dicFirstTable)
            if withErr:
                # 2nd table - errors tables
                dicFirstTable = {eHtml.HEADER: ['Error Desc'],
                                 eHtml.ROWS: []}
                for err in errList:
                    dicFirstTable[eHtml.ROWS].append ( [err] )

                htmlList.append(dicFirstTable)

            msgHtml = createHtmlFromList(htmlList=htmlList, htmlHeader=msgName)
            self.__sendSMTP(msgSubj=msgSubj, msgHtml=msgHtml)

    def __sendSMTP (self, msgSubj, msgHtml=None, msgText=None):
        sender          = config.SMTP_SENDER
        receivers       = ", ".join(config.SMTP_RECEIVERS)
        receiversList   = config.SMTP_RECEIVERS
        serverSMTP      = config.SMTP_SERVER
        serverUsr       = config.SMTP_SERVER_USER
        serverPass      = config.SMTP_SERVER_PASS

        msg = MIMEMultipart('alternative')
        msg['Subject']  = msgSubj
        msg['From']     = sender
        msg['To']       = receivers

        if msgText:
            textInMail = ''
            if isinstance(msgText, list):
                for l in msgText:
                    textInMail += l + "\n"
            else:
                textInMail = msgText

            msg.attach(MIMEText(textInMail, 'plain'))

        if msgHtml and len(msgHtml)>0:
            msg.attach( MIMEText(msgHtml, 'html') )

        try:
            server = smtplib.SMTP(serverSMTP)
            server.ehlo()
            server.starttls()

            server.login(serverUsr, serverPass)
            server.sendmail(sender, receiversList, msg.as_string())
            server.quit()
        except smtplib.SMTPException:
            err = "gFunc->sendMsg: unable to send email to %s, subject is: %s " % (str(receivers), str(msgSubj))
            raise ValueError(err)