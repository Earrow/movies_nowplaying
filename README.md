# movies_nowplaying
定期抓取豆瓣正在热映影片信息和猫眼票房，发送到指定邮箱。

## 运行环境
安装Python3和MongoDB数据库。
安装python库：
```
pip3 install -r requirements.txt
```

## 运行配置
在配置文件config.ini中配置数据库和邮箱相关配置：
```
[database]
host = localhost
port = 27017
database = movie_nowplaying
collection = movies

[mail]
host = smtp.qq.com
pwd = ******
sender = ******@qq.com
receiver = ******@qq.com
```

## 运行方法
```
python3 main.py
```
