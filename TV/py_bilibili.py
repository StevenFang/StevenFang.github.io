# coding=utf-8
# !/usr/bin/python
import sys
import os
from base.spider import Spider
import json
from requests import session, utils
import threading
import time
import random
from urllib.parse import quote

sys.path.append('..')
dirname, filename = os.path.split(os.path.abspath(__file__))
sys.path.append(dirname)

class Spider(Spider):

    #【建议通过扫码确认】设置Cookie，在双引号内填写
    raw_cookie_line = ""
    #如果主cookie没有vip，可以设置第二cookie，仅用于播放会员番剧，所有的操作、记录还是在主cookie，不会同步到第二cookie
    raw_cookie_vip = ""

    #默认主页显示3图
    max_home_video_content = 3

    #二维码图片转码使用国内 tool_lu，国外 qrcode_show
    qrcode_service = 'qrcode_show'
    
    #收藏标签默认显示追番1，追剧2，默认收藏夹0
    fav_mode = 0

    #上传播放进度间隔时间，单位秒，b站默认间隔15，0则不上传播放历史
    heartbeat_interval = 15

    #从正片中拆分出番剧的预告
    hide_bangumi_preview = True
    #登陆会员账号后，影视播放页不显示会员专享的标签，更简洁
    hide_bangumi_vip_badge = True
    #影视播放页是否显示花絮、PV、番外等非正片内容，无正片时不受此设定影响
    show_bangumi_pv = True
    #番剧（热门）列表使用横图
    bangumi_horizontal_cover = True
    #非会员播放会员专享视频时，添加一个页面可以使用解析源，解析源自行解决
    bangumi_vip_parse = True
    #付费视频添加一个页面可以使用解析，解析源自行解决
    bangumi_pay_parse = True

    #部分视频列表分页，限制每次加载数量
    page_size = 10

    #是否显示 UP 标签, True 为显示，False 为不显示，未登录时默认显示
    show_up_tab = False
    # UP 标签的位置，0为第一，大于主页标签长度为最末
    where_is_up_tab = 4
    
    #主页标签排序, 未登录或cookie失效时自动隐藏动态、收藏、关注、历史
    cateManual = [
        "推荐",
        "影视",
        "直播",
        "频道",
        "动态",
        "收藏",
        "关注",
        "历史",
        "搜索",
    ]

    #在动态标签的筛选中固定显示他，n为用户名或任意都可以，v必须为准确的UID
    focus_on_up_list = [
        #{"n":"徐云流浪中国", "v":"697166795"},
    ]
    
    #在搜索标签的筛选中固定显示搜索词
    focus_on_search_key = [
        '周杰伦',
        '汪星人',
        '喵星人'
    ]

    #自定义推荐标签的筛选
    tuijian_list = [
        "热门",
        "排行榜",
        "每周必看",
        #"入站必刷",
        "番剧时间表",
        "国创时间表",
        "动画",
        "音乐",
        #"舞蹈",
        #"游戏",
        #"鬼畜",
        "知识",
        "科技",
        #"运动",
        "生活",
        "美食",
        #"动物",
        #"汽车",
        #"时尚",
        "娱乐",
        "影视",
        #"原创",
        "新人",
        ]

    #是否显示直播标签筛选中分区的细化标签
    show_live_filter_tag = False
    #自定义直播标签的分区筛选
    cateManualLive = [
        "推荐",
        "网游",
        "手游",
        "单机游戏",
        "娱乐",
        "电台",
        "虚拟主播",
        "生活",
        "知识",
        "赛事",
        #"购物",
    ]

    def getName(self):
        return "哔哩哔哩"

    def load_config(self):
        if os.path.exists(f"{dirname}/config.json"):
            with open(f"{dirname}/config.json",encoding="utf-8") as f:
                self.userConfig = json.load(f)
        else:
            self.userConfig = {}
        self.userConfig_new = {}
    
    def dump_config(self):
        with open(f"{dirname}/config.json", 'w', encoding="utf-8") as f:
            data = json.dumps(self.userConfig_new, indent=1, ensure_ascii=False)
            f.write(data)

    # 主页
    def homeContent(self, filter):
        result = {}
        classes = []
        needLogin = ['动态', '收藏', '关注', '历史']
        for k in self.cateManual:
            if k in needLogin:
                self.getCookie_event.wait()
                if not self.isLogin:
                    continue
            classes.append({
                'type_name': k,
                'type_id': k
            })
        self.add_focus_on_up_filter_event.wait()
        if self.show_up_tab:
            classes.insert(self.where_is_up_tab, {
                'type_name': 'UP',
                'type_id': 'UP'})
            self.config["filter"].update({'UP': self.config["filter"].pop('动态')})
        self.add_channel_filter_event.wait()
        self.add_fav_filter_event.wait()
        self.add_live_filter_event.wait()
        result['class'] = classes
        if filter:
            result['filters'] = self.config['filter']
        t = threading.Thread(target=self.dump_config)
        t.start()
        return result

    # 用户cookies
    cookies = cookies_vip = cookies_fake = userid = csrf = ''
    isLogin = False
    con = threading.Condition()
    getCookie_event = threading.Event()

    def getCookie_dosome(self, co):
        c = co.strip().split('=', 1)
        if not '%' in c[1]:
            c[1] = quote(c[1])
        return c

    def getCookie(self):
        import http.cookies
        cookies_dic = self.userConfig.get('cookie_dic', '')
        if not self.raw_cookie_line and not cookies_dic:
            self.show_up_tab = True
            self.getCookie_event.set()
            with self.con:
                self.con.notifyAll()
            return
        if self.raw_cookie_line:
            cookies_dic = dict(map(self.getCookie_dosome, self.raw_cookie_line.split(';')))
        cookie_jar = utils.cookiejar_from_dict(cookies_dic)
        rsp = session()
        self.cookies = rsp.cookies = cookie_jar
        url = 'https://api.bilibili.com/x/web-interface/nav'
        content = self.fetch(url, headers=self.header, cookies=self.cookies)
        res = json.loads(content.text)
        if res["code"] == 0:
            self.userConfig_new['userid'] = self.userConfig['userid'] = self.userid = res["data"].get('mid')
            self.csrf = rsp.cookies['bili_jct']
            self.isLogin = int(res['data'].get('isLogin'))
            if int(res['data'].get('vipStatus')):
                self.cookies_vip = self.cookies
            self.userConfig_new['cookie_dic'] = cookies_dic
            self.userConfig_new['face'] = self.userConfig['face'] = res['data'].get('face')
            self.userConfig_new['uname'] = self.userConfig['uname'] = res['data'].get('uname')
            t = threading.Thread(target=self.dump_config)
            t.start()
        else:
            self.show_up_tab = True
        with self.con:
            self.getCookie_event.set()
            self.con.notifyAll()

    def getVIPCookie(self):
        import http.cookies
        self.getCookie_event.wait()
        cookies_dic = self.userConfig.get('cookie_vip_dic', '')
        if self.cookies_vip or not self.raw_cookie_vip and not cookies_dic:
            return
        if self.raw_cookie_vip:
            cookies_dic = dict(map(self.getCookie_dosome, self.raw_cookie_vip.split(';')))
        cookie_jar = utils.cookiejar_from_dict(cookies_dic)
        rsp = session()
        self.cookies_vip = rsp.cookies = cookie_jar
        url = 'https://api.bilibili.com/x/web-interface/nav'
        content = self.fetch(url, headers=self.header, cookies=self.cookies_vip)
        res = json.loads(content.text)
        if res["code"] == 0:
            if not res['data']['vipStatus']:
                self.cookies_vip = ''
            self.userConfig_new['cookie_vip_dic'] = cookies_dic
            self.userConfig_new['userid_vip'] = self.userConfig['userid_vip'] = res["data"].get('mid')
            self.userConfig_new['face_vip'] = self.userConfig['face_vip'] = res['data'].get('face')
            self.userConfig_new['uname_vip'] = self.userConfig['uname_vip'] = res['data'].get('uname')
            t = threading.Thread(target=self.dump_config)
            t.start()

    getFakeCookie_event = threading.Event()

    def getFakeCookie(self):
        self.getCookie_event.wait()
        rsp = self.fetch('https://www.bilibili.com')
        self.cookies_fake = rsp.cookies
        self.getFakeCookie_event.set()
        if not self.isLogin:
            self.cookies = self.cookies_fake
        return self.cookies_fake
        
    def get_fav_list_dict(self, fav):
        fav_dict = {
            'n': fav['title'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;",'"').strip(),
            'v': fav['id']}
        return fav_dict

    def get_fav_list(self):
        url = 'https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=%s&jsonp=jsonp' % self.userid
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jo = json.loads(rsp.text)
        fav_list = []
        if jo['code'] == 0:
            fav = jo['data'].get('list')
            self.userConfig_new['fav_list'] = self.userConfig['fav_list'] = list(map(self.get_fav_list_dict, fav))
        return self.userConfig['fav_list']

    add_fav_filter_event = threading.Event()

    def add_fav_filter(self):
        self.getCookie_event.wait()
        fav_list = self.userConfig.get('fav_list', '')
        userid = self.userConfig.get('userid', '')
        if not self.userid:
            fav_list = []
        elif not fav_list or fav_list and userid != self.userid:
            fav_list = self.get_fav_list()
        else:
            t = threading.Thread(target=self.get_fav_list)
            t.start()
        fav_top = [{"n": "追番", "v": "1"},{"n": "追剧", "v": "2"}]
        fav_config = self.config["filter"].get('收藏')
        if fav_config:
            fav_config.insert(0, {
                "key": "mlid",
                "name": "分区",
                "value": fav_top + fav_list,
            })
        self.add_fav_filter_event.set()

    def get_channel_list_dict(self, channel):
        channel_dict = {
            'n': channel['name'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;",'"').strip(),
            'v': channel['id']}
        return channel_dict

    def get_channel_list(self):
        if not self.cookies_fake:
            self.getFakeCookie_event.wait()
        url = 'https://api.bilibili.com/x/web-interface/web/channel/category/channel/list?id=100&offset=0&page_size=15'
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jo = json.loads(rsp.text)
        channel_list = []
        if jo['code'] == 0:
            channel = jo['data'].get('channels')
            self.userConfig_new['channel_list'] = self.userConfig['channel_list'] = list(map(self.get_channel_list_dict, channel))
        return self.userConfig['channel_list']

    add_channel_filter_event = threading.Event()

    def add_channel_filter(self):
        channel_list = self.userConfig.get('channel_list', '')
        if not channel_list:
            channel_list = self.get_channel_list()
        else:
            t = threading.Thread(target=self.get_channel_list)
            t.start()
        channel_config = self.config["filter"].get('频道')
        if channel_config:
            channel_config.insert(0, {
                "key": "cid",
                "name": "分区",
                "value": channel_list,
            })
        self.add_channel_filter_event.set()

    def get_up_list(self):
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?timezone_offset=-480&type=video&page=1'
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jo = json.loads(rsp.text)
        up_list = []
        if jo['code'] == 0:
            up = jo['data'].get('items')
            self.userConfig_new['up_list'] = self.userConfig['up_list'] = list(map(lambda x: {'n': x['modules']["module_author"]['name'], 'v': str(x['modules']["module_author"]['mid'])}, up))
        return self.userConfig['up_list']

    add_focus_on_up_filter_event = threading.Event()

    def add_focus_on_up_filter(self):
        self.getCookie_event.wait()
        up_list = self.userConfig.get('up_list', '')
        userid = self.userConfig.get('userid')
        if not self.userid:
            up_list = [{"n": "账号管理", "v": "登录"}]
        elif not up_list or up_list and userid != self.userid:
            up_list = self.get_up_list()
        else:
            t = threading.Thread(target=self.get_up_list)
            t.start()
        if len(self.focus_on_up_list) > 0:
            focus_on_up_list_mid = list(map(lambda x: x['v'], self.focus_on_up_list))
            for item in up_list:
                if item['v'] in focus_on_up_list_mid:
                    up_list.remove(item)
        up_top = [{"n": "上个视频的UP主", "v": "上个视频的UP主"}] + self.focus_on_up_list
        if self.isLogin:
            up_list += [{"n": '账号管理', "v": "登录"}]
        dynamic_config = self.config["filter"].get('动态')
        if dynamic_config:
            dynamic_config.insert(0, {
                "key": "mid",
                "name": "UP主",
                "value": up_top + up_list,
            })
        self.add_focus_on_up_filter_event.set()

    def get_live_parent_area_list(self, parent_area):
        name = parent_area['name']
        id = str(parent_area['id'])
        area = parent_area['list']
        area_dict = list(map(lambda area: {'n': area['name'], 'v': str(area['parent_id']) + '_' + str(area['id'])}, area))
        live_area = {'key': 'tid', 'name': name, 'value': area_dict}
        cateLive_name = {'id': id + '_0', 'value': live_area}
        return (name, cateLive_name)

    def get_live_list(self):
        if not self.cookies_fake:
            self.getFakeCookie_event.wait()
        url = 'https://api.live.bilibili.com/xlive/web-interface/v1/index/getWebAreaList?source_id=2'
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jo = json.loads(rsp.text)
        cateLive = {}
        if jo['code'] == 0:
            parent = jo['data']['data']
            self.userConfig_new['cateLive'] = self.userConfig['cateLive'] = dict(map(self.get_live_parent_area_list, parent))
        return self.userConfig['cateLive']

    add_live_filter_event = threading.Event()

    def add_live_filter(self):
        cateLive = self.userConfig.get('cateLive', '')
        if cateLive:
            t = threading.Thread(target=self.get_live_list)
            t.start()
        else:
            cateLive = self.get_live_list()
        self.config["filter"]['直播'] = []
        live_area = {'key': 'tid', 'name': '分区', 'value': []}
        for name in self.cateManualLive:
            if name in cateLive:
                area_dict = {'n': name, 'v': cateLive[name]['id']}
                live_area["value"].append(area_dict)
                if self.show_live_filter_tag:
                    self.config["filter"]['直播'].append(cateLive[name]['value'])
            else:
                area_dict = {'n': name, 'v': name}
                live_area["value"].append(area_dict)
        self.config["filter"]['直播'].insert(0, live_area)
        self.add_live_filter_event.set()

    def add_search_key(self):
        if len(self.focus_on_search_key) > 0 and self.config["filter"].get('搜索'):
            keyword = {"key": "keyword", "name": "搜索词","value": []}
            keyword["value"] = list(map(lambda i: {'n': i, 'v': i}, self.focus_on_search_key))
            self.config["filter"]['搜索'].insert(0, keyword)

    def get_tuijian_filter(self):
        tuijian_filter = {"番剧时间表": "10001", "国创时间表": "10004", "排行榜": "0", "动画": "1", "音乐": "3", "舞蹈": "129", "游戏": "4", "鬼畜": "119", "知识": "36", "科技": "188", "运动": "234", "生活": "160", "美食": "211", "动物": "217", "汽车": "223", "时尚": "155", "娱乐": "5", "影视": "181", "原创": "origin", "新人": "rookie"}
        tf_list = {"key": "tid", "name": "分类", "value": []}
        for t in self.tuijian_list:
            tf = tuijian_filter.get(t)
            if not tf:
                tf = t
            tf_dict = {'n': t, 'v': tf}
            tf_list["value"].append(tf_dict)
        self.config["filter"]['推荐'] = tf_list

    def __init__(self):
        self.load_config()
        t = threading.Thread(target=self.add_live_filter)
        t.start()
        t = threading.Thread(target=self.add_channel_filter)
        t.start()
        t = threading.Thread(target=self.getCookie)
        t.start()
        t = threading.Thread(target=self.getFakeCookie)
        t.start()
        t = threading.Thread(target=self.add_focus_on_up_filter)
        t.start()
        t = threading.Thread(target=self.add_fav_filter)
        t.start()
        t = threading.Thread(target=self.homeVideoContent)
        t.start()
        t = threading.Thread(target=self.add_search_key)
        t.start()
        t = threading.Thread(target=self.get_tuijian_filter)
        t.start()
        t = threading.Thread(target=self.getVIPCookie)
        t.start()

    def init(self, extend=""):
        print("============{0}============".format(extend))
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # 降低内存占用
    def format_img(self, img):
        img += "@672w_378h_1c.webp"
        if not img.startswith('http'):
            img = 'https:' + img
        return img

    def pagination(self, array, pg):
        max_number = self.page_size * int(pg)
        min_number = max_number - self.page_size
        return array[min_number:max_number]

    # 将超过10000的数字换成成以万和亿为单位
    def zh(self, num):
        if int(num) >= 100000000:
            p = round(float(num) / float(100000000), 1)
            p = str(p) + '亿'
        else:
            if int(num) >= 10000:
                p = round(float(num) / float(10000), 1)
                p = str(p) + '万'
            else:
                p = str(num)
        return p

    # 将秒数转化为 时分秒的格式
    def second_to_time(self, a):
        a = int(a)
        if a < 3600:
            return time.strftime("%M:%S", time.gmtime(a))
        else:
            return time.strftime("%H:%M:%S", time.gmtime(a))

    # 字符串时分秒以及分秒形式转换成秒
    def str2sec(self, x):
        x = str(x)
        try:
            h, m, s = x.strip().split(':')  # .split()函数将其通过':'分隔开，.strip()函数用来除去空格
            return int(h) * 3600 + int(m) * 60 + int(s)  # int()函数转换成整数运算
        except:
            m, s = x.strip().split(':')  # .split()函数将其通过':'分隔开，.strip()函数用来除去空格
            return int(m) * 60 + int(s)  # int()函数转换成整数运算

    # 按时间过滤
    def filter_duration(self, vodlist, key):
        if key == '0':
            return vodlist
        else:
            vod_list_new = [i for i in vodlist if
                            self.time_diff1[key][0] <= self.str2sec(str(i["vod_remarks"])) < self.time_diff1[key][1]]
            return vod_list_new

    # 提取番剧id
    def find_bangumi_id(self, url):
        aid = str(url).strip().split(r"/")[-1]
        if not aid:
            aid = str(url).strip().split(r"/")[-2]
        aid = aid.split(r"?")[0]
        return aid

    # 登录二维码
    def get_Login_qrcode(self):
        result = {}
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jo = json.loads(rsp.text)
        if jo['code'] == 0:
            id = jo['data']['qrcode_key']
            url = jo['data']['url']
            if self.qrcode_service == 'qrcode_show':
                header = {
                    'Accept': 'image/png',
                    'X-QR-Width': '16',
                    'X-QR-Height': '9',
                }
                url = 'http://qrcode.show/' + url
            elif self.qrcode_service == 'tool_lu':
                header = {"User-Agent": self.header["User-Agent"]}
                url = 'https://tool.lu/qrcode/basic.html?text=https%3A%2F%2Fpassport.bilibili.com%2Fh5-app%2Fpassport%2Flogin%2Fscan%3Fnavhide%3D1%26qrcode_key%3D' + id + '%26from%3D&front_color=%23000000&background_color=%23ffffff&tolerance=30&size=200&margin=50'
            rsp = self.fetch(url, headers=header)
            with open(f"{dirname}/qrcode.png", 'wb') as f:
                f.write(rsp.content)
            img = f"file://{dirname}/qrcode.png"
            title = '有效期3分钟，确认后点这里'
            page = [{
                "vod_id": 'login' + id,
                "vod_name": title,
                "vod_pic": img
            }]
            if self.cookies_vip:
                page.insert(0, {
                    "vod_id": 'up' + str(self.userConfig['userid_vip']),
                    "vod_name": self.userConfig['uname_vip'],
                    "vod_pic": self.format_img(self.userConfig['face_vip']),
                    "vod_remarks": '已登录的副账号'
                })
            if self.isLogin:
                page.insert(0, {
                    "vod_id": 'up' + str(self.userConfig['userid']),
                    "vod_name": self.userConfig['uname'],
                    "vod_pic": self.format_img(self.userConfig['face']),
                    "vod_remarks": '已登录的主账号'
                })
            result['list'] = page
            result['page'] = 1
            result['pagecount'] = 1
            result['limit'] = 1
            result['total'] = 1
        return result

    time_diff1 = {'1': [0, 300],
                  '2': [300, 900], '3': [900, 1800], '4': [1800, 3600],
                  '5': [3600, 99999999999999999999999999999999]
                  }
    time_diff = '0'

    dynamic_offset = ''

    def get_dynamic(self, pg, mid, order):
        if mid == '0':
            result = {}
            if int(pg) == 1:
                self.dynamic_offset = ''
            url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?timezone_offset=-480&type=video&offset=%s&page=%s' % (self.dynamic_offset, pg)
            rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
            jo = json.loads(rsp.text)
            if jo['code'] == 0:
                self.dynamic_offset = jo['data'].get('offset')
                videos = []
                vodList = jo['data']['items']
                for vod in vodList:
                    if not vod['visible']:
                        continue
                    up = vod['modules']["module_author"]['name']
                    ivod = vod['modules']['module_dynamic']['major']['archive']
                    aid = str(ivod['aid']).strip()
                    title = ivod['title'].strip().replace("<em class=\"keyword\">", "").replace("</em>", "")
                    img = ivod['cover'].strip()
                    # remark = str(ivod['duration_text']).strip()
                    remark = str(self.second_to_time(self.str2sec(ivod['duration_text']))).strip() + '  ' + str(
                        up).strip()  # 显示分钟数+up主名字
                    videos.append({
                        "vod_id": 'av' + aid,
                        "vod_name": title,
                        "vod_pic": self.format_img(img),
                        "vod_remarks": remark
                    })
                result['list'] = videos
                result['page'] = pg
                result['pagecount'] = 9999
                result['limit'] = 99
                result['total'] = 999999
            return result
        else:
            return self.get_up_videos(mid=mid, pg=pg, order=order)

    def get_found(self, tid, rid, pg):
        result = {}
        cookies = self.cookies_fake
        if tid == '推荐':
            url = 'https://api.bilibili.com/x/web-interface/index/top/rcmd?fresh_type=3&fresh_idx={0}&fresh_idx_1h={0}&homepage_ver=1&ps={1}'.format(pg, self.page_size)
            cookies = self.cookies
        elif tid == '热门':
            url = 'https://api.bilibili.com/x/web-interface/popular?pn={0}&ps={1}'.format(pg, self.page_size)
        elif tid == "入站必刷":
            url = 'https://api.bilibili.com/x/web-interface/popular/precious'
        elif tid == "每周必看":
            url = 'https://api.bilibili.com/x/web-interface/popular/series/list'
            rsp = self.fetch(url, headers=self.header, cookies=cookies)
            jo = json.loads(rsp.text)
            number = jo['data']['list'][0]['number']
            url = 'https://api.bilibili.com/x/web-interface/popular/series/one?number=' + str(number)
        else:
            url = 'https://api.bilibili.com/x/web-interface/ranking/v2?rid={0}&type={1}'.format(rid, tid)
        rsp = self.fetch(url, headers=self.header, cookies=cookies)
        jo = json.loads(rsp.text)
        if jo['code'] == 0:
            videos = []
            vodList = jo['data'].get('item')
            if not vodList:
                vodList = jo['data']['list']
            if len(vodList) > self.page_size:
                vodList = self.pagination(vodList, pg)
            for vod in vodList:
                aid = vod.get('aid')
                if not aid:
                    aid = vod['id']
                title = vod['title'].strip()
                img = vod['pic'].strip()
                rcmd_reason = vod.get('rcmd_reason')
                if tid in ['推荐', '热门'] and rcmd_reason != None and rcmd_reason.get('content'):
                    reason= '    ' + vod['rcmd_reason']['content'].strip()
                    if '人气飙升' in reason:
                        reason= '    人气飙升'
                    elif '互动视频' in reason:
                        continue
                else:
                    reason= "　≡" + self.zh(vod['stat']['danmaku'])
                remark = str(self.second_to_time(vod['duration'])).strip() + "　▶ " + self.zh(vod['stat']['view']) + reason
                videos.append({
                    "vod_id": 'av' + str(aid).strip(),
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 99
            result['total'] = 999999
        return result

    def get_bangumi(self, tid, pg, order, season_status):
        result = {}
        cookies = self.cookies_fake
        url = 'https://api.bilibili.com/pgc/season/index/result?type=1&season_type={0}&page={1}&order={2}&season_status={3}&pagesize={4}'.format(tid, pg, order, season_status, self.page_size)
        if order == '热门':
            if tid == '1':
                url = 'https://api.bilibili.com/pgc/web/rank/list?season_type={0}&day=3'.format(tid)
            else:
                url = 'https://api.bilibili.com/pgc/season/rank/web/list?season_type={0}&day=3'.format(tid)
        elif order == '追番剧':
            url = 'https://api.bilibili.com/x/space/bangumi/follow/list?type={0}&vmid={1}&pn={2}&ps={3}'.format(tid, self.userid, pg, self.page_size)
            cookies = self.cookies
        rsp = self.fetch(url, headers=self.header, cookies=cookies)
        jo = json.loads(rsp.text)
        if jo['code'] == 0:
            if 'data' in jo:
                vodList = jo['data']['list']
            else:
                vodList = jo['result']['list']
            if len(vodList) > self.page_size:
                vodList = self.pagination(vodList, pg)
            videos = []
            for vod in vodList:
                aid = str(vod['season_id']).strip()
                title = vod['title']
                img = vod.get('ss_horizontal_cover')
                if not img or tid == '1' and not self.bangumi_horizontal_cover:
                    if vod.get('first_ep_info') and 'cover' in vod['first_ep_info']:
                        img = vod['first_ep_info']['cover']
                    elif vod.get('first_ep') and 'cover' in vod['first_ep']:
                        img = vod['first_ep']['cover']
                    else:
                        img = vod['cover'].strip()
                remark = vod.get('index_show')
                if not remark and vod.get('new_ep') and vod['new_ep'].get('index_show'):
                    remark = vod['new_ep']['index_show']
                videos.append({
                    "vod_id": 'ss' + aid,
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 90
            result['total'] = 999999
        return result

    def get_timeline(self, tid, pg):
        result = {}
        url = 'https://api.bilibili.com/pgc/web/timeline/v2?season_type={0}&day_before=2&day_after=4'.format(tid)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        content = rsp.text
        jo = json.loads(content)
        if jo['code'] == 0:
            videos1 = []
            vodList = jo['result']['latest']
            for vod in vodList:
                aid = str(vod['season_id']).strip()
                title = vod['title'].strip()
                img = vod['cover'].strip()
                remark = vod['pub_index'] + '　' + vod['follows'].replace('系列', '')
                videos1.append({
                    "vod_id": 'ss' + aid,
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            videos2 = []
            vodList2 = jo['result']['timeline']
            for i in range(len(vodList2)):
                vodList = vodList2[i]['episodes']
                for vod in vodList:
                    if str(vod['published']) == "0":
                        aid = str(vod['season_id']).strip()
                        title = str(vod['title']).strip()
                        img = str(vod['cover']).strip()
                        date = str(time.strftime("%m-%d %H:%M", time.localtime(vod['pub_ts'])))
                        remark = date + "   " + vod['pub_index']
                        videos2.append({
                            "vod_id": 'ss' + aid,
                            "vod_name": title,
                            "vod_pic": self.format_img(img),
                            "vod_remarks": remark
                        })
            result['list'] = videos2 + videos1
            result['page'] = 1
            result['pagecount'] = 1
            result['limit'] = 90
            result['total'] = 999999
        return result

    def get_live(self, pg, parent_area_id, area_id):
        result = {}
        cookies = self.cookies_fake
        url = 'https://api.live.bilibili.com/xlive/web-interface/v1/second/getList?platform=web&parent_area_id=%s&area_id=%s&sort_type=online&page=%s' % (parent_area_id, area_id, pg)
        if parent_area_id == '热门':
            url = 'https://api.live.bilibili.com/room/v1/room/get_user_recommend?page=%s&page_size=%s' % (pg, self.page_size)
        elif parent_area_id == '推荐':
            url = 'https://api.live.bilibili.com/xlive/web-interface/v1/webMain/getList?platform=web&page=%s' % pg
            cookies = self.cookies
        rsp = self.fetch(url, headers=self.header, cookies=cookies)
        jo = json.loads(rsp.text)
        if jo['code'] == 0:
            videos = []
            vodList = jo['data']
            if 'recommend_room_list' in vodList:
                vodList = vodList['recommend_room_list']
            elif 'list' in vodList:
                vodList = vodList['list']
            for vod in vodList:
                aid = str(vod['roomid']).strip()
                title = vod['title'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;", '"')
                img = vod.get('user_cover')
                if not img:
                    img = vod.get('cover')
                remark = vod['watched_show']['text_small'].strip() + "  " + vod['uname'].strip()
                videos.append({
                    "vod_id": aid,
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 99
            result['total'] = 999999
        return result

    get_up_videos_event = threading.Event()
    get_up_videos_mid = ''
    get_up_videos_result = []
    
    def get_up_videos(self, mid, pg, order):
        result = {}
        if not mid.isdigit():
            if int(pg) == 1:
                self.get_up_videos_mid = mid = self.up_mid
            else:
                mid = self.get_up_videos_mid
        if int(pg) == 1:
            self.get_up_info_event.clear()
            t = threading.Thread(target=self.get_up_info, args=(mid, ))
            t.start()
        Space = order2 = ''
        if order == 'oldest':
            order2 = order
            order = 'pubdate'
        elif order == 'quicksearch':
            Space = '投稿: '
            self.get_up_videos_result.clear()
        tmp_pg = pg
        if order2:
            self.get_up_info_event.wait()
            tmp_pg = self.up_info[mid]['vod_pc'] - int(pg) + 1
        url = 'https://api.bilibili.com/x/space/arc/search?mid={0}&pn={1}&ps={2}&order={3}'.format(mid, tmp_pg, self.page_size, order)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        content = rsp.text
        jo = json.loads(content)
        videos = []
        if jo['code'] == 0:
            vodList = jo['data']['list']['vlist']
            for vod in vodList:
                aid = str(vod['aid']).strip()
                title = vod['title'].strip().replace("<em class=\"keyword\">", "").replace("</em>", "")
                img = vod['pic'].strip()
                remark = self.second_to_time(self.str2sec(str(vod['length']).strip())) + "　▶" + self.zh(vod['play'])
                videos.append({
                    "vod_id": 'av' + aid,
                    "vod_name": Space + title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            if order2:
                videos.reverse()
            if int(pg) == 1:
                self.get_up_info_event.wait()
                vodname = self.up_info[mid]['name'] + "  个人主页"
                if Space:
                    vodname = 'UP: ' + self.up_info[mid]['name']
                gotoUPHome={
                    "vod_id": 'up' + str(mid),
                    "vod_name": vodname,
                    "vod_pic": self.format_img(self.up_info[mid]['face']),
                    "vod_remarks": self.up_info[mid]['following'] + '  投稿：' + str(self.up_info[mid]['vod_count'])
                }
                videos.insert(0, gotoUPHome)
            if Space:
                self.get_up_videos_result = videos
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 99
            result['limit'] = 99
            result['total'] = 999999
        self.get_up_videos_event.set()
        return result

    history_view_at = 0
    
    def get_history(self, type, pg):
        result = {}
        if int(pg) == 1:
            self.history_view_at = 0
        url = 'https://api.bilibili.com/x/web-interface/history/cursor?ps={0}&view_at={1}&type={2}'.format(self.page_size, self.history_view_at, type)
        if type == '稍后再看':
            url = 'https://api.bilibili.com/x/v2/history/toview'
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jo = json.loads(rsp.text)
        if jo['code'] == 0:
            videos = []
            vodList = jo['data']['list']
            if type == '稍后再看':
                vodList = self.pagination(vodList, pg)
            else:
                self.history_view_at = jo['data']['cursor']['view_at']
            for vod in vodList:
                history = vod.get('history', '')
                if history:
                    business = history['business']
                    aid = str(history['oid']).strip()
                    img = vod['cover'].strip()
                    part = str(history['part']).strip()
                else:
                    business = 'archive'
                    aid = str(vod["aid"]).strip()
                    img = vod['pic'].strip()
                    part = str(vod['page']['part']).strip()
                if business == 'article':
                    continue
                elif business == 'pgc':
                    aid = 'ep' + str(history['epid'])
                    total = vod['total']
                    part = vod.get('show_title')
                elif business == 'archive':
                    aid = 'av' + aid
                    total = vod['videos']
                title = vod['title'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;", '"')
                if business == 'live':
                    live_status = vod.get('live_status', '')
                    remark = '未开播  '
                    if live_status:
                        remark = '已开播  '
                    remark += vod['author_name'].strip()
                else:
                    if str(vod['progress']) == '-1':
                        remark = '已看完'
                    elif str(vod['progress']) == '0':
                        remark = '刚开始看'
                    else:
                        process = str(self.second_to_time(vod['progress'])).strip()
                        remark = '看到  ' + process
                    if not total in [0, 1] and part:
                        remark += ' (' + str(part) + ')'
                videos.append({
                    "vod_id": aid,
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 90
            result['total'] = 999999
        return result

    def get_fav_detail(self, pg, mlid, order):
        result = {}
        url = 'https://api.bilibili.com/x/v3/fav/resource/list?media_id=%s&order=%s&pn=%s&ps=10&platform=web&type=0' % (mlid, order, pg)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        content = rsp.text
        jo = json.loads(content)
        if jo['code'] == 0:
            videos = []
            vodList = jo['data']['medias']
            for vod in vodList:
                # 只展示类型为 视频的条目
                # 过滤去掉收藏中的 已失效视频;如果不喜欢可以去掉这个 if条件
                if vod.get('type') in [2] and vod.get('title') != '已失效视频':
                    aid = str(vod['id']).strip()
                    title = vod['title'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;",
                                                                                                            '"')
                    img = vod['cover'].strip()
                    remark = str(self.second_to_time(vod['duration'])).strip() + "　▶" + self.zh(vod['cnt_info']['play'])
                    videos.append({
                        "vod_id": 'av' + aid + '_mlid' + str(mlid),
                        "vod_name": title,
                        "vod_pic": self.format_img(img),
                        "vod_remarks": remark
                    })
            # videos=self.filter_duration(videos, duration_diff)
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 99
            result['total'] = 999999
        return result

    get_up_info_event = threading.Event()
    up_info = {}
    
    def get_up_info(self, mid):
        if mid in self.up_info:
            self.get_up_info_event.set()
        url = "https://api.bilibili.com/x/web-interface/card?mid={0}".format(mid)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jRoot = json.loads(rsp.text)
        if jRoot['code'] == 0:
            jo = jRoot['data']['card']
            info = {}
            info['following'] = '未关注'
            if jRoot['data']['following']:
                info['following'] = '已关注'
            info['name'] = jo['name'].replace("<em class=\"keyword\">", "").replace("</em>", "")
            info['face'] = jo['face']
            info['fans'] = self.zh(jo['fans'])
            info['like_num'] = self.zh(jRoot['data']['like_num'])
            info['vod_count'] = str(jRoot['data']['archive_count']).strip()
            info['desc'] = jo['Official']['desc'] + "　" + jo['Official']['title']
            pc = divmod(int(info['vod_count']), self.page_size)
            info['vod_pc'] =pc[0]
            if pc[1] != 0:
                info['vod_pc'] += 1
            self.up_info[mid] = info
        self.get_up_info_event.set()

    get_vod_relation_event = threading.Event()
    
    def get_vod_relation(self, id, relation):
        if id.isdigit():
            urlarg = 'aid=' + str(id)
        elif '=' in id:
            urlarg = id
        else:
            urlarg = 'bvid=' + id
        url = 'https://api.bilibili.com/x/web-interface/archive/relation?' + urlarg
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jo = json.loads(rsp.text)
        if jo['code'] == 0:
            jo = jo['data']
            if jo['attention']:
                relation.append('已关注')
            else:
                relation.append('未关注')
            triple = []
            if jo['favorite']:
                triple.append('已收藏')
            if jo['like']:
                triple.append('已点赞')
            coin = jo.get('coin')
            if coin:
                triple.append(f"已投{coin}个币")
            if len(triple) == 3:
                relation.append('已三连')
            else:
                relation.extend(triple)
            if jo['dislike']:
                relation.append('已踩')
            if jo['season_fav']:
                relation.append('已订阅合集')
        self.get_vod_relation_event.set()

    def get_channel(self, pg, cid, order):
        result = {}
        if str(pg) == '1':
            self.channel_offset = ''
        if order == "featured":
            url = 'https://api.bilibili.com/x/web-interface/web/channel/featured/list?channel_id={0}&filter_type=0&offset={1}&page_size={2}'.format(cid, self.channel_offset, self.page_size)
        else:
            url = 'https://api.bilibili.com/x/web-interface/web/channel/multiple/list?channel_id={0}&sort_type={1}&offset={2}&page_size={3}'.format(cid, order, self.channel_offset, self.page_size)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jo = json.loads(rsp.text)
        if jo.get('code') == 0:
            self.channel_offset = jo['data'].get('offset')
            videos = []
            vodList = jo['data']['list']
            if pg == '1' and 'items' in vodList[0]:
                vodList_rank = vodList[0]['items']
                del (vodList[0])
                vodList = vodList_rank + vodList
            for vod in vodList:
                if 'uri' in vod and 'bangumi' in vod['uri']:
                    aid = self.find_bangumi_id(vod['uri'])
                else:
                    aid = 'av' + str(vod['id']).strip()
                title = vod['name'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;", '"')
                img = vod['cover'].strip()
                remark = "▶ " + vod['view_count']
                if 'duration' in vod:
                    remark = str(self.second_to_time(self.str2sec(vod['duration']))).strip() + "　" + remark
                videos.append({
                    "vod_id": aid,
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 99
            result['total'] = 999999
        return result

    def get_follow(self, pg, sort):
        result = {}
        if sort == "最常访问":
            url = 'https://api.bilibili.com/x/relation/followings?vmid={0}&pn={1}&ps=10&order=desc&order_type=attention' .format(self.userid, pg)
        elif sort == "最近关注":
            url = 'https://api.bilibili.com/x/relation/followings?vmid={0}&pn={1}&ps=10&order=desc&order_type='.format(self.userid, pg)
        elif sort == "正在直播":
            url = 'https://api.live.bilibili.com/xlive/web-ucenter/v1/xfetter/GetWebList?page={0}&page_size=10'.format(pg)
        elif sort == "最近访问":
            url = 'https://api.bilibili.com/x/v2/history?pn={0}&ps=15'.format(pg)
        elif sort == "特别关注":
            url = 'https://api.bilibili.com/x/relation/tag?mid={0}&tagid=-10&pn={1}&ps=10'.format(self.userid, pg)
        elif sort == "悄悄关注":
            url = 'https://api.bilibili.com/x/relation/whispers?pn={0}&ps=10'.format(pg)
        else:
            url = 'https://api.bilibili.com/x/relation/followers?vmid={0}&pn={1}&ps=10&order=desc&order_type=attention'.format(self.userid, pg)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jo = json.loads(rsp.text)
        if jo['code'] != 0:
            return result
        if sort == "特别关注" or sort == "最近访问":
            vodList = jo['data']
        elif sort == "正在直播":
            vodList = jo['data']['rooms']
        else:
            vodList = jo['data']['list']
        if int(pg) == 1:
            self.recently_up_list = []
        follow = []
        for f in vodList:
            remark = ''
            if sort == "最近访问":
                mid = 'up' + str(f['owner']['mid'])
                if mid in self.recently_up_list:
                    continue
                self.recently_up_list.append(mid)
                title = str(f['owner']['name']).strip()
                img = str(f['owner']['face']).strip()
            elif sort == "正在直播":
                mid = str(f['room_id'])
                title = f['title'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;", '"')
                img = f['cover_from_user'].strip()
                remark = f['uname'].strip()
            else:
                mid = 'up' + str(f['mid'])
                title = str(f['uname']).strip()
                img = str(f['face']).strip()
            if 'special' in f and f['special'] == 1:
                remark = '特别关注'
            follow.append({
                "vod_id": mid,
                "vod_name": title,
                "vod_pic": self.format_img(img),
                "vod_remarks": remark
            })
        result['list'] = follow
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 99
        result['total'] = 999999
        return result

    homeVideoContent_result = {}
    
    def homeVideoContent(self):
        if self.homeVideoContent_result == {}:
            videos = self.get_found(rid='0', tid='all', pg=1)['list'][0:int(self.max_home_video_content)]
            self.homeVideoContent_result['list'] = videos
        return self.homeVideoContent_result

    def categoryContent(self, tid, pg, filter, extend):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        if tid == "推荐":
            if 'tid' in extend:
                tid = extend['tid']
            if tid.isdigit():
                tid = int(tid)
                if tid > 10000:
                    tid -= 10000
                    return self.get_timeline(tid=tid, pg=pg)
                rid = tid
                tid = 'all'
                return self.get_found(tid=tid, rid=rid, pg=pg)
            rid = '0'
            return self.get_found(tid=tid, rid=rid, pg=pg)
        elif tid == "影视":
            tid = '1'
            order = '热门'
            season_status = '-1'
            if 'tid' in extend:
                tid = extend['tid']
            if 'order' in extend:
                order = extend['order']
            if 'season_status' in extend:
                if order == '热门':
                    order = '2'
                season_status = extend['season_status']
            return self.get_bangumi(tid, pg, order, season_status)
        elif tid == "动态":
            mid = '0'
            order = 'pubdate'
            if 'mid' in extend:
                mid = extend['mid']
            if 'order' in extend:
                order = extend['order']
            if mid == '0' and not self.isLogin or mid == '登录':
                return self.get_Login_qrcode()
            return self.get_dynamic(pg=pg, mid=mid, order=order)
        elif tid == '频道':
            order = 'hot'
            cid = random.choice(self.userConfig['channel_list'])
            cid = cid['v']
            if 'order' in extend:
                order = extend['order']
            if 'cid' in extend:
                cid = extend['cid']
            return self.get_channel(pg=pg, cid=cid, order=order)
        elif tid == '直播':
            tid = "热门"
            area_id = '0'
            if 'tid' in extend:
                tid = extend['tid']
            if '_' in tid:
                tids = tid.split('_')
                tid = tids[0]
                area_id = tids[1]
            return self.get_live(pg=pg, parent_area_id=tid, area_id=area_id)
        elif tid == "UP":
            mid = self.up_mid
            if 'mid' in extend:
                mid = extend['mid']
            if not mid or mid == '登录':
                return self.get_Login_qrcode()
            up_config = self.config["filter"].get('UP')
            if not mid and up_config:
                for i in up_config:
                    if i['key'] == 'mid':
                        if len(i['value']) > 1:
                            mid = i['value'][1]['v']
                        break
            order = 'pubdate'
            if 'order' in extend:
                order = extend['order']
            return self.get_up_videos(mid=mid, pg=pg, order=order)
        elif tid == "关注":
            sort = "最常访问"
            if 'sort' in extend:
                sort = extend['sort']
            return self.get_follow(pg, sort)
        elif tid == "收藏":
            mlid = str(self.fav_mode)
            if 'mlid' in extend:
                mlid = extend['mlid']
            fav_config = self.config["filter"].get('收藏')
            if mlid in ['1', '2']:
                return self.get_bangumi(tid=mlid, pg=pg, order='追番剧', season_status='')
            elif mlid == '0' and fav_config:
                for i in fav_config:
                    if i['key'] == 'mlid':
                        if len(i['value']) > 1:
                            mlid = i['value'][2]['v']
                        break
            order = 'mtime'
            if 'order' in extend:
                order = extend['order']
            return self.get_fav_detail(pg=pg, mlid=mlid, order=order)
        elif tid == '历史':
            type = 'all'
            if 'type' in extend:
                type = extend['type']
            if type == 'UP主':
                return self.get_follow(pg=pg, sort='最近访问')
            return self.get_history(type=type, pg=pg)
        else:
            duration_diff = '0'
            if 'duration' in extend:
                duration_diff = extend['duration']
            type = 'video'
            if 'type' in extend:
                type = extend['type']
            order = 'totalrank'
            if 'order' in extend:
                order = extend['order']
            keyword = str(self.search_key)
            search_config = self.config["filter"].get('搜索')
            if not keyword and search_config:
                for i in search_config:
                    if i['key'] == 'keyword':
                        if len(i['value']) > 0:
                            keyword = i['value'][0]['v']
                        break
            if 'keyword' in extend:
                keyword = extend['keyword']
            return self.get_search_content(key=keyword, pg=pg, duration_diff=duration_diff, order=order, type=type, ps=self.page_size)

    search_content_dict = {}

    def get_search_content(self, key, pg, duration_diff, order, type, ps):
        if not self.cookies_fake:
            self.getFakeCookie_event.wait()
        url = 'https://api.bilibili.com/x/web-interface/search/type?keyword={0}&page={1}&duration={2}&order={3}&search_type={4}&page_size={5}'.format(
            key, pg, duration_diff, order, type, ps)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        content = rsp.text
        jo = json.loads(content)
        result = {}
        if jo.get('code') == 0 and 'result' in jo['data']:
            videos = []
            vodList = jo['data']['result']
            if type == 'live':
                vodList = vodList['live_room']
            if vodList == None:
                with self.con:
                    self.search_content_dict[type] = result
                    self.con.notifyAll()
                return result
            for vod in vodList:
                title = ''
                if type == 'bili_user':
                    aid = 'up' + str(vod['mid']).strip()
                    img = vod['upic'].strip()
                    remark = '粉丝:' + self.zh(vod['fans']) + "　投稿:" + self.zh(vod['videos'])
                    title = vod['uname']
                elif type == 'live':
                    aid = str(vod['roomid']).strip()
                    img = vod['cover'].strip()
                    remark = '人气:' + self.zh(vod['online'])  + '　' + vod['uname']
                elif 'media' in type:
                    aid = str(vod['season_id']).strip()
                    if self.detailContent_args:
                        seasons = self.detailContent_args.get('seasons')
                        if seasons:
                            bangumi_seasons_id = []
                            for ss in self.detailContent_args['seasons']:
                                bangumi_seasons_id.append(ss['vod_id'])
                            if aid + 'ss' in bangumi_seasons_id:
                                continue
                    aid = 'ss' + aid
                    img = vod['cover'].strip()
                    remark = str(vod['index_show']).strip()
                else:
                    aid = 'av' + str(vod['aid']).strip()
                    img = vod['pic'].strip()
                    remark = str(self.second_to_time(self.str2sec(vod['duration']))).strip() + "　▶" + self.zh(vod['play']) + "　≡ " + self.zh(vod['danmaku'])
                if not title:
                    title = vod['title'].replace("<em class=\"keyword\">", "").replace("</em>", "").replace("&quot;",
                                                                                                        '"')
                # remark = str(vod['duration']).strip()
                videos.append({
                    "vod_id": aid,
                    "vod_name": title,
                    "vod_pic": self.format_img(img),
                    "vod_remarks": remark
                })
            # videos=self.filter_duration(videos, duration_diff)
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 99
            result['total'] = 999999
        with self.con:
            self.search_content_dict[type] = result
            self.con.notifyAll()
        return result

    def cleanSpace(self, str):
        return str.replace('\n', '').replace('\t', '').replace('\r', '').replace(' ', '')

    def get_normal_episodes(self, episode):
        ssid = epid = ''
        aid = episode.get('aid', '')
        if not aid:
            aid = self.detailContent_args['aid']
        cid = episode.get('cid', '')
        ep_title = episode.get('title', '')
        if not ep_title:
            ep_title = episode.get('part', '')
        duration = episode.get('duration', '')
        if not duration:
            page = episode.get('page', '')
            if page:
                duration = page['duration']
        preview = parse = badge = long_title = ''
        ep_from = self.detailContent_args.get('from')
        if ep_from and ep_from == 'bangumi':
            epid = episode.get('id', '')
            if epid:
                epid = '_ep' + str(epid)
            ssid = '_ss' + self.detailContent_args['ssid']
            if duration and str(duration).endswith('000'):
                duration = int(duration / 1000)
            if ep_title.isdigit():
                ep_title = '第' + ep_title + self.detailContent_args['title_type']
            badge = episode.get('badge', '')
            if not self.cookies_vip and badge == '会员' and self.bangumi_vip_parse or badge == '付费' and self.bangumi_pay_parse:
                parse = '_parse'
            if self.cookies_vip and self.hide_bangumi_vip_badge:
                badge = badge.replace('会员', '')
            if self.hide_bangumi_preview and badge == '预告':
                badge = badge.replace('预告', '')
                preview = 1
            if badge:
                badge = '【' + badge + '】'
            long_title = episode.get('long_title', '')
            if not badge and long_title:
                long_title = ' ' + long_title
        title = ep_title + badge + long_title
        title = title.replace("#", "﹟").replace("$", "﹩")
        if duration:
            duration = '_dur' + str(duration)
        url = '{0}${1}_{2}{3}{4}{5}'.format(title, aid, cid, ssid, epid, duration)
        if preview:
            self.detailContent_args['preview'] = 1
            return [None, None, url]
        if parse:
            self.detailContent_args['parse'] = 1
            ep_title += '【解析】'+ long_title
            ep_title = ep_title.replace("#", "﹟").replace("$", "﹩")
            parseurl = '{0}${1}_{2}{3}{4}{5}{6}'.format(ep_title, aid, cid, ssid, epid, duration, parse)
        else:
            parseurl = url
        return [url, parseurl, None]

    def get_ugc_season_section(self, section):
        if self.detailContent_args['sections_len'] > 1:
            sec_title = self.detailContent_args['season_title'] + ' ' + section['title']
        else:
            sec_title = self.detailContent_args['season_title']
        sec_title = sec_title.replace("#", "﹟").replace("$", "﹩")
        episodes = section['episodes']
        playUrl = list(map(self.get_normal_episodes, episodes))
        playUrl = '#'.join(list(x for x in map(lambda x: x[0], playUrl) if x is not None))
        return sec_title, playUrl

    get_ugc_season_event = threading.Event()

    def get_ugc_season(self, sections):
        self.detailContent_args['sections_len'] = len(sections)
        test = dict(map(self.get_ugc_season_section, sections))
        self.detailContent_args['seasonPt'] = list(map(lambda x: x, test.keys()))
        self.detailContent_args['seasonPu'] = list(map(lambda x: x, test.values()))
        self.get_ugc_season_event.set()

    get_vod_related_event = threading.Event()

    def get_vod_related(self, jo_Related):
        playUrl = list(map(self.get_normal_episodes, jo_Related))
        self.detailContent_args['relatedP'] = ['#'.join(list(x for x in map(lambda x: x[0], playUrl) if x is not None))]
        self.get_vod_related_event.set()

    get_vod_pages_event = threading.Event()

    def get_vod_pages(self, pages):
        playUrl = list(map(self.get_normal_episodes, pages))
        self.detailContent_args['firstP'] = ['#'.join(list(x for x in map(lambda x: x[0], playUrl) if x is not None))]
        self.get_vod_pages_event.set()

    up_mid = ''
    detailContent_args = {}
    
    def detailContent(self, array):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        aid = array[0]
        if 'up' in aid:
            return self.up_detailContent(array)
        if 'ss' in aid or 'ep' in aid:
            return self.ysContent(array)
        if 'login' in aid:
            return self.login_detailContent(array)
        if aid.isdigit():
            return self.live_detailContent(array)
        mlid = ''
        for i in aid.split('_'):
            if i.startswith('av', 0, 2):
                id = i.replace('av', '', 1)
                urlargs = 'aid=' + str(id)
            elif i.startswith('BV', 0, 2):
                id = i
                urlargs = 'bvid=' + id
            elif i.startswith('mlid', 0, 4):
                mlid = i.replace('mlid', '', 1)
        self.get_vod_relation_event.clear()
        relation = []
        t = threading.Thread(target=self.get_vod_relation, args=(urlargs, relation, ))
        t.start()
        url = 'https://api.bilibili.com/x/web-interface/view/detail?' + urlargs
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jRoot = json.loads(rsp.text)
        jo = jRoot['data']['View']
        if 'redirect_url' in jo and 'bangumi' in jo['redirect_url']:
            ep_id = self.find_bangumi_id(jo['redirect_url'])
            new_array = []
            for i in array:
                new_array.append(i)
            new_array[0] = ep_id
            return self.ysContent(new_array)
        aid = jo.get('aid')
        self.up_mid = str(jo['owner']['mid'])
        self.detailContent_args = {}
        self.detailContent_args['from'] = 'video'
        self.detailContent_args['aid'] = aid
        #相关合集
        self.get_ugc_season_event.set()
        ugc_season = jo.get('ugc_season')
        if ugc_season:
            self.get_ugc_season_event.clear()
            self.detailContent_args['season_title'] = ugc_season['title']
            sections = ugc_season['sections']
            t = threading.Thread(target=self.get_ugc_season, args=(sections, ))
            t.start()
        #相关推荐
        self.get_vod_related_event.set()
        jo_Related = jRoot['data'].get('Related')
        if jo_Related:
            self.get_vod_related_event.clear()
            t = threading.Thread(target=self.get_vod_related, args=(jo_Related, ))
            t.start()
        #正片
        self.get_vod_pages_event.set()
        pages = jo['pages']
        if pages:
            self.get_vod_pages_event.clear()
            t = threading.Thread(target=self.get_vod_pages, args=(pages, ))
            t.start()
        title = jo['title'].replace("<em class=\"keyword\">", "").replace("</em>", "")
        pic = jo['pic']
        up_name = jo['owner']['name']
        desc = jo['desc'].strip()
        typeName = jo['tname']
        date = time.strftime("%Y%m%d", time.localtime(jo['pubdate']))  # 投稿时间本地年月日表示
        stat = jo['stat']
        # 演员项展示视频状态，包括以下内容：
        status = "播放: " + self.zh(stat['view']) + "　弹幕: " + self.zh(stat['danmaku']) + "　点赞: " + self.zh(stat['like']) + "　收藏: " + self.zh(stat['favorite']) + "　投币: " + self.zh(stat['coin'])
        remark = str(jo['duration']).strip()
        duration = jo['duration']
        vod = {
            "vod_id": 'av' + str(aid),
            "vod_name": title, 
            "vod_pic": pic,
            "type_name": typeName,
            "vod_year": date,
            "vod_area": "bilidanmu",
            "vod_remarks": remark,  # 不会显示
            'vod_tags': 'mv',  # 不会显示
            "vod_actor": status,
            "vod_content": desc
        }
        #做点什么
        follow = '关注UP$' + str(self.up_mid) + '_1_notplay_follow'
        unfollow = '取消关注$' + str(self.up_mid) + '_2_notplay_follow'
        like = '点赞$' + str(aid) + '_1_notplay_like'
        unlike = '取消点赞$' + str(aid) + '_2_notplay_like'
        coin1 = '投1币并点赞$' + str(aid) + '_1_notplay_coin'
        coin2 = '投2币并点赞$' + str(aid) + '_2_notplay_coin'
        fav = '收藏$' + str(aid) + '_0_notplay_fav'
        triple = '一键三连$' + str(aid) + '_notplay_triple'
        Space = ' $_'
        secondPList = [follow, triple, like, Space, Space, Space, fav, coin1, coin2, Space, Space, Space, unfollow, unlike]
        if mlid:
            favdel = '取消收藏$' + str(aid) + '_'+ str(mlid) + '_notplay_fav'
            secondPList.append(favdel)
        secondP = ['#'.join(secondPList)]
        if pages:
            self.get_vod_pages_event.wait()
            AllPt = ['B站', '做点什么']
            AllPu = self.detailContent_args['firstP'] + secondP
        else:
            AllPt = ['做点什么']
            AllPu = secondP
        if jo_Related:
            self.get_vod_related_event.wait()
            AllPt.append('相关推荐')
            AllPu.extend(self.detailContent_args['relatedP'])
        if ugc_season:
            self.get_ugc_season_event.wait()
            AllPt.extend(self.detailContent_args['seasonPt'])
            AllPu.extend(self.detailContent_args['seasonPu'])
        vod['vod_play_from'] = "$$$".join(AllPt)
        vod['vod_play_url'] = "$$$".join(AllPu)
        #视频关系
        self.get_vod_relation_event.wait()
        vod['vod_director'] = up_name + '　' + '　'.join(relation)

        result = {
            'list': [
                vod
            ]
        }
        return result

    def up_detailContent(self, array):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        mid = array[0].replace('up', '')
        self.get_up_info_event.clear()
        info = {}
        i = threading.Thread(target=self.get_up_info, args=(mid, ))
        i.start()
        self.detailContent_args = {}
        self.detailContent_args['from'] = 'up'
        self.up_mid = mid
        first = '是否关注$ '
        follow = '关注$' + str(mid) + '_1_mid_follow'
        unfollow = '取消关注$' + str(mid) + '_2_mid_follow'
        qqfollow = '悄悄关注$' + str(mid) + '_3_mid_follow'
        spfollow = '特别关注$' + str(mid) + '_-10_mid_specialfollow'
        unspfollow = '取消特别关注$' + str(mid) + '_0_mid_specialfollow'
        doWhat = [first, follow, qqfollow, spfollow, unfollow, unspfollow]
        doWhat = '#'.join(doWhat)
        self.get_up_info_event.wait()
        vod = {
            "vod_id": 'up' + str(mid),
            "vod_name": self.up_info[mid]['name'] + "  个人主页",
            "vod_pic": self.up_info[mid]['face'],
            "vod_remarks": "",  # 不会显示
            "vod_tags": 'mv',  # 不会显示
            "vod_actor": "粉丝数：" + self.up_info[mid]['fans'] + "　投稿数：" + self.up_info[mid]['vod_count'] + "　点赞数：" + self.up_info[mid]['like_num'],
            "vod_director": self.up_info[mid]['name'] + '　UID：' +str(mid) + "　" + self.up_info[mid]['following'],
            "vod_content": self.up_info[mid]['desc'],
            'vod_play_from': '关注TA$$$视频投稿在动态标签——筛选——上个UP，选择后查看'
        }
        vod['vod_play_url'] = doWhat

        result = {
            'list': [
                vod
            ]
        }
        return result

    def login_detailContent(self, array):
        key = array[0].replace('login', '', 1)
        vod = {
            "vod_name": "登录页",
            "vod_content": '请通过b站客户端扫码确认登录后点击相应按钮获取cookie',
            'vod_play_from': '登录$$$退出登录'
        }
        first = '在客户端确认登录后点击相应按钮>>>$ '
        login = '设置为主账号，动态收藏关注等内容源于此$' + str(key) + '_0_login_setting'
        login_vip = '设置为备用的VIP账号，仅用于播放会员番剧$' + str(key) + '_1_login_setting'
        loginP = ['#'.join([first, login, login_vip])]
        second = '点击相应按钮退出账号>>>$ '
        logout = '退出主账号$0_logout_setting'
        logout_vip = '退出备用的VIP账号$1_logout_setting'
        logoutP = ['#'.join([second, logout, logout_vip])]
        vod['vod_play_url'] = '$$$'.join(loginP + logoutP)
        result = {
            'list': [
                vod
            ]
        }
        return result

    def get_all_season(self, season):
        season_id = str(season['season_id'])
        season_title = season['season_title']
        if season_id == self.detailContent_args['ssid']:
            self.detailContent_args['s_title'] = season_title
        pic = season['cover']
        remark = season['new_ep']['index_show']
        result = {
            "vod_id": season_id + 'ss',
            "vod_name": '系列：' + season_title,
            "vod_pic": self.format_img(pic),
            "vod_remarks": remark}
        return result

    def add_season_to_search(self, seasons):
        self.detailContent_args['seasons'] = list(map(self.get_all_season, seasons))

    def get_bangumi_section(self, sec):
        sec_title = sec['title'].replace("#", "﹟").replace("$", "﹩")
        sec_type = sec['type']
        if sec_type in [1, 2] and len(sec['episode_ids']) == 0:
            episodes = sec['episodes']
            playUrl = '#'.join(list(x for x in map(lambda x: x[0], list(map(self.get_normal_episodes, episodes))) if x is not None))
            return sec_title, playUrl
        return None

    get_section_event = threading.Event()

    def get_section(self, section):
        test = dict(x for x in map(self.get_bangumi_section, section) if x is not None)
        self.detailContent_args['SectionPf'] = list(map(lambda x: x, test.keys()))
        self.detailContent_args['SectionPu'] = list(map(lambda x: x, test.values()))
        self.get_section_event.set()

    get_bangumi_episodes_event = threading.Event()

    def get_bangumi_episodes(self, episodes):
        playUrl = list(map(self.get_normal_episodes, episodes))
        self.detailContent_args['FirstPu'] = '#'.join(list(x for x in map(lambda x: x[0], playUrl) if x is not None))
        if self.detailContent_args.get('parse', ''):
            self.detailContent_args['ParsePu'] = '#'.join(list(x for x in map(lambda x: x[1], playUrl) if x is not None))
        if self.detailContent_args.get('preview', ''):
            self.detailContent_args['PreviewPu'] = '#'.join(list(x for x in map(lambda x: x[2], playUrl) if x is not None))
        self.get_bangumi_episodes_event.set()

    def ysContent(self, array):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        self.detailContent_args = {}
        self.detailContent_args['from'] = 'bangumi'
        aid = array[0]
        if 'ep' in aid:
            aid = 'ep_id=' + aid.replace('ep', '')
        elif 'ss' in aid:
            aid = 'season_id=' + aid.replace('ss', '')
        else:
            aid = 'season_id=' + aid
        url = "https://api.bilibili.com/pgc/view/web/season?{0}".format(aid)
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jRoot = json.loads(rsp.text)
        jo = jRoot['result']
        self.detailContent_args['ssid'] = str(jo['season_id'])
        title = jo['title']
        self.detailContent_args['s_title'] = jo['season_title']
        self.detailContent_args['title_type'] = '集'
        if jo['type'] in [1, 4]:
            self.detailContent_args['title_type'] = '话'
        #获取正片
        episodes = jo['episodes']
        if len(episodes) > 0:
            self.get_bangumi_episodes_event.clear()
            t = threading.Thread(target=self.get_bangumi_episodes, args=(episodes, ))
            t.start()
        section = jo.get('section')
        #获取花絮
        self.get_section_event.set()
        if section and not len(jo['episodes']) or section and self.show_bangumi_pv:
            self.get_section_event.clear()
            t = threading.Thread(target=self.get_section, args=(section, ))
            t.start()
        #添加系列到搜索
        seasons = jo.get('seasons')
        if len(seasons) == 1:
            self.detailContent_args['s_title'] = seasons[0]['season_title']
            self.detailContent_args['seasons'] = []
            seasons = 0
        else:
            t = threading.Thread(target=self.add_season_to_search, args=(seasons, ))
            t.start()
        pic = jo['cover']
        typeName = jo['share_sub_title']
        date = jo['publish']['pub_time'][0:4]
        dec = jo['evaluate']
        remark = jo['new_ep']['desc']
        stat = jo['stat']
        # 演员和导演框展示视频状态，包括以下内容：
        status = "弹幕: " + self.zh(stat['danmakus']) + "　点赞: " + self.zh(stat['likes']) + "　投币: " + self.zh(
            stat['coins']) + "　追番追剧: " + self.zh(stat['favorites'])
        if 'rating' in jo:
            score = "评分: " + str(jo['rating']['score']) + '　' + jo['subtitle']
        else:
            score = "暂无评分" + '　' + jo['subtitle']
        vod = {
            "vod_id": 'ss' + self.detailContent_args['ssid'],
            "vod_name": title,
            "vod_pic": pic,
            "type_name": typeName,
            "vod_year": date,
            "vod_area": "bilidanmu",
            "vod_remarks": remark,
            "vod_actor": status,
            "vod_director": score,
            "vod_content": dec
        }
        ZhuiPf = '追番剧'
        ZhuiPu = '是否追番剧$ #追番剧$' + self.detailContent_args['ssid'] + '_add_zhui#取消追番剧$' + self.detailContent_args['ssid'] + '_del_zhui'
        if seasons:
            ZhuiPf += '$$$更多系列'
            ZhuiPu += '$$$更多系列在快速搜索中查看$ '
        self.get_bangumi_episodes_event.wait()
        PreviewPf = []
        PreviewPu = self.detailContent_args.get('PreviewPu', [])
        if PreviewPu:
            PreviewPf.append('预告')
            PreviewPu = [PreviewPu]
        if section:
            self.get_section_event.wait()
        FirstPf = []
        FirstPu = self.detailContent_args.get('FirstPu', [])
        if FirstPu:
            FirstPf = [self.detailContent_args['s_title']]
            FirstPu = [FirstPu]
        ParsePf = []
        ParsePu = self.detailContent_args.get('ParsePu', [])
        if ParsePu:
            ParsePf.append(str(self.detailContent_args['s_title']) + '【解析】')
            ParsePu = [ParsePu]
        fromL = FirstPf + ParsePf + PreviewPf + self.detailContent_args.get('SectionPf', [])
        urlL = FirstPu + ParsePu + PreviewPu + self.detailContent_args.get('SectionPu', [])
        fromL.insert(1, ZhuiPf)
        urlL.insert(1, ZhuiPu)
        vod['vod_play_from'] = '$$$'.join(fromL)
        vod['vod_play_url'] = '$$$'.join(urlL)
        result = {
            'list': [
                vod
            ]
        }
        return result

    get_live_api2_playurl_event = threading.Event()

    def get_live_api2_playurl(self, room_id, api2_playUrl):
        qn = {'原画': '10000', '高清': '0'}
        codec = {'avc': '0', 'hevc': '1'}
        format = {'flv': '0', 'mp4': '2'}
        name = {'0': '主线', '1': '备线'}
        for q in qn:
            url = []
            for f in format:
                for c in codec:
                    for n in name:
                        url.append(f + '_' + c + name[n] + '$2_' + qn[q] + '_' + format[f] + '_' + codec[c] + '_' + n + '_' + str(room_id))
            api2_playUrl.append('#'.join(url))
        self.get_live_api2_playurl_event.set()

    def live_detailContent(self, array):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        self.detailContent_args = {}
        self.detailContent_args['from'] = 'live'
        room_id = array[0]
        api2_playUrl = []
        self.get_live_api2_playurl_event.clear()
        t = threading.Thread(target=self.get_live_api2_playurl, args=(room_id, api2_playUrl, ))
        t.start()
        url = "https://api.live.bilibili.com/room/v1/Room/get_info?room_id=%s" % room_id
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        jRoot = json.loads(rsp.text)
        if jRoot.get('code') == 0:
            jo = jRoot['data']
            mid = str(jo["uid"])
            self.get_up_info_event.clear()
            info = {}
            t = threading.Thread(target=self.get_up_info, args=(mid, ))
            t.start()
            self.up_mid = mid
            title = jo['title'].replace("<em class=\"keyword\">", "").replace("</em>", "")
            pic = jo.get("user_cover")
            desc = jo.get('description')
            typeName = jo.get('parent_area_name') + '--' + jo.get('area_name')
            if jo['live_status'] == 0:
                live_status = "未开播"
            else:
                live_status = "开播时间：" + jo.get('live_time')
            remark = '在线人数:' + str(jo['online']).strip()
            vod = {
                "vod_id": room_id,
                "vod_name": title,
                "vod_pic": pic,
                "type_name": typeName,
                "vod_year": "",
                "vod_area": "bililivedanmu",
                "vod_remarks": remark,
                "vod_actor": "关注：" + self.zh(jo.get('attention')) + "　房间号：" + room_id +  "　UID：" + mid,
                "vod_content": desc,
            }
            api1_playUrl = 'flv线路原画$platform=web&quality=4_' + room_id + '#flv线路高清$platform=web&quality=3_' + room_id + '#h5线路原画$platform=h5&quality=4_' + room_id + '#h5线路高清$platform=h5&quality=3_' + room_id
            vod['vod_play_from'] = '原画$$$高清$$$关注/取关$$$API_1'
            follow = '关注$' + str(mid) + '_1_follow'
            unfollow = '取消关注$' + str(mid) + '_2_follow'
            secondPList = [follow, unfollow]
            secondP = ['#'.join(secondPList)]
            self.get_live_api2_playurl_event.wait()
            playUrl = api2_playUrl +  secondP + [api1_playUrl]
            vod['vod_play_url'] = '$$$'.join(playUrl)
            self.get_up_info_event.wait()
            vod["vod_director"] = self.up_info[mid]['name'] + '　' + self.up_info[mid]['following'] + "　" + live_status
            result = {
                'list': [
                    vod
                ]
            }
        return result

    def do_video_search(self, result):
        list = result['list']
        for n in range(len(list)):
            remark = list[n]['vod_remarks'].split('　≡')
            list[n]['vod_remarks'] = remark[0]
        return result

    def do_some_type_search(self, result, name):
        list = result['list']
        for n in range(len(list)):
            list[n]['vod_name'] = name + list[n]['vod_name']
        return result

    get_search_content_event = threading.Event()
    search_key = ''
    
    def searchContent(self, key, quick):
        if not self.cookies_fake:
            self.getFakeCookie_event.clear()
            t = threading.Thread(target=self.getFakeCookie)
            t.start()
        self.search_key = key
        search_from = self.detailContent_args.get('from', '')
        if quick and self.up_mid and search_from:
            if self.up_mid != self.get_up_videos_mid and search_from != 'bangumi':
                self.get_up_videos_event.clear()
                i = threading.Thread(target=self.get_up_videos, args=(self.up_mid, 1, 'quicksearch'))
                i.start()
        with self.con:
            self.get_search_content_event.clear()
            self.con.notifyAll()
            self.search_content_dict.clear()
        result = {}
        types = {'video': '','media_bangumi': '番剧：', 'media_ft': '影视：', 'bili_user': 'UP主：', 'live': '直播间：'}
        for type in types:
            t = threading.Thread(target=self.get_search_content, args=(key, 1, 0, '', type, 10, ))
            t.start()
        self.get_search_content_event.set()
        n = 0
        while self.get_search_content_event.is_set():
            for type in types:
                if type in self.search_content_dict:
                    t = self.search_content_dict[type]
                    list = t.get('list')
                    if list and len(result) == 0:
                        if type == 'video':
                            result = self.do_video_search(t)
                        else:
                            result = self.do_some_type_search(t, types[type])
                    elif list:
                        if type == 'video':
                            rsp = self.do_video_search(t)
                        else:
                            rsp = self.do_some_type_search(t, types[type])
                        result['list'] += rsp['list']
                    with self.con:
                        self.search_content_dict.pop(type)
                    n += 1
            if len(types) == n:
                break
            with self.con:
                self.con.wait()
        if not self.get_search_content_event.is_set():
            return
        if quick:
            if search_from == 'bangumi':
                result['list'] = self.detailContent_args['seasons'] + result['list']
            elif self.up_mid:
                self.get_up_videos_event.wait()
                if len(self.get_up_videos_result) > 0:
                    result['list'] = self.get_up_videos_result + result['list']
        return result

    heartbeat_con = threading.Condition()
    post_heartbeat_event = threading.Event()
    heartbeat_count = 0

    def stop_heartbeat(self):
        if self.post_heartbeat_event.is_set():
            self.post_heartbeat_event.clear()
            with self.heartbeat_con:
                self.heartbeat_con.notifyAll()

    def post_heartbeat(self, aid, cid, ssid, epid, heartbeat_times, played_time):
        url = 'https://api.bilibili.com/x/click-interface/web/heartbeat'
        data = {'aid': str(aid), 'cid': str(cid), 'csrf': str(self.csrf)}
        if ssid:
            data['sid'] = str(ssid)
            data['epid'] = str(epid)
            data['type'] = 4
        for t in range(heartbeat_times):
            if t == heartbeat_times - 1:
                #播完为-1
                played_time = '-1'
            data['played_time'] = str(played_time)
            self.post(url=url, headers=self.header, cookies=self.cookies, data=data)
            with self.heartbeat_con:
                self.heartbeat_con.wait()
            if t == heartbeat_times - 1:
                self.post_heartbeat_event.clear()
            if t != heartbeat_times - 1 and not self.post_heartbeat_event.is_set():
                played_time += self.heartbeat_count
                data['played_time'] = str(played_time)
                self.post(url=url, headers=self.header, cookies=self.cookies, data=data)
            if not self.post_heartbeat_event.is_set():
                break
            played_time += self.heartbeat_interval

    def start_heartbeat(self, aid, cid, ids):
        duration = ssid = epid = ''
        for i in ids:
            if 'ss' in i:
                ssid = i.replace('ss', '')
            if 'ep' in i:
                epid = i.replace('ep', '')
            if 'dur' in i:
                duration = int(i.replace('dur', ''))
        if not duration:
            url = 'https://api.bilibili.com/x/web-interface/view?aid={0}&cid={1}'.format(aid, cid)
            rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
            jRoot = json.loads(rsp.text)
            duration = jRoot['data']['duration']
        url = 'https://api.bilibili.com/x/player/v2?aid={0}&cid={1}'.format(aid, cid)
        rsp = self.fetch(url, cookies=self.cookies, headers=self.header)
        jo = json.loads(rsp.text)
        played_time = 0
        if int(jo['data']['last_play_cid']) == int(cid):
            last_play_time = int(jo['data']['last_play_time'])
            if last_play_time > 0:
                played_time = int(last_play_time / 1000)
        heartbeat_times = int((duration - played_time) / self.heartbeat_interval) + 1
        self.post_heartbeat_event.set()
        t = threading.Thread(target=self.post_heartbeat, args=(aid, cid, ssid, epid, heartbeat_times, played_time, ))
        t.start()
        self.heartbeat_count = 0
        while self.post_heartbeat_event.is_set():
            time.sleep(1)
            self.heartbeat_count += 1
            if self.heartbeat_count == self.heartbeat_interval:
                self.heartbeat_count = 0
                with self.heartbeat_con:
                    self.heartbeat_con.notifyAll()
                
    def post_live_history(self, room_id):
        data = {'room_id': str(room_id), 'platform': 'pc', 'csrf': str(self.csrf)}
        url = 'https://api.live.bilibili.com/xlive/web-room/v1/index/roomEntryAction'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_follow(self, mid, act):
        data = {'fid': str(mid), 'act': str(act), 'csrf': str(self.csrf)}
        url = 'https://api.bilibili.com/x/relation/modify'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_special(self, mid, act):
        data = {'fids': str(mid), 'tagids': str(act), 'csrf': str(self.csrf)}
        url = 'https://api.bilibili.com/x/relation/tags/addUsers'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_like(self, aid, act):
        data = {'aid': str(aid), 'like': str(act), 'csrf': str(self.csrf)}
        url = 'https://api.bilibili.com/x/web-interface/archive/like'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_coin(self, aid, coin_num):
        data = {'aid': str(aid), 'multiply': str(coin_num), 'select_like': '1', 'csrf': str(self.csrf)}
        url = 'https://api.bilibili.com/x/web-interface/coin/add'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_fav(self, aid, act):
        data = {'rid': str(aid), 'type': '2', 'csrf': str(self.csrf)}
        if str(act) == '0':
            data['add_media_ids'] = '0'
        else:
            data['del_media_ids'] = str(act)
        url = 'https://api.bilibili.com/x/v3/fav/resource/deal'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_triple(self, aid):
        data = {'aid': str(aid), 'csrf': str(self.csrf)}
        url = 'https://api.bilibili.com/x/web-interface/archive/like/triple'
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    def do_zhui(self, season_id, act):
        data = {'season_id': str(season_id), 'csrf': str(self.csrf)}
        url = 'https://api.bilibili.com/pgc/web/follow/{0}'.format(act)
        self.post(url=url, headers=self.header, cookies=self.cookies, data=data)

    get_cid_event = threading.Event()
    
    def get_cid(self, video):
        url = "https://api.bilibili.com/x/web-interface/view?aid=%s" % str(video['aid'])
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
        jRoot = json.loads(rsp.text)
        jo = jRoot['data']
        video['cid'] = jo['cid']
        video['duration'] = jo['duration']
        if 'redirect_url' in jo and 'bangumi' in jo['redirect_url']:
            video['ep'] = self.find_bangumi_id(jo['redirect_url'])
        self.get_cid_event.set()

    def start_set_cookie(self, key, vip):
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=' + key
        rsp = self.fetch(url, headers=self.header, cookies=self.cookies_fake)
        cookie_dic = dict(rsp.cookies)
        cookie_dic = {**self.cookies_fake, **cookie_dic}
        if int(vip):
            self.userConfig_new['cookie_vip_dic'] = self.userConfig['cookie_vip_dic'] = cookie_dic
            t = threading.Thread(target=self.getVIPCookie)
            t.start()
        else:
            self.userConfig_new['cookie_dic'] = self.userConfig['cookie_dic'] = cookie_dic
            t = threading.Thread(target=self.getCookie)
            t.start()

    def unset_cookie(self, vip):
        if int(vip):
            self.cookies_vip = ''
            if self.userConfig.get('cookie_vip_dic', ''):
                self.userConfig.pop('cookie_vip_dic')
            if self.userConfig_new.get('cookie_vip_dic', ''):
                self.userConfig_new.pop('cookie_vip_dic')
        else:
            self.cookies = self.cookies_fake
            self.isLogin = 0
            if self.userConfig.get('cookie_dic', ''):
                self.userConfig.pop('cookie_dic')
            if self.userConfig_new.get('cookie_dic', ''):
                self.userConfig_new.pop('cookie_dic')
        self.dump_config()

    def playerContent(self, flag, id, vipFlags):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        result = {'playUrl': '', 'url': ''}
        ids = id.split("_")
        if 'web' in id or '2' == ids[0]:
            return self.live_playerContent(flag, id, vipFlags)
        if len(ids) < 2:
            return result
        aid = ids[0]
        cid = ids[1]
        self.get_cid_event.set()
        if cid == 'cid':
            self.get_cid_event.clear()
            video = {'aid': str(aid)}
            t = threading.Thread(target=self.get_cid, args=(video, ))
            t.start()
        if 'setting' in id:
            if 'login' in id:
                key = aid
                vip = cid
                t = threading.Thread(target=self.start_set_cookie, args=(key, vip, ))
                t.start()
            elif 'logout' in id:
                vip = aid
                t = threading.Thread(target=self.unset_cookie, args=(vip, ))
                t.start()
            return result
        if 'zhui' in id:
            self.do_zhui(aid, cid)
            return result
        if 'follow' in id:
            if 'special' in id:
                self.do_special(aid, cid)
            else:
                self.do_follow(aid, cid)
            return result
        if 'notplay' in id:
            if 'like' in id:
                self.do_like(aid, cid)
            elif 'coin' in id:
                self.do_coin(aid, cid)
            elif 'fav' in id:
                self.do_fav(aid, cid)
            elif 'triple' in id:
                self.do_triple(aid)
            return result
        if not self.get_cid_event.is_set():
            self.get_cid_event.wait()
            cid = video['cid']
            ids.append('dur' + str(video['duration']))
            if 'ep' in video:
                id += '_' + video['ep']
                ids.append(video['ep'])
        url = 'https://api.bilibili.com/x/player/playurl?avid={0}&cid={1}&qn=116'.format(aid, cid)
        cookies = self.cookies
        if 'ep' in id:
            if 'parse' in id:
                test = list(x for x in map(lambda x: x if 'ep' in x else None, ids) if x is not None)
                url = 'https://www.bilibili.com/bangumi/play/' + test[0]
                result["url"] = url
                result["flag"] = 'bilibili'
                result["parse"] = 1
                result['jx'] = 1
                result["header"] = {"User-Agent": self.header["User-Agent"]}
                return result
            url = 'https://api.bilibili.com/pgc/player/web/playurl?aid={0}&cid={1}&qn=116'.format(aid, cid)
            if self.cookies_vip:
                cookies = self.cookies_vip
        # 回传播放历史记录
        if self.isLogin and self.heartbeat_interval > 0:
            t = threading.Thread(target=self.start_heartbeat, args=(aid, cid, ids, ))
            t.start()
        rsp = self.fetch(url, cookies=cookies, headers=self.header)
        jRoot = json.loads(rsp.text)
        if jRoot['code'] == 0:
            if 'data' in jRoot:
                jo = jRoot['data']
            elif 'result' in jRoot:
                jo = jRoot['result']
            else:
                return result
        else:
            return result
        ja = jo['durl']
        maxSize = -1
        position = -1
        for i in range(len(ja)):
            tmpJo = ja[i]
            if maxSize < int(tmpJo['size']):
                maxSize = int(tmpJo['size'])
                position = i
        url = ''
        if len(ja) > 0:
            if position == -1:
                position = 0
            result["url"] = ja[position]['url']
        result["parse"] = 0
        result["contentType"] = 'video/x-flv'
        result["header"] = self.header
        return result

    def live_playerContent(self, flag, id, vipFlags):
        t = threading.Thread(target=self.stop_heartbeat())
        t.start()
        result = {'playUrl': '', 'url': ''}
        ids = id.split("_")
        if len(ids) < 2:
            return result
        if 'follow' in id:
            self.do_follow(ids[0], ids[1])
            return result
        # 回传观看直播记录
        if self.isLogin and self.heartbeat_interval > 0:
            t = threading.Thread(target=self.post_live_history, args=(ids[-1], ))
            t.start()
        if ids[0] == '2':
            qn = int(ids[1])
            format = int(ids[2])
            codec = int(ids[3])
            num = int(ids[4])
            room_id = int(ids[-1])
            url = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={0}&protocol=0,1&format={1}&codec={2}&qn={3}&platform=web'.format(room_id, format, codec, qn)
            rsp = self.fetch(url, cookies=self.cookies, headers=self.header)
            jo = json.loads(rsp.text)
            if jo['code'] == 0:
                playurl_info = jo['data']['playurl_info']
                try:
                    codec = playurl_info['playurl']['stream'][0]['format'][0]['codec'][0]
                except:
                    return
                base_url = str(codec['base_url'])
                try:
                    host = str(codec['url_info'][num]['host'])
                    extra = str(codec['url_info'][num]['extra'])
                except:
                    host = str(codec['url_info'][0]['host'])
                    extra = str(codec['url_info'][0]['extra'])
                playurl = host + base_url + extra
                result["url"] = playurl
                if ".flv" in playurl:
                    result["contentType"] = 'video/x-flv'
                else:
                    result["contentType"] = ''
            else:
                return result
        else:
            url = 'https://api.live.bilibili.com/room/v1/Room/playUrl?cid=%s&%s' % (ids[1], ids[0])
            # raise Exception(url)
            try:
                rsp = self.fetch(url, headers=self.header, cookies=self.cookies)
            except:
                return result
            jRoot = json.loads(rsp.text)
            if jRoot['code'] == 0:
                jo = jRoot['data']
                ja = jo['durl']
                if len(ja) > 0:
                    result["url"] = ja[0]['url']
                if "h5" in ids[0]:
                    result["contentType"] = ''
                else:
                    result["contentType"] = 'video/x-flv'
            else:
                return result
        result["parse"] = 0
        # result['type'] ="m3u8"
        result["header"] = {
            "Referer": "https://live.bilibili.com",
            "User-Agent": self.header["User-Agent"]
        }
        return result

    config = {
        "player": {},
        "filter": {
            "关注": [{"key": "sort", "name": "分类",
                      "value": [{"n": "正在直播", "v": "正在直播"},
                                {"n": "最近关注", "v": "最近关注"}, {"n": "特别关注", "v": "特别关注"},
                                {"n": "悄悄关注", "v": "悄悄关注"}, {"n": "我的粉丝", "v": "我的粉丝"}]}],
            "动态": [{"key": "order", "name": "个人动态排序",
                    "value": [{"n": "最新发布", "v": "pubdate"}, {"n": "最多播放", "v": "click"},
                              {"n": "最多收藏", "v": "stow"}, {"n": "最早发布", "v": "oldest"}]}, ],
            "影视": [{"key": "tid", "name": "分类",
                      "value": [{"n": "番剧", "v": "1"}, {"n": "国创", "v": "4"}, {"n": "电影", "v": "2"},
                              {"n": "电视剧", "v": "5"}, {"n": "纪录片", "v": "3"}, {"n": "综艺", "v": "7"}]},
                    {"key": "order", "name": "排序",
                      "value": [{"n": "热门", "v": "热门"}, {"n": "播放数量", "v": "2"}, {"n": "更新时间", "v": "0"},
                                {"n": "最高评分", "v": "4"}, {"n": "弹幕数量", "v": "1"}, {"n": "追看人数", "v": "3"},
                                {"n": "开播时间", "v": "5"}, {"n": "上映时间", "v": "6"}]},
                    {"key": "season_status", "name": "付费",
                      "value": [{"n": "全部", "v": "-1"}, {"n": "免费", "v": "1"},
                                {"n": "付费", "v": "2%2C6"}, {"n": "大会员", "v": "4%2C6"}]}],
            "频道": [{"key": "order", "name": "排序",
                    "value": [{"n": "近期热门", "v": "hot"}, {"n": "月播放量", "v": "view"},
                              {"n": "最新投稿", "v": "new"}, {"n": "频道精选", "v": "featured"}, ]}, ],
            "收藏": [{"key": "order", "name": "排序",
                      "value": [{"n": "收藏时间", "v": "mtime"}, {"n": "播放量", "v": "view"},
                                {"n": "投稿时间", "v": "pubtime"}]}, ],
            "历史": [{"key": "type", "name": "分类",
                          "value": [{"n": "视频", "v": "archive"}, {"n": "直播", "v": "live"}, {"n": "UP主", "v": "UP主"}, {"n": "稍后再看", "v": "稍后再看"}]}, ],
            "搜索": [{"key": "type", "name": "类型",
                      "value": [{"n": "视频", "v": "video"}, {"n": "番剧", "v": "media_bangumi"}, {"n": "影视", "v": "media_ft"},
                                {"n": "直播", "v": "live"}, {"n": "用户", "v": "bili_user"}]},
                    {"key": "order", "name": "视频排序",
                      "value": [{"n": "综合排序", "v": "totalrank"}, {"n": "最新发布", "v": "pubdate"}, {"n": "最多点击", "v": "click"},
                                {"n": "最多收藏", "v": "stow"}, {"n": "最多弹幕", "v": "dm"}]},
                    {"key": "duration", "name": "视频时长",
                      "value": [{"n": "全部", "v": "0"}, {"n": "60分钟以上", "v": "4"}, {"n": "30~60分钟", "v": "3"},
                                {"n": "5~30分钟", "v": "2"}, {"n": "5分钟以下", "v": "1"}]}],
        }
    }

    header = {
        "Referer": "https://www.bilibili.com",
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36'
    }

    def localProxy(self, param):

        return [200, "video/MP2T", action, ""]
