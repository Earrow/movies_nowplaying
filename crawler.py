# coding=utf-8

import logging
import time
import random
from configparser import ConfigParser

import requests
from pybloom import ScalableBloomFilter
from pymongo import MongoClient
from parser import ParserDouBan, ParserMaoYan, ParseError


class CrawlerDouBan:
    logger = logging.getLogger('movie_nowplaying.CrawlerDouBan')

    def __init__(self, city):
        """豆瓣页面抓取，抓取正在上映列表和电影介绍页。

        :param city: 抓取影片数据的城市。
        """
        self._url = 'https://movie.douban.com/cinema/nowplaying/{}/'.format(city.lower())
        # 电影列表页请求头
        self._list_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep - alive',
            'Host': 'movie.douban.com',
            'Referer': 'https://movie.douban.com/',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_0) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36'
        }
        # 电影介绍页请求头
        self._info_headers = self._list_headers.copy()
        self._info_headers.update({'Referer': self._url})
        # 用布隆过滤器去重
        self._bf = ScalableBloomFilter()

        cfg = ConfigParser()
        cfg.read('config.ini')
        db_host = cfg.get('database', 'host')
        db_port = cfg.getint('database', 'port')
        db_dbname = cfg.get('database', 'database')
        db_collection = cfg.get('database', 'collection')

        self._db = MongoClient(db_host, db_port)[db_dbname][db_collection]
        for movie in self._db.find({}):
            self.logger.debug('get {} in database'.format(movie['url']))
            self._bf.add(movie['url'])

    def crawl(self):
        """抓取网页。"""
        s = requests.Session()
        # 抓取正在上映列表
        self.logger.debug('getting {}'.format(self._url))
        r = s.get(self._url, headers=self._list_headers)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.logger.exception('get {} error'.format(self._url))
            self.logger.error(r.headers)

            raise StopIteration
        else:
            self.logger.debug('get {} OK'.format(self._url))
            self.logger.debug('request headers: {}'.format(r.request.headers))
            self.logger.debug('response headers: {}'.format(r.headers))

            # 逐个抓取正在上映的电影介绍
            for movie in ParserDouBan.parse_nowplaying_list(r.text):
                self.logger.debug('get movie: {}, link: {}'.format(movie.name, movie.link))
                if movie.link in self._bf:
                    self.logger.debug('find {} in cache, skipped'.format(movie.name))
                else:
                    self.logger.info('get new movie: {}'.format(movie.name))
                    self._bf.add(movie.link)
                    self._db.insert_one({'name': movie.name, 'url': movie.link})

                    try:
                        r = s.get(movie.link, headers=self._info_headers)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError:
                        self.logger.exception('get {} error'.format(movie.link))
                        self.logger.warning(r.headers)
                    except requests.exceptions.ConnectionError:
                        self.logger.exception('get {} error'.format(movie.link))
                    else:
                        self.logger.debug('get movie {} info OK'.format(movie.name))
                        self.logger.debug('response headers: {}'.format(r.headers))
                        release_date, summary, hot_comment = ParserDouBan.parse_movie_info(r.text)

                        yield list(movie) + [release_date, summary, hot_comment]
                    finally:
                        time.sleep(random.randint(2, 6))


class CrawlerMaoYan:
    """猫眼页面抓取，抓取电影票房。"""
    logger = logging.getLogger('movie_nowplaying.CrawlerMaoYan')

    def __init__(self):
        self._url = 'http://piaofang.maoyan.com/?ver=normal'
        self._headers = {
            'Host': 'piaofang.maoyan.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/62.0.3202.75 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'http://piaofang.maoyan.com/dashboard',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Cookie': '_lxsdk_s=b612e13fda305b2dadde4a6974ab%7C%7C2'
        }

    def crawl(self):
        """抓取票房页面。"""
        self.logger.debug('getting {}'.format(self._url))
        r = requests.get(self._url, headers=self._headers)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.logger.exception('get {} error'.format(self._url))
            self.logger.error(r.headers)
        else:
            self.logger.debug('get {} OK'.format(self._url))
            self.logger.debug('request headers: {}'.format(r.request.headers))
            self.logger.debug('response headers: {}'.format(r.headers))

            try:
                return ParserMaoYan.parse_box_office(r.text)
            except ParseError:
                self.logger.error('parse maoyan page error')


if __name__ == '__main__':
    c = CrawlerDouBan('hefei')
