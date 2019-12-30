#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# @Author   : Erwin Lyu

"""天津大学材料平台自动记录台账脚本

该文件用于自动完成天大材料平台记录台账

使用方法: 在程序入口点(文件最下方)处填写账号、密码、所需记录的台账的起始和终止页码

版本历史:
        ----version 1.0 首次提交
        ----version 1.1 解决了"保管人"一栏为空时程序中断的问题

references:
https://zhuanlan.zhihu.com/p/33331091
https://zhuanlan.zhihu.com/p/63916386
Acknowledgement: @youqingxiaozhua
"""

import urllib3
import requests
from lxml import etree
import http
import sys
import re

urllib3.disable_warnings()

class Ledger_Processing():
    def __init__(self):
        self.s = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'
        }
        self.form_data = {
            'username': 'usrname',
            'password': 'pwd',
            'execution': '',
            '_eventId': 'submit',
            'submit': 'submit'
        }
        self.s.verify = False

    def login(self, usrname, pwd):

        """
        登录模块
        """

        self.form_data['username'] = usrname
        self.form_data['password'] = pwd
        
        # "我的台账"首页
        server_url = "http://59.67.37.36/tshop/src/My/Ledger.html"
        print("connecting server...\n")

        # 获得sso登录链接
        reps = self.s.get(server_url, headers=self.headers)
        cas_login_url = reps.url
        print("redirecting to cas server: {0}\n".format(cas_login_url))

        # 重定向到sso登录页面
        reps = self.s.get(server_url, headers=self.headers)
        print(reps.cookies)
        if reps.status_code == 200:
            print("redirected to cas login server.\n")

        # 获取令牌
        selector = etree.HTML(reps.text)
        execution = selector.xpath('//div//input[1]/@value')[2]
        self.form_data['execution'] = execution

        # 完成登录
        reps = self.s.post(cas_login_url, data=self.form_data, headers=self.headers)
        if reps.status_code == 200:
            print("successfully POSTed.\n")
        reps = self.s.get(reps.url)

    def postpone(self, origin):

        """
        将"领用时间"设定为采购清单详情页所示日期之后的3天
        如果超过第28日则定为下个月的第3天
        """

        year = int(origin[0:4])
        month = int(origin[4:6])
        day = int(origin[6:8]) + 3
        if day > 28:
            day = 2
            month = month + 1
        time_str = "-" + "{:0>2d}".format(day)
        if month > 12:
            month = 1
            year = year + 1
        time_str = "-" + "{:0>2d}".format(month) + time_str
        time_str = "{:0>2d}".format(year) + time_str
        return time_str

    def ledger_processor(self, usrname, pwd, page_start, page_end):

        """
        记录台账模块
        """

        pay_load = {
            'user': 'usr',
            'use_num': 0,
            'remark': "办公",
            'use_time': '2019-12-31',
            'rec_id': 'xxx',
            'order_id': 'xxx',
            'sy_num': 0
        }

        # 登录
        tshop.login(usrname=usrname, pwd=pwd)

        for page in range(page_start - 1, page_end):
            server_url = "http://59.67.37.36/tshop/src/My/Ledger/pageNo-{}.html".format(page)
            reps = self.s.get(server_url, headers=self.headers)
            selector = etree.HTML(reps.text)

            # 每一页共有10个条目
            for i in range(1, 11):
                usedOrNot = selector.xpath("string(//table/tbody/tr[$val]/td[12]/span/text())", val=i)
                if len(usedOrNot) == 0:
                    break
                else:
                    usedOrNot = usedOrNot.split()[0]
                
                # 挑选出"尚未使用"的条目
                # 将使用人、数量、备注和领用时间信息填入payload
                if usedOrNot == "尚未使用":
                    person = selector.xpath("string(//table/tbody/tr[$val]/td[11]/text())", val=i)
                    try:
                        person = person.split()[0]
                    except:
                        print("********WARNING: page{}-item{} has no keeper's name, please handle it manually********".format(page + 1, i))
                        continue
                    pay_load['user'] = person
                    remark = selector.xpath("string(//table/tbody/tr[$val]/td[3]/text())", val=i)
                    if len(remark) > 2:
                        remark = remark.split()[0]
                    else:
                        remark = "办公"
                    pay_load['remark'] = remark
                    datestr = selector.xpath("string(//table/tbody/tr[$val]/td[1]/a/text())", val=i)
                    datestr = datestr.split()[0][1:9]
                    datestr = self.postpone(datestr)
                    pay_load['use_time'] = datestr
                    onclick = selector.xpath("string(//table/tbody/tr[$val]/td[13]/button/@onclick)", val=i)
                    pattern = re.compile(r'\d+')
                    match = pattern.findall(onclick)
                    pay_load['rec_id'] = match[0]
                    pay_load['order_id'] = match[1]
                    pay_load['sy_num'] = match[2]
                    pay_load['use_num'] = match[2]
                    post_url = "http://59.67.37.36/tshop/src/My/Ledger/Add/id-1.html"

                    # 填写并提交表单信息, 完成台账记录
                    reps = self.s.post(post_url, data=pay_load, headers=self.headers)
                    if reps.status_code == 200:
                        print("page{0} - item{1} has been processed".format(page + 1, i))
        
        self.s.close()


if __name__ == '__main__':
    """
    usrname=    填写账户
    pwd=        填写密码
    page_start= 填写起始页码
    page_end=   填写终止页码
    """
    tshop = Ledger_Processing()
    tshop.ledger_processor(usrname='usrname', pwd='password', page_start=1, page_end=100)