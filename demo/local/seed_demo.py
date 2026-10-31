#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BBS 本地演示数据种子（只写独立库 bbs_local_codex）

设计约束（与 run.py 保持一致）：
  · 固定连接本机 localhost / 127.0.0.1，固定库名 bbs_local_codex；没有“库名参数”
  · 运行时读取后端 .env 的连接配置，但绝不打印账号、密码或 .env 内容
  · 不 DROP、不 TRUNCATE、不清库、不 UPDATE/DELETE 既有用户内容
  · 只新增专用 demo_* 演示账号、演示帖子，以及关联的评论 / 点赞 / 收藏 / 关注
  · 固定用户名 + 固定标题/评论内容作为自然键，重复执行不会重复插入
  · 图片全部复用 D:\\项目\\BBS 里的本地静态吧图，不访问外网
  · 全部数据库写入放在一个事务里，失败整体回滚

用法（用后端虚拟环境的 Python 运行）：
    D:\\项目\\BBS\\bbs-app-backend\\.venv\\Scripts\\python.exe bbs-local\\seed_demo.py
    D:\\项目\\BBS\\bbs-app-backend\\.venv\\Scripts\\python.exe bbs-local\\seed_demo.py --check

--check 只做只读检查：不建目录、不复制图片、不写数据库。
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
import shutil
import sys
from pathlib import Path

import pymysql
from dotenv import dotenv_values

# =============================================================================
# 固定路径 / 固定库名
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "bbs-app-backend"
ENV_FILE = BACKEND_DIR / ".env"
STATIC_BARS_DIR = BACKEND_DIR / "static" / "images" / "bars"

DEPLOY_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = DEPLOY_DIR / "uploads"
DEMO_IMAGE_DIR = UPLOAD_DIR / "posts" / "demo_seed"

LOCAL_DB = "bbs_local_codex"
ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
PBKDF2_ITERATIONS = 200_000
SEED_LOCK = "bbs_local_demo_seed_v1"

# 演示凭据只写在 bbs-demo-guide.md；本脚本不打印密码。
DEMO_PASSWORD = "Demo@2026"
DEMO_ADMIN_PASSWORD = "DemoAdmin@2026"

REQUIRED_TABLES = (
    "users",
    "bars",
    "posts",
    "post_images",
    "comments",
    "likes",
    "favorites",
    "follows",
    "footprints",
    "notify_read",
)

# =============================================================================
# 演示账号（全部使用 demo_ 前缀，避免和真实用户重名；已存在则只复用、绝不改角色/密码）
# =============================================================================
DEMO_USERS = [
    ("demo_lin", "林小满", "/static/avatars/avatar-1.png"),
    ("demo_zhou", "周舟", "/static/avatars/avatar-2.png"),
    ("demo_qi", "齐悦", "/static/avatars/avatar-3.png"),
    ("demo_tang", "唐豆豆", "/static/avatars/avatar-4.png"),
    ("demo_mao", "毛球", "/static/avatars/avatar-5.png"),
    ("demo_yu", "余声", "/static/avatars/avatar-6.png"),
    ("demo_su", "苏叶", "/static/avatars/avatar-7.png"),
    ("demo_chen", "陈一页", "/static/avatars/avatar-8.png"),
]
DEMO_ADMIN = ("demo_admin", "演示管理员", "/static/avatars/default.png")

# 关注的吧（按吧名解析，避免依赖自增 id）
DEMO_FOLLOWS = {
    "demo_lin": ["前端吧", "科技吧", "旅游吧", "读书吧"],
    "demo_zhou": ["前端吧", "游戏吧", "足球吧", "跑步吧"],
    "demo_qi": ["美食吧", "摄影吧", "烘焙吧", "旅游吧"],
    "demo_tang": ["美食吧", "养猫吧", "烘焙吧", "电影吧"],
    "demo_mao": ["游戏吧", "养猫吧", "手工吧", "美食吧"],
    "demo_yu": ["电影吧", "音乐吧", "吉他吧", "读书吧"],
    "demo_su": ["读书吧", "音乐吧", "科技吧", "吉他吧", "跑步吧"],
    "demo_chen": ["前端吧", "游戏吧", "科技吧", "钓鱼吧"],
    "demo_admin": ["前端吧", "美食吧"],
}

# 足迹（只写演示账号自己的足迹；重复执行由唯一键忽略）
DEMO_FOOTPRINTS = {
    "demo_lin": ["前端吧", "科技吧", "旅游吧"],
    "demo_mao": ["养猫吧", "手工吧"],
    "demo_yu": ["电影吧", "音乐吧"],
}

