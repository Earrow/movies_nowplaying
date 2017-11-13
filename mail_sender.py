# coding=utf-8

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from configparser import ConfigParser


class MailSender:
    def __init__(self):
        cfg = ConfigParser()
        cfg.read('config.ini')

        self._host = cfg.get('mail', 'host')
        self._pwd = cfg.get('mail', 'pwd')
        self._sender = cfg.get('mail', 'sender')
        self._receiver = cfg.get('mail', 'receiver')

    def send(self, subject, content):
        """发送邮件。

        :param subject: 主题。
        :param content: 内容。
        """
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = Header(self._sender, 'utf-8')
        msg['To'] = Header(self._receiver, 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')

        smtp = smtplib.SMTP_SSL(self._host)
        smtp.ehlo(self._host)
        smtp.login(self._sender, self._pwd)
        smtp.sendmail(self._sender, self._receiver, msg.as_string())
        smtp.quit()


if __name__ == '__main__':
    sender = MailSender()
    sender.send('发件测试', '这是一封测试邮件功能的邮件')
