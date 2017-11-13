# coding=utf-8

"""定义一些工具函数。"""

import re


def multiple_replace(text, replacer):
    """替换字符串中的多个子字符串。

    原始字符串中如果包含替换规则字典中的键，会将其替换为该键对应的值，否则无操作。

    Usage::
        >>> multiple_replace('1122', {'1':'3', '2': '4'})
        '3344'

    :param text: 要进行替换操作原始字符串。
    :type text: string
    :param replacer: 替换规则字典，其中的键是要替换的子字符串，对应的值是要替换成的字符串。
    :type replacer: dict of string
    :return 替换后的结果字符串。
    :rtype string
    :raise TypeError if any key or value in replacer is not a string
    """
    pattern = re.compile('|'.join(replacer.keys()))

    return pattern.sub(lambda m: replacer[m.group(0)], text)