# =============================================================================
# 20 篇演示帖子：标题是固定自然键；评论内容也是固定自然键
#   image_bars: 复用后端 static/images/bars/bar-N.jpg
# =============================================================================
DEMO_POSTS = [
    {
        "bar": "前端吧",
        "author": "demo_lin",
        "tag": "技术交流",
        "title": "三年后再看 useEffect：我把踩过的坑整理成了清单",
        "content": (
            "刚工作时只会把 useEffect 当成 componentDidMount 用，结果依赖数组、闭包和"
            "竞态问题轮番上课。\n\n这次重新梳理了一遍，按「什么时候不该用」「依赖怎么写」"
            "「清理函数到底清理什么」三块做了清单，也贴了几个真实项目里的改法。\n\n"
            "最想提醒新同学的一句：先问自己这是不是在同步外部系统，如果不是，大概率不需要 Effect。"
        ),
        "image_bars": [1],
        "hours_ago": 2,
        "views": 186,
        "forward_count": 3,
        "likes": ["demo_zhou", "demo_qi", "demo_chen"],
        "favorites": ["demo_zhou"],
        "comments": [
            {
                "author": "demo_zhou",
                "text": "依赖数组里放对象那段太真实了，我也踩过。",
                "likes": ["demo_lin", "demo_qi"],
            },
            {
                "author": "demo_chen",
                "text": "建议补一条：开发环境 StrictMode 下执行两次不是 bug。",
            },
            {
                "author": "demo_qi",
                "text": "收藏了，下周组内分享直接抄作业。",
            },
        ],
    },
    {
        "bar": "科技吧",
        "author": "demo_chen",
        "tag": "数码",
        "title": "从 0 搭了一台静音 NAS，附完整配件清单和功耗实测",
        "content": (
            "需求很简单：存照片、跑下载、偶尔当个家庭影音库，但必须安静。\n\n"
            "最后选了低功耗平台 + 两块机械盘 + 一个静音风扇，待机功耗和满载功耗都做了记录。"
            "机箱放在书桌下面，晚上基本听不到声音。\n\n配件清单和踩坑点都写在正文里了，"
            "有同样需求的朋友可以直接按这个思路配。"
        ),
        "image_bars": [8],
        "hours_ago": 5,
        "views": 342,
        "forward_count": 6,
        "likes": ["demo_lin", "demo_su", "demo_yu"],
        "favorites": ["demo_lin"],
        "comments": [
            {
                "author": "demo_lin",
                "text": "功耗待机多少瓦？想放卧室又怕吵。",
                "likes": ["demo_chen"],
            },
            {
                "author": "demo_su",
                "text": "硬盘选的哪款？最近正好在看。",
            },
        ],
    },
    {
        "bar": "美食吧",
        "author": "demo_tang",
        "tag": "菜谱",
        "title": "复刻学校后街那碗牛肉面，汤底我熬了四个小时",
        "content": (
            "毕业后最想念的不是食堂，是后街那家没有招牌的牛肉面。\n\n"
            "这次从牛骨焯水开始，加了八角、桂皮、香叶和一小块陈皮，小火慢熬四个小时。"
            "牛肉单独卤，最后切厚片铺在面上，再卧一个溏心蛋。\n\n"
            "味道不敢说一模一样，但第一口下去，确实回到了那个冬天。"
        ),
        "image_bars": [2],
        "hours_ago": 8,
        "views": 221,
        "forward_count": 1,
        "likes": ["demo_qi", "demo_mao", "demo_lin"],
        "favorites": ["demo_qi"],
        "comments": [
            {
                "author": "demo_qi",
                "text": "看饿了，求香料比例。",
                "likes": ["demo_tang"],
            },
            {
                "author": "demo_mao",
                "text": "那个溏心蛋是点睛之笔。",
            },
        ],
    },
    {
        "bar": "养猫吧",
        "author": "demo_mao",
        "tag": "日常",
        "title": "捡到的小橘第一次主动睡在我腿上，纪念一下",
        "content": (
            "上个月在楼下捡到的小橘，刚来的时候躲在沙发底下两天不出来。\n\n"
            "这周开始会跟着我走来走去，今天下午我坐在沙发上看书，它跳上来闻了闻，"
            "然后直接在我腿上睡着了。\n\n不敢动，腿麻也值了。"
        ),
        "image_bars": [11],
        "hours_ago": 11,
        "views": 508,
        "forward_count": 2,
        "likes": ["demo_lin", "demo_tang", "demo_qi", "demo_su"],
        "favorites": ["demo_tang"],
        "comments": [
            {
                "author": "demo_lin",
                "text": "小橘好有安全感，说明你把它照顾得很好。",
                "likes": ["demo_mao", "demo_tang"],
            },
            {
                "author": "demo_tang",
                "text": "恭喜转正，铲屎官。",
            },
            {
                "author": "demo_qi",
                "text": "照片呢照片呢，蹲一张正脸。",
            },
        ],
    },
    {
        "bar": "电影吧",
        "author": "demo_yu",
        "tag": "影评",
        "title": "重看《海上钢琴师》：这次我注意到的全是镜头外的声音",
        "content": (
            "第一次看的时候只顾着剧情，这次戴耳机重看，发现整部片子的环境声特别讲究。\n\n"
            "海浪、船舱的金属声、人群的喧闹，和钢琴声之间一直有一种若即若离的关系。"
            "1900 不下船的选择，放到今天看依然很难用一句“逃避”概括。\n\n"
            "好的电影大概就是这样，隔几年再看，注意到的全是不一样的东西。"
        ),
        "image_bars": [4],
        "hours_ago": 14,
        "views": 163,
        "forward_count": 1,
        "likes": ["demo_su", "demo_chen"],
        "favorites": ["demo_su"],
        "comments": [
            {
                "author": "demo_su",
                "text": "这部每次看都会有新的理解。",
            },
        ],
    },
    {
        "bar": "读书吧",
        "author": "demo_su",
        "tag": "书评",
        "title": "读完《置身事内》，我终于把地方债那章看明白了",
        "content": (
            "这本书放了很久才翻开，结果一读就停不下来。\n\n"
            "作者把很多新闻里听过但没真正理解的词，放回了具体的地方政府和城投平台里讲。"
            "地方债那一章我做了满满两页笔记，终于知道那些数字是怎么转起来的。\n\n"
            "不是那种读完就忘的畅销书，值得慢慢读。"
        ),
        "image_bars": [5],
        "hours_ago": 20,
        "views": 97,
        "forward_count": 0,
        "likes": ["demo_chen", "demo_yu"],
        "favorites": ["demo_chen"],
        "comments": [
            {
                "author": "demo_chen",
                "text": "这本书把很多新闻里的词串起来了。",
            },
            {
                "author": "demo_yu",
                "text": "求下一本推荐，想接着读。",
            },
        ],
    },
    {
        "bar": "跑步吧",
        "author": "demo_zhou",
        "tag": "训练",
        "title": "从 5 公里喘到半马 1 小时 58 分，我的 12 周训练表",
        "content": (
            "去年这个时候，5 公里还要走走停停。\n\n"
            "这 12 周没有堆太多跑量，核心是每周一次慢跑、一次节奏跑、一次长距离，"
            "剩下两天做力量和拉伸。最难的不是跑，是按时睡觉和认真吃饭。\n\n"
            "比赛当天前 15 公里压住速度，最后 6 公里反而越跑越轻松。"
            "训练表放在正文里，供同样想跑半马的朋友参考。"
        ),
        "image_bars": [12],
        "hours_ago": 26,
        "views": 412,
        "forward_count": 5,
        "likes": ["demo_lin", "demo_qi", "demo_mao"],
        "favorites": ["demo_lin"],
        "comments": [
            {
                "author": "demo_lin",
                "text": "每周跑量怎么安排的？膝盖还好吗？",
                "likes": ["demo_zhou"],
            },
            {
                "author": "demo_qi",
                "text": "太强了，我还在 5 公里挣扎。",
            },
        ],
    },
    {
        "bar": "摄影吧",
        "author": "demo_qi",
        "tag": "技巧",
        "title": "雨天扫街参数分享：50mm 也能拍出电影感",
        "content": (
            "很多人觉得雨天不适合拍照，其实雨后的反光和低饱和天空特别出片。\n\n"
            "这次只带了一支 50mm，光圈收到 f/2.8，快门保持在 1/125 以上，"
            "重点找路面积水、玻璃倒影和行人剪影。后期只做了轻微降饱和和冷色调整。\n\n"
            "器材不是重点，愿意在雨里多走两条街才是。"
        ),
        "image_bars": [9],
        "hours_ago": 30,
        "views": 188,
        "forward_count": 2,
        "likes": ["demo_yu", "demo_su"],
        "favorites": ["demo_yu"],
        "comments": [
            {
                "author": "demo_yu",
                "text": "雨天反光确实好看，快门大概多少？",
            },
            {
                "author": "demo_su",
                "text": "最后一张的构图很舒服。",
            },
        ],
    },
    {
        "bar": "游戏吧",
        "author": "demo_chen",
        "tag": "攻略",
        "title": "这版本别再无脑堆暴击了，实测三套出装",
        "content": (
            "新版本暴击收益被稀释之后，很多人还在照抄旧出装。\n\n"
            "这周用三套不同思路各打了十把：纯暴击、攻速特效、半肉穿透。"
            "结果在同等经济下，攻速特效的持续输出最稳定，半肉穿透容错最高。\n\n"
            "当然，出装只是下限，走位和进场时机还是得练。"
        ),
        "image_bars": [3],
        "hours_ago": 36,
        "views": 629,
        "forward_count": 8,
        "likes": ["demo_zhou", "demo_mao"],
        "favorites": ["demo_zhou"],
        "comments": [
            {
                "author": "demo_zhou",
                "text": "第二套试了两把，确实顺。",
                "likes": ["demo_chen"],
            },
            {
                "author": "demo_mao",
                "text": "手残党表示还是先练走位。",
            },
        ],
    },
    {
        "bar": "音乐吧",
        "author": "demo_yu",
        "tag": "歌单",
        "title": "通勤歌单更新：十首适合阴天循环的歌",
        "content": (
            "最近上下班都在听这十首，整体是偏安静但不至于让人睡着的路线。\n\n"
            "有老歌也有新专辑，按照从早高峰到下班路上的情绪顺序排了序。"
            "第三首适合在雨天进地铁时听，最后一首留给到家前的那段路。\n\n"
            "歌单已整理好，欢迎交换你的阴天单曲。"
        ),
        "image_bars": [6],
        "hours_ago": 42,
        "views": 275,
        "forward_count": 4,
        "likes": ["demo_su", "demo_lin", "demo_qi"],
        "favorites": ["demo_su"],
        "comments": [
            {
                "author": "demo_su",
                "text": "第三首一响就知道今天稳了。",
            },
            {
                "author": "demo_lin",
                "text": "已加入收藏，明早通勤就听。",
            },
        ],
    },
    {
        "bar": "烘焙吧",
        "author": "demo_tang",
        "tag": "烘焙",
        "title": "第一次做可颂就开酥成功，记录一下翻车边缘",
        "content": (
            "第一次挑战可颂，前一天晚上把面团和黄油都准备好，第二天早上六点起来开酥。\n\n"
            "中间室温有点高，黄油差点化掉，临时把操作台搬到空调下面才救回来。"
            "最后成品层次不算完美，但切开能看到清晰的蜂窝，已经很满足了。\n\n"
            "下次准备把黄油温度再压低一点。"
        ),
        "image_bars": [13],
        "hours_ago": 48,
        "views": 143,
        "forward_count": 1,
        "likes": ["demo_qi", "demo_mao"],
        "favorites": ["demo_qi"],
        "comments": [
            {
                "author": "demo_qi",
                "text": "层次好漂亮，温度控制的多少？",
            },
            {
                "author": "demo_mao",
                "text": "看起来已经很像店里卖的了。",
            },
        ],
    },
    {
        "bar": "旅游吧",
        "author": "demo_lin",
        "tag": "攻略",
        "title": "错峰去泉州住了四天，这条老城步行线建议收藏",
        "content": (
            "避开周末去泉州住了四天，基本靠步行和公交，节奏很舒服。\n\n"
            "第一天从西街慢慢走到开元寺，第二天去蟳埔村看簪花围，"
            "第三天沿着中山路看骑楼，第四天留给了几个小博物馆。\n\n"
            "最推荐早上七点多的西街，店铺还没完全开门，本地人已经开始吃面线糊了。"
            "住宿建议选在老城边缘，既安静又方便走回来。"
        ),
        "image_bars": [16],
        "hours_ago": 54,
        "views": 356,
        "forward_count": 7,
        "likes": ["demo_su", "demo_yu", "demo_qi"],
        "favorites": ["demo_su", "demo_yu"],
        "comments": [
            {
                "author": "demo_su",
                "text": "四天会不会太赶？我打算住两晚。",
                "likes": ["demo_lin"],
            },
            {
                "author": "demo_yu",
                "text": "西街早上人少的时候最好逛。",
            },
            {
                "author": "demo_qi",
                "text": "求住宿区域推荐。",
            },
        ],
    },
    {
        "bar": "足球吧",
        "author": "demo_zhou",
        "tag": "复盘",
        "title": "周末业余联赛复盘：我们输在了第二落点",
        "content": (
            "比分是 1 比 2，但场面没有比分那么难看。\n\n"
            "上半场我们控球更多，问题出在每次解围之后，第二落点几乎全被对方拿到，"
            "导致防线一直被迫后退。下半场调整了后腰站位，情况好了很多，可惜时间不够。\n\n"
            "业余比赛拼到最后，很多时候拼的就是站位纪律和体能分配。"
        ),
        "image_bars": [7],
        "hours_ago": 60,
        "views": 118,
        "forward_count": 0,
        "likes": ["demo_chen", "demo_mao"],
        "favorites": ["demo_chen"],
        "comments": [
            {
                "author": "demo_chen",
                "text": "第二落点这个说法很专业，确实是站位问题。",
            },
        ],
    },
    {
        "bar": "手工吧",
        "author": "demo_mao",
        "tag": "手作",
        "title": "用旧牛仔裤做了个电脑内胆包，缝纫机初体验",
        "content": (
            "衣柜里有一条穿旧了的牛仔裤，一直舍不得扔，干脆剪了做内胆包。\n\n"
            "第一次用缝纫机，直线走得歪歪扭扭，拆了两次才勉强满意。"
            "内衬用了旧衬衫的布，夹层塞了一点薄棉，电脑放进去刚好。\n\n"
            "虽然近看全是瑕疵，但自己做的用起来就是开心。"
        ),
        "image_bars": [14],
        "hours_ago": 66,
        "views": 84,
        "forward_count": 0,
        "likes": ["demo_tang", "demo_lin"],
        "favorites": ["demo_tang"],
        "comments": [
            {
                "author": "demo_tang",
                "text": "旧物改造太有成就感了。",
            },
            {
                "author": "demo_lin",
                "text": "走线比我想象中整齐。",
            },
        ],
    },
    {
        "bar": "吉他吧",
        "author": "demo_su",
        "tag": "练习",
        "title": "指弹新手三个月，终于把《风之诗》完整弹下来了",
        "content": (
            "三个月前连右手分解都还不稳，现在终于能把《风之诗》从头到尾弹完。\n\n"
            "中间最难的是中间段的泛音和节奏切换，单独抠了两周。"
            "每天练四十分钟，先慢速把每个小节弹干净，再一点点加速度。\n\n"
            "录了一版留作纪念，虽然还有杂音，但对自己来说是个小小的里程碑。"
        ),
        "image_bars": [10],
        "hours_ago": 72,
        "views": 197,
        "forward_count": 2,
        "likes": ["demo_yu", "demo_lin", "demo_qi"],
        "favorites": ["demo_yu"],
        "comments": [
            {
                "author": "demo_yu",
                "text": "三个月能完整弹下来很厉害了。",
            },
            {
                "author": "demo_lin",
                "text": "求一个新手练习顺序。",
            },
        ],
    },
    {
        "bar": "钓鱼吧",
        "author": "demo_chen",
        "tag": "渔获",
        "title": "周日下午水库野钓，三条鲫鱼换来一身蚊子包",
        "content": (
            "天气预报说多云，结果到了水库就开始晒，蚊子也比想象中多。\n\n"
            "下午三点之后鱼口才好起来，最终收获三条鲫鱼，最大的差不多半斤。"
            "虽然不算爆护，但坐在水边发呆的半天已经很值了。\n\n"
            "下次一定记得带驱蚊水。"
        ),
        "image_bars": [15],
        "hours_ago": 80,
        "views": 132,
        "forward_count": 1,
        "likes": ["demo_zhou", "demo_mao"],
        "favorites": ["demo_zhou"],
        "comments": [
            {
                "author": "demo_zhou",
                "text": "钓鱼佬永不空军，三条也是鱼。",
            },
            {
                "author": "demo_mao",
                "text": "蚊子包是附赠的纪念品。",
            },
        ],
    },
    {
        "bar": "美食吧",
        "author": "demo_qi",
        "tag": "一人食",
        "title": "一人食也值得认真：十五分钟番茄虾仁意面",
        "content": (
            "下班晚了不想点外卖，冰箱里刚好有番茄和虾仁，就做了这份意面。\n\n"
            "番茄先炒出沙，加一点番茄膏提味，虾仁最后两分钟再下锅，"
            "意面煮到比包装时间少一分钟，进酱汁里再收一下。\n\n"
            "十五分钟，一口锅，洗碗也轻松。一个人吃饭也可以很认真。"
        ),
        "image_bars": [2],
        "hours_ago": 90,
        "views": 168,
        "forward_count": 2,
        "likes": ["demo_tang", "demo_lin"],
        "favorites": ["demo_tang"],
        "comments": [
            {
                "author": "demo_tang",
                "text": "番茄先炒出沙这一步很关键。",
            },
            {
                "author": "demo_lin",
                "text": "明天晚饭就它了。",
            },
        ],
    },
    {
        "bar": "前端吧",
        "author": "demo_lin",
        "tag": "团队协作",
        "title": "给团队写了一份 Code Review 清单，争议最大的五条",
        "content": (
            "团队最近来了几位新同学，Code Review 的尺度不太统一，我就试着写了一份清单。\n\n"
            "没想到讨论最激烈的不是命名和格式，而是「小改动要不要补测试」"
            "「评论要不要区分 blocking 和 nit」「重构能不能顺手改无关代码」。\n\n"
            "最后我们达成共识：清单不是为了卡人，而是减少来回解释的成本。"
            "把争议点写清楚，比强行统一更重要。"
        ),
        "image_bars": [1],
        "hours_ago": 100,
        "views": 244,
        "forward_count": 4,
        "likes": ["demo_chen", "demo_zhou", "demo_su"],
        "favorites": ["demo_chen"],
        "comments": [
            {
                "author": "demo_chen",
                "text": "第五条是不是太严格了，小改动也要求补测试？",
                "likes": ["demo_lin"],
            },
            {
                "author": "demo_zhou",
                "text": "清单最大的价值是减少来回解释。",
            },
        ],
    },
    {
        "bar": "科技吧",
        "author": "demo_zhou",
        "tag": "评测",
        "title": "用了半年电子墨水屏，聊聊它到底适合谁",
        "content": (
            "半年前入手了一台电子墨水屏，原本是想替代平板看文档，结果用下来发现场景比想象中窄。\n\n"
            "它最适合的是长时间读文字、做批注和睡前阅读，眼睛确实舒服很多。"
            "但如果要刷网页、看视频或者做色彩相关的工作，它并不合适。\n\n"
            "所以别把它当成万能平板，当成一个专门的阅读工具，体验会好很多。"
        ),
        "image_bars": [8],
        "hours_ago": 110,
        "views": 205,
        "forward_count": 3,
        "likes": ["demo_chen", "demo_yu"],
        "favorites": ["demo_chen"],
        "comments": [
            {
                "author": "demo_chen",
                "text": "适合看文档，不适合刷视频，总结到位。",
            },
            {
                "author": "demo_yu",
                "text": "夜里看确实舒服很多。",
            },
        ],
    },
    {
        "bar": "电影吧",
        "author": "demo_tang",
        "tag": "经验",
        "title": "在家搭了个 100 寸投影，租房党也能抄的作业",
        "content": (
            "一直想在租的房子里弄个投影，又不想大动干戈，最后选了一套可以随时拆走的方案。\n\n"
            "投影放在床头柜上，幕布用可移动支架，走线全部沿着踢脚板，退租时十分钟就能收完。"
            "晚上关灯看片，100 寸的沉浸感确实不是电视能比的。\n\n"
            "预算和避坑点都整理在正文里，租房的朋友可以参考。"
        ),
        "image_bars": [4],
        "hours_ago": 120,
        "views": 312,
        "forward_count": 6,
        "likes": ["demo_yu", "demo_mao", "demo_su"],
        "favorites": ["demo_yu"],
        "comments": [
            {
                "author": "demo_yu",
                "text": "租房怎么解决走线问题？",
                "likes": ["demo_tang"],
            },
            {
                "author": "demo_mao",
                "text": "看完立刻去量了白墙尺寸。",
            },
        ],
    },
]


