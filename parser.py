# coding=utf-8

import re
import base64
from collections import namedtuple
from tempfile import NamedTemporaryFile

import utils
from lxml import html
from fontTools.ttLib import TTFont


class ParseError(Exception):
    """解析页面出错。"""
    pass


class ParserDouBan:
    """豆瓣页面解析，获取正在上映电影及介绍。"""

    @staticmethod
    def parse_nowplaying_list(nowplaying_doc):
        """解析正在上映页，获取正在上映的各电影基础信息及介绍链接。

        :param nowplaying_doc: 正在上映页面内容。
        :return: generator of Movie which is (name, score, region, director, actors, link)
        """
        Movie = namedtuple('Movie', 'name score region director actors link')

        tree = html.fromstring(nowplaying_doc)
        # 正在上映电影列表
        movies = tree.xpath('//div[@id="nowplaying"]//ul[@class="lists"]/li')

        for movie in movies:
            name = movie.xpath('./@data-title')[0]
            score = movie.xpath('./@data-score')[0]
            region = movie.xpath('./@data-region')[0]
            director = movie.xpath('./@data-director')[0]
            actors = movie.xpath('./@data-actors')[0]
            link = movie.xpath('.//li[@class="stitle"]/a/@href')[0]

            m = Movie(name, score, region, director, actors, link)
            yield m

    @staticmethod
    def parse_movie_info(movie_info_doc):
        """解析电影介绍页面，提取上映日期、简介、热门短评。

        :param movie_info_doc: 电影介绍页面内容。
        :return: tuple of release_date and summary
        """
        tree = html.fromstring(movie_info_doc)
        # 上映日期结尾带有地区，如 2017-10-20(中国大陆)。这里去掉后面的地区只保留时间
        release_date = tree.xpath('//span[@property="v:initialReleaseDate"][position()=1]/text()')[0].split('(')[0]
        # 对简介的每一段去掉首尾空白，并在段之间添加换行
        summary = '\n'.join([text.strip() for text in tree.xpath('//span[@property="v:summary"]/text()')])
        hot_comment = [comment.strip() for comment in tree.xpath('//p[@class=""]/text()') if comment.strip()]

        return release_date, summary, hot_comment


class ParserMaoYan:
    """猫眼页面解析，获取电影票房。"""

    @staticmethod
    def parse_box_office(box_office_doc):
        """解析猫眼票房页面，获取各正在上映影片的累计票房。

        :param box_office_doc: 页面内容。
        :return: dict of movie name and box office
        :raise: ParseError if parse html doc failed
        """
        tree = html.fromstring(box_office_doc)
        font_face_style = tree.xpath('//style[@id="js-nuwa"]/text()')[0]
        try:
            font_face = re.match(r'.*base64,(.*)\) format.*', font_face_style, re.S).group(1)
        except AttributeError:
            raise ParseError('parse font-face failed')

        # 数字字符和数字的映射
        real_numbers = ParserMaoYan._parse_font_face(font_face)

        # 片名
        movies_name = tree.xpath('//li[@class="c1"]/b/text()')
        # 票房
        movies_box_office = tree.xpath('//li[@class="c1"]//i[@class="cs"]/text()')
        # 上映时长
        movies_released_days = tree.xpath('//li[@class="c1"]//i[@class="font-orange"]/text() | '
                                          '//li[@class="c1"]//em/text()')
        # 排片占比
        movies_schedule_rate = tree.xpath('//li[@class="c4 "]/i/text()')

        movies = {}
        for movie_name, movie_box_office, movie_released_days, movie_schedule_rate in zip(
                movies_name, movies_box_office, movies_released_days, movies_schedule_rate):
            movies[movie_name] = (utils.multiple_replace(movie_box_office, real_numbers), movie_released_days,
                                  utils.multiple_replace(movie_schedule_rate, real_numbers))

        return movies

    @staticmethod
    def _parse_font_face(font_face):
        """解析unicode值和十进制数字的映射。

        猫眼使用font_face进行反爬虫，html中的数字都是类似'&#xe4f9'这样的字符，这些字符和数字的映射被定义在字体文件中，
        经过渲染会显示为正常的数字。
        有两种方式应对这种反爬虫方式：1.解析字体文件，分析出映射关系；2.对网页截图，进行OCR。 这里使用第一种方法。

        字体文件被定义在页面上，是一串base64编码的字符串。对其解码后使用fontTools工具解析，获取glyph order，即是映射关系。

        :param font_face: 编码后的字体文件字符串
        :return: dict of unicode and number string
        """
        font_data = base64.b64decode(font_face)
        with NamedTemporaryFile('w+b') as fp:
            fp.write(font_data)
            fp.seek(0)

            font = TTFont(fp.name)

            # getGlyphOrder()返回这样的列表：['glyph00000', 'x', 'uniEFD3', 'uniEC6A', 'uniE4F9', 'uniF8F3', 'uniF324',
            #  'uniE7F7', 'uniE711', 'uniF1C9', 'uniE21D', 'uniF1D7']
            #
            # 除去前两个元素，索引和元素值既是我们需要的映射关系，第三个元素对应0，第四个元素对应1...
            # 将其转换为{'\uefd3': '0', '\uec6a': '1', '\ue4f9': '2', '\uf8f3': '3', '\uf324': '4', '\ue7f7': '5',
            #  '\ue711': '6','\uf1c9': '7', '\ue21d': '8', '\uf1d7': '9'}这样的字典return出去
            return {eval("u\"" + '\\u' + value.split('uni')[-1].lower() + "\""): str(key) for key, value
                    in dict(enumerate(font.getGlyphOrder()[2:])).items()}


if __name__ == '__main__':
    p = ParserMaoYan()
    with open('maoyan.html') as fp:
        try:
            print((p.parse_box_office(fp.read())))
        except ParseError:
            print('get e')
