# coding=utf-8

import logging.config
import smtplib
import sys
import os

from crawler import CrawlerDouBan, CrawlerMaoYan
from mail_sender import MailSender
from apscheduler.schedulers.blocking import BlockingScheduler

# 配置日志
logging.config.fileConfig(os.path.join(sys.path[0], 'config.ini'))
logger = logging.getLogger('movie_nowplaying')

# 定时任务调度器
sched = BlockingScheduler()

crawler_douban = CrawlerDouBan('hefei')
crawler_maoyan = CrawlerMaoYan()
sender = MailSender()


@sched.scheduled_job('cron', minute='0', hour='8', day_of_week='fri')
def fun():
    contents = []
    movies_box_office = crawler_maoyan.crawl()

    for name, star, region, director, actors, link, release_date, summary, hot_comment in crawler_douban.crawl():
        if movies_box_office and name in movies_box_office:
            content = ('<{name}>\t豆瓣评分: {star}\n{release_days}\t累计票房: {box_office}\t排片占比: {schedule_rate}\n'
                       '上映时间: {release_date}\n地区: {region}\n导演: {director}\n主演: {actors}\n简介: {summary}\n'
                       '热门短评: \n{comments}').format(
                name=name, box_office=movies_box_office[name][0], release_date=release_date,
                release_days=movies_box_office[name][1], schedule_rate=movies_box_office[name][2],
                region=region, star=star, director=director, actors=actors, summary=summary,
                comments='\n'.join('>>> ' + c for c in hot_comment))
        else:
            content = ('<{name}>\t{star}\n上映时间: {release_date}\n地区: {region}\n导演: {director}\n主演: {actors}\n'
                       '简介: {summary}\n热门短评: \n{comments}').format(
                name=name, release_date=release_date, region=region, star=star, director=director, actors=actors,
                summary=summary, comments='\n'.join('>>> ' + c for c in hot_comment))
        contents.append(content)

    if contents:
        try:
            sender.send('豆瓣正在上映电影更新', '\n\n\n'.join(contents))
        except smtplib.SMTPException:
            logger.exception('邮件发送失败')
        else:
            logger.info('sent mail successfully, movies updated number: {}'.format(len(contents)))
    else:
        logger.debug('no movies updated')


sched.start()