# =============================================================================
# 基础工具
# =============================================================================
class SeedError(RuntimeError):
    pass


def log(message: str) -> None:
    print(message, flush=True)


def db_error_text(exc: Exception) -> str:
    """只输出错误码/类型与中文提示，不输出账号、密码或 .env 内容。"""
    if isinstance(exc, pymysql.err.OperationalError) and exc.args:
        code = exc.args[0]
        hints = {
            1045: "账号或密码无效/无权限",
            1044: "数据库账号无权限",
            1049: "独立库不存在，请先用 run.py 初始化",
            2003: "无法连接 MySQL（服务未启动或端口不对）",
            2006: "MySQL 连接已断开",
            2013: "MySQL 连接超时",
        }
        return f"MySQL 错误 {code}：{hints.get(code, '连接失败')}"
    if isinstance(exc, pymysql.err.MySQLError) and exc.args:
        code = exc.args[0]
        return f"MySQL 错误 {code}：{type(exc).__name__}"
    return type(exc).__name__


def load_db_config() -> dict:
    """运行时读取后端 .env；值只保存在内存里，绝不打印。"""
    if not ENV_FILE.is_file():
        raise SeedError(f"缺少后端 .env：{ENV_FILE}")
    values = dotenv_values(str(ENV_FILE))
    missing = [key for key in ("DB_HOST", "DB_PORT", "DB_USER") if not values.get(key)]
    if missing:
        raise SeedError("后端 .env 缺少连接配置：" + ", ".join(missing))

    host = str(values["DB_HOST"]).strip()
    if host.lower() not in ALLOWED_HOSTS:
        raise SeedError("后端 .env 的 DB_HOST 必须是 localhost 或 127.0.0.1")

    try:
        port = int(str(values["DB_PORT"]).strip())
    except ValueError as exc:
        raise SeedError("后端 .env 的 DB_PORT 不是有效端口") from exc

    return {
        "host": "127.0.0.1" if host.lower() == "localhost" else host,
        "port": port,
        "user": str(values["DB_USER"]).strip(),
        "password": str(values.get("DB_PASSWORD") or ""),
    }


