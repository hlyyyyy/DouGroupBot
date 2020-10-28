# 豆瓣小组机器人

最近给朋友做了一个豆瓣小组自动评论机器人，使用 requests 与 lxml 库，在控制刷新频率的情况下，基本能做到头排评论。除了爬虫的这一部分，还很重要的是要能对帖子回复有趣的内容。

## 基本功能

同时支持 cookie登录以及账号密码登录。建议尽量使用 cookie，密码登录过多会有验证码阻碍，并有异常行为导致封号的危险。支持自动更新 cookie，总是保持使用的 cookie最新。

通过 XPath 快速解析返回的HTML。有心的朋友可以benchmark一下beautiful soup 和 XPath 表达式之间的速度差异。Python 官方的 [XPath 文档](https://docs.python.org/3/library/xml.etree.elementtree.html#supported-xpath-syntax)其实就很清晰了，推荐一读。在获得服务器返回的HTML和准备好回复内容之间的时间，都是不必要的对用户的延迟，速度很重要。

经过实践调试的最佳动态睡眠，在帖子多的情况下开足马力，帖子少时长时间休眠，并在有新帖出现后快速恢复。同时每次评论后随机睡眠，保证功能的情况下尽量降低服务器请求次数，保护账号，保护阿北。（珍惜阿北人人有责）

拥有智能图像识别接口，识别验证码，可接入任何OCR模块。目前知名的开源识别库为 [Tesseract](https://tesseract-ocr.github.io/tessdoc/Home.html)，然而并不保证效果。

### 自动回复

自动回复单独说一下。自动回复的原理就是发出 `post` 请求。请求的 URL 地址就是帖子的URL加上 add_comment。带不带最后的 #last 无所谓。注意编码问题，如果回复内容来自外部文件，注意转换为 UTF-8 编码。注意 POST 需要带上所有 `hidden` 的元素的值。不了解的可以看看HTML中关于 `form` 元素的知识。

抢头排除了速度以外，还需要记录已经评论过的帖子，避免重复评论。这就需要持久化，最开始可以写入 csv 甚至普通 text 文件。要注意一定在评论完之后才写入本地。这里用来区别的key可以直接用帖子的 href。即使把几千条同时载入内存作为字典，也是绰绰有余的。

帖子的回复内容也很关键，毕竟这不是单纯的爬虫程序，是一个有感情的 bot。至少，要有自己的语录库，从中随机挑选语录。更加高级有针对性的自然语言处理聊天bot是进阶的功能。

## 经验总结

1. requests 的 Session 相当好用，可以自动长连接、自动更新 cookie。
2. session 不足在于，对于请求没有重试的功能。是的你没看错。当网络环境差的时候，会频繁遇到来自底层 urllib 形形色色的报错，requests 统一将其抽象为 `requests.ConnectionError` 。建议从一开始就在项目中使用自己对 `requests.Session` 的封装，对每次请求封装重试逻辑，并且实现为单例模式。
3. 注意隐私保护，不要将密码上传至 ~~GayHub~~ GitHub。
4. 一开始就有意识地模块化，不需要很详细，毕竟提前优化是万恶之源，但是一定的模块化的确是递增式扩展程序的必经之路



## 免责声明

谨慎使用，遵守网站规定与法律法规，对造成任何后果概不负责。请爱惜网站服务器，也是在爱惜自己的豆瓣账号。



---

## 进阶 TODO

- [ ] 多线程
- [ ] 完全的生产者-消费者模式
- [x] 接入自然语言处理接口
- [x] 接入OCR接口

## 大虞海棠专组tips

### 运行指南
```
1. 先在resources/文件夹下创建histo.txt、record.txt两个空文件
2. 在网页上登录豆瓣账号，F12获取cookies中所需元素（具体见resources/cookies.txt），并将其填入resources/cookies.txt
3. mySelectors/NewPostSelector.py中39行 if cnt > ? 可以更改筛选条件
4. 支持账号密码登录，在confidentials/pwd.txt中输入账号密码
5. 更新功能：先使用账号密码登录，自动获取登录后的cookie，之后每两个半小时重新登录一次，获取新的cookie
6. 拟更新功能：夜晚休眠时间调整
```

### 部署指南
```
# 避免解析cookies文件时，文本内容包括\n
echo -n "bid=""; ck=; dbcl2=""" >> resources/cookies.txt

# 启动后台程序
nohup python3 crawler.py > output.log &
# 结束后台程序
pkill -f crawler.py
```