def connect(config: dict) -> pymysql.connections.Connection:
    """固定连到 bbs_local_codex；不提供库名参数，也不读取 .env 的 DB_NAME。"""
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=LOCAL_DB,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=8,
        read_timeout=30,
        write_timeout=30,
    )


def hash_password(password: str) -> str:
    """与后端 main.py 完全一致的 PBKDF2-SHA256 格式。"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_schema(cur) -> None:
    cur.execute("SELECT DATABASE()")
    row = cur.fetchone()
    current = str(row[0]) if row else ""
    if current != LOCAL_DB:
        raise SeedError(f"当前数据库不是 {LOCAL_DB}，已拒绝继续")

    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
        (LOCAL_DB,),
    )
    existing = {row[0] for row in cur.fetchall()}
    missing = [table for table in REQUIRED_TABLES if table not in existing]
    if missing:
        raise SeedError("独立库表不完整，缺少：" + ", ".join(missing) + "；请先运行 run.py")


def resolve_bar_ids(cur, names: set[str]) -> dict[str, int]:
    if not names:
        return {}
    placeholders = ", ".join(["%s"] * len(names))
    cur.execute(f"SELECT id, name FROM bars WHERE name IN ({placeholders})", tuple(names))
    mapping = {str(row[1]): int(row[0]) for row in cur.fetchall()}
    missing = sorted(name for name in names if name not in mapping)
    if missing:
        raise SeedError("缺少贴吧：" + "、".join(missing) + "；请先运行 run.py 初始化")
    return mapping


def image_urls(spec: dict) -> list[str]:
    return [f"/uploads/posts/demo_seed/demo_bar-{bar}.jpg" for bar in spec["image_bars"]]


def source_image(bar: int) -> Path:
    return STATIC_BARS_DIR / f"bar-{bar}.jpg"


def prepare_images(check_only: bool) -> tuple[int, list[str]]:
    """把本地静态吧图复制到 uploads/posts/demo_seed/；已存在且非空则跳过。"""
    problems: list[str] = []
    for spec in DEMO_POSTS:
        for bar in spec["image_bars"]:
            src = source_image(bar)
            if not src.is_file() or src.stat().st_size <= 0:
                problems.append(str(src))
                continue
            dst = DEMO_IMAGE_DIR / f"demo_bar-{bar}.jpg"
            if dst.is_file() and dst.stat().st_size > 0:
                continue
            if check_only:
                continue
            DEMO_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except OSError as exc:
                problems.append(f"{dst}（{type(exc).__name__}）")

    # 归档统计按“本次需要复制的文件数”算，便于 --check 展示
    unique_needed = {
        (DEMO_IMAGE_DIR / f"demo_bar-{bar}.jpg")
        for spec in DEMO_POSTS
        for bar in spec["image_bars"]
        if not ((DEMO_IMAGE_DIR / f"demo_bar-{bar}.jpg").is_file()
                and (DEMO_IMAGE_DIR / f"demo_bar-{bar}.jpg").stat().st_size > 0)
    }
    return len(unique_needed), problems


# =============================================================================
# 只读检查
# =============================================================================
def run_check() -> int:
    log("BBS 本地演示数据种子 · 只读检查")
    log(f"固定库：{LOCAL_DB}（没有库名参数，不能绕过）")
    try:
        config = load_db_config()
        log(f"已读取后端 .env（凭据不显示）；连接 {config['host']}:{config['port']}")
    except Exception as exc:
        log(f"[错误] {exc}")
        return 1

    needed_images, image_problems = prepare_images(check_only=True)
    if image_problems:
        log("[错误] 本地静态吧图缺失或不可读：")
        for item in image_problems:
            log(f"  - {item}")
        return 1
    log(f"[ok] 本地静态吧图齐全；本次需要复制 {needed_images} 张（--check 不复制）")

    try:
        conn = connect(config)
    except Exception as exc:
        log(f"[错误] 连接独立库失败：{db_error_text(exc)}")
        return 1

    try:
        with conn.cursor() as cur:
            verify_schema(cur)
            bar_names = {spec["bar"] for spec in DEMO_POSTS}
            bar_names |= {name for names in DEMO_FOLLOWS.values() for name in names}
            bar_names |= {name for names in DEMO_FOOTPRINTS.values() for name in names}
            resolve_bar_ids(cur, bar_names)
            log("[ok] 10 张核心表齐全，贴吧可解析")

            usernames = [item[0] for item in DEMO_USERS] + [DEMO_ADMIN[0]]
            placeholders = ", ".join(["%s"] * len(usernames))
            cur.execute(f"SELECT username, role FROM users WHERE username IN ({placeholders})", tuple(usernames))
            existing_users = {str(row[0]): str(row[1]) for row in cur.fetchall()}
            log(f"演示账号：已存在 {len(existing_users)} / {len(usernames)}（已存在只复用，不改角色和密码）")
            if DEMO_ADMIN[0] in existing_users and existing_users[DEMO_ADMIN[0]] not in ("admin", "super_admin"):
                log(f"[警告] {DEMO_ADMIN[0]} 已存在但角色是 {existing_users[DEMO_ADMIN[0]]}；按约定不提升")
            log(f"演示帖子：计划 {len(DEMO_POSTS)} 篇 + 关联评论/点赞/收藏/关注")

            # 统计已有演示帖子（标题 + 作者）
            cur.execute(
                "SELECT u.username, p.title FROM posts p JOIN users u ON u.id = p.user_id "
                "WHERE u.username LIKE 'demo_%'"
            )
            existing_posts = {(str(row[0]), str(row[1])) for row in cur.fetchall()}
            planned = {(spec["author"], spec["title"]) for spec in DEMO_POSTS}
            log(f"  已存在 {len(planned & existing_posts)} 篇，将新增 {len(planned - existing_posts)} 篇")
        log("[--check] 未复制图片、未写数据库。")
        return 0
    except Exception as exc:
        if isinstance(exc, SeedError):
            log(f"[错误] {exc}")
        else:
            log(f"[错误] 检查失败：{db_error_text(exc)}")
        return 1
    finally:
        conn.close()


# =============================================================================
# 写入
# =============================================================================
def ensure_user(cur, username: str, nickname: str, avatar: str, role: str, password: str,
                created_ids: dict[str, int], notes: list[str]) -> tuple[int, bool]:
    """返回 (user_id, 是否本次新建)。已存在账号只复用，绝不改角色/密码。"""
    cur.execute("SELECT id, role FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        user_id = int(row[0])
        if role == "admin" and str(row[1]) not in ("admin", "super_admin"):
            notes.append(f"{username} 已存在但角色为 {row[1]}，按约定不提升为管理员")
        elif role == "admin":
            notes.append(f"{username} 已存在（管理员），复用原账号，不重置密码")
        else:
            notes.append(f"{username} 已存在，复用原账号，不重置密码")
        created_ids[username] = user_id
        return user_id, False

    cur.execute(
        """INSERT INTO users (username, password_hash, nickname, avatar, role, status)
           VALUES (%s, %s, %s, %s, %s, 1)""",
        (username, hash_password(password), nickname, avatar, role),
    )
    user_id = int(cur.lastrowid)
    created_ids[username] = user_id
    notes.append(f"新增{('管理员' if role == 'admin' else '用户')} {username}")
    return user_id, True


def ensure_follows(cur, user_id: int, bar_ids: list[int], hours_ago: int, stats: dict) -> None:
    for bar_id in bar_ids:
        cur.execute(
            """INSERT IGNORE INTO follows (user_id, bar_id, created_at)
               VALUES (%s, %s, NOW() - INTERVAL %s HOUR)""",
            (user_id, bar_id, hours_ago),
        )
        if cur.rowcount == 1:
            stats["follows"] += 1


def ensure_footprints(cur, user_id: int, bar_ids: list[int], stats: dict) -> None:
    for idx, bar_id in enumerate(bar_ids):
        cur.execute(
            """INSERT IGNORE INTO footprints (user_id, bar_id, viewed_at)
               VALUES (%s, %s, NOW() - INTERVAL %s MINUTE)""",
            (user_id, bar_id, (idx + 1) * 7),
        )
        if cur.rowcount == 1:
            stats["footprints"] += 1


def ensure_comment(cur, post_id: int, spec: dict, comment: dict, index: int,
                   post_hours: int, user_ids: dict[str, int], stats: dict) -> int | None:
    user_id = user_ids[comment["author"]]
    cur.execute(
        """SELECT id, status FROM comments
            WHERE post_id = %s AND user_id = %s AND content = %s
            ORDER BY id LIMIT 1""",
        (post_id, user_id, comment["text"]),
    )
    row = cur.fetchone()
    if row:
        comment_id = int(row[0])
        if int(row[1]) != 1:
            # 已被删除/软删除：按约定不复活
            return None
    else:
        # 评论时间落在帖子之后，最多不超过“现在”
        hours_ago = max(0, post_hours - (index + 1))
        cur.execute(
            """INSERT INTO comments
                   (post_id, user_id, parent_id, content, like_count, status, created_at)
               VALUES (%s, %s, NULL, %s, 0, 1, NOW() - INTERVAL %s HOUR)""",
            (post_id, user_id, comment["text"], hours_ago),
        )
        comment_id = int(cur.lastrowid)
        cur.execute("UPDATE posts SET comment_count = comment_count + 1 WHERE id = %s", (post_id,))
        stats["comments"] += 1

    for liker in comment.get("likes", []):
        liker_id = user_ids[liker]
        cur.execute(
            """INSERT IGNORE INTO likes (user_id, target_type, target_id, created_at)
               VALUES (%s, 'comment', %s, NOW() - INTERVAL %s HOUR)""",
            (liker_id, comment_id, max(0, post_hours - 2)),
        )
        if cur.rowcount == 1:
            cur.execute("UPDATE comments SET like_count = like_count + 1 WHERE id = %s", (comment_id,))
            stats["comment_likes"] += 1
    return comment_id


def ensure_post(cur, spec: dict, bar_id: int, user_ids: dict[str, int], stats: dict) -> None:
    author_id = user_ids[spec["author"]]
    cur.execute(
        """SELECT id, status, content FROM posts
            WHERE user_id = %s AND title = %s
            ORDER BY id LIMIT 1""",
        (author_id, spec["title"]),
    )
    row = cur.fetchone()
    if row:
        post_id = int(row[0])
        if int(row[1]) != 1:
            # 已软删除：不复活、不覆盖
            stats["posts_skipped_deleted"] += 1
            return
        if str(row[2]) != spec["content"]:
            # 同名帖子已被人工改过正文：视为用户内容，不再补互动，避免误改
            stats["posts_skipped_modified"] += 1
            return
        stats["posts_existing"] += 1
    else:
        cur.execute(
            """INSERT INTO posts
                   (bar_id, user_id, tag, title, content, like_count, comment_count,
                    forward_count, view_count, is_top, status, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, 0, 0, %s, %s, 0, 1,
                       NOW() - INTERVAL %s HOUR, NOW() - INTERVAL %s HOUR)""",
            (
                bar_id,
                author_id,
                spec["tag"],
                spec["title"],
                spec["content"],
                int(spec.get("forward_count", 0)),
                int(spec.get("views", 0)),
                int(spec["hours_ago"]),
                int(spec["hours_ago"]),
            ),
        )
        post_id = int(cur.lastrowid)
        stats["posts_created"] += 1

    # 图片：固定 URL + sort_order，唯一键保证幂等
    for idx, url in enumerate(image_urls(spec)):
        cur.execute(
            """INSERT IGNORE INTO post_images (post_id, image_url, sort_order)
               VALUES (%s, %s, %s)""",
            (post_id, url, idx),
        )
        if cur.rowcount == 1:
            stats["images"] += 1

    # 帖子点赞（只增不删；已存在则忽略）
    for liker in spec.get("likes", []):
        liker_id = user_ids[liker]
        cur.execute(
            """INSERT IGNORE INTO likes (user_id, target_type, target_id, created_at)
               VALUES (%s, 'post', %s, NOW() - INTERVAL %s HOUR)""",
            (liker_id, post_id, max(0, int(spec["hours_ago"]) - 1)),
        )
        if cur.rowcount == 1:
            cur.execute("UPDATE posts SET like_count = like_count + 1 WHERE id = %s", (post_id,))
            stats["post_likes"] += 1

    # 收藏
    for who in spec.get("favorites", []):
        user_id = user_ids[who]
        cur.execute(
            """INSERT IGNORE INTO favorites (user_id, post_id, created_at)
               VALUES (%s, %s, NOW() - INTERVAL %s HOUR)""",
            (user_id, post_id, max(0, int(spec["hours_ago"]) - 1)),
        )
        if cur.rowcount == 1:
            stats["favorites"] += 1

    # 评论 + 评论点赞
    for idx, comment in enumerate(spec.get("comments", [])):
        ensure_comment(
            cur,
            post_id,
            spec,
            comment,
            idx,
            int(spec["hours_ago"]),
            user_ids,
            stats,
        )


def run_seed() -> int:
    log("BBS 本地演示数据种子")
    log(f"固定库：{LOCAL_DB}（没有库名参数，不能绕过）")

    try:
        config = load_db_config()
        log(f"已读取后端 .env（凭据不显示）；连接 {config['host']}:{config['port']}")
    except Exception as exc:
        log(f"[错误] {exc}")
        return 1

    needed_images, image_problems = prepare_images(check_only=False)
    if image_problems:
        log("[错误] 本地静态吧图缺失或复制失败：")
        for item in image_problems:
            log(f"  - {item}")
        return 1
    log(f"[图片] 本地静态吧图已就绪（本次复制 {needed_images} 张，目标 {DEMO_IMAGE_DIR}）")

    try:
        conn = connect(config)
    except Exception as exc:
        log(f"[错误] 连接独立库失败：{db_error_text(exc)}")
        return 1

    stats = {
        "users_created": 0,
        "posts_created": 0,
        "posts_existing": 0,
        "posts_skipped_deleted": 0,
        "posts_skipped_modified": 0,
        "comments": 0,
        "post_likes": 0,
        "comment_likes": 0,
        "favorites": 0,
        "follows": 0,
        "footprints": 0,
        "images": 0,
    }
    notes: list[str] = []
    lock_acquired = False
    committed = False

    try:
        with conn.cursor() as cur:
            verify_schema(cur)
            bar_names = {spec["bar"] for spec in DEMO_POSTS}
            bar_names |= {name for names in DEMO_FOLLOWS.values() for name in names}
            bar_names |= {name for names in DEMO_FOOTPRINTS.values() for name in names}
            bar_ids = resolve_bar_ids(cur, bar_names)

            cur.execute("SELECT GET_LOCK(%s, 10)", (SEED_LOCK,))
            lock_row = cur.fetchone()
            if not lock_row or lock_row[0] != 1:
                raise SeedError("另一个种子进程正在运行，请稍后重试")
            lock_acquired = True

            # 把前面的只读查询收尾，给写入一个干净的事务边界
            conn.commit()
            conn.begin()

            user_ids: dict[str, int] = {}
            for username, nickname, avatar in DEMO_USERS:
                _, created = ensure_user(
                    cur, username, nickname, avatar, "user", DEMO_PASSWORD, user_ids, notes
                )
                if created:
                    stats["users_created"] += 1

            _, admin_created = ensure_user(
                cur,
                DEMO_ADMIN[0],
                DEMO_ADMIN[1],
                DEMO_ADMIN[2],
                "admin",
                DEMO_ADMIN_PASSWORD,
                user_ids,
                notes,
            )
            if admin_created:
                stats["users_created"] += 1

            # 关注 + 足迹（只对本次解析到的 demo 账号）
            for username, names in DEMO_FOLLOWS.items():
                ensure_follows(
                    cur,
                    user_ids[username],
                    [bar_ids[name] for name in names],
                    hours_ago=24,
                    stats=stats,
                )
            for username, names in DEMO_FOOTPRINTS.items():
                ensure_footprints(
                    cur,
                    user_ids[username],
                    [bar_ids[name] for name in names],
                    stats=stats,
                )

            # 帖子 + 图片 + 评论 + 点赞 + 收藏
            for spec in DEMO_POSTS:
                ensure_post(cur, spec, bar_ids[spec["bar"]], user_ids, stats)

            conn.commit()
            committed = True

    except SeedError as exc:
        if not committed:
            try:
                conn.rollback()
            except Exception:
                pass
        log(f"[错误] {exc}")
        return 1
    except Exception as exc:
        if not committed:
            try:
                conn.rollback()
            except Exception:
                pass
        log(f"[错误] 写入失败，已回滚：{db_error_text(exc)}")
        return 1
    finally:
        if lock_acquired:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT RELEASE_LOCK(%s)", (SEED_LOCK,))
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

    log("")
    log("[完成] 演示数据已写入（事务已提交）")
    for note in notes:
        log(f"  · {note}")
    log("  · 新增帖子 %d 篇；已存在 %d 篇；软删除跳过 %d 篇；人工改过正文跳过 %d 篇" % (
        stats["posts_created"], stats["posts_existing"],
        stats["posts_skipped_deleted"], stats["posts_skipped_modified"]))
    log("  · 新增评论 %d 条、帖子点赞 %d 个、评论点赞 %d 个、收藏 %d 个、关注 %d 个、足迹 %d 条、图片 %d 张" % (
        stats["comments"], stats["post_likes"], stats["comment_likes"],
        stats["favorites"], stats["follows"], stats["footprints"], stats["images"]))
    log("  · 没有 DROP / TRUNCATE / DELETE，也没有修改既有用户资料")
    log("  · 演示账号密码只写在 outputs/bbs-demo-guide.md，脚本不打印")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BBS 本地演示数据种子（固定 bbs_local_codex，只增不改，不打印凭据）"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只做只读检查：不复制图片、不写数据库",
    )
    args = parser.parse_args()

    if args.check:
        return run_check()
    return run_seed()


if __name__ == "__main__":
    sys.exit(main())
