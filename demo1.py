import requests
from loguru import logger
import json
import random
import time
from datetime import datetime, timedelta
import cv2
import numpy as np
import base64
import sys
sys.stdout.reconfigure(encoding='utf-8')
def generate_slide_track(distance_x, distance_y=0, points_num=100, duration_ms=None):
    """
    生成滑块移动轨迹数据
    
    参数:
    - distance_x: 水平移动距离
    - distance_y: 垂直移动距离（默认为0）
    - points_num: 轨迹点数量（默认为100）
    - duration_ms: 滑动持续时间（毫秒），默认自动计算（300-800ms范围内）
    """
    # 设置开始时间（当前时间）
    start_time = datetime.now()
    
    # 如果未指定持续时间，随机生成一个合理值
    if duration_ms is None:
        duration_ms = random.randint(300, 800)
    
    # 计算结束时间
    end_time = start_time + timedelta(milliseconds=duration_ms)
    
    # 轨迹参数
    start_x, start_y = 0, 0  # 起始坐标
    end_x = distance_x       # 结束x坐标
    end_y = distance_y       # 结束y坐标
    
    # 生成轨迹点
    track_list = []
    
    # 添加起点（down事件）
    track_list.append({
        "x": start_x,
        "y": start_y,
        "type": "down",
        "t": 1500  # 相对于开始时间的毫秒数
    })
    
    for i in range(1, points_num - 1):
        progress = i / (points_num - 2)
        ease_progress = progress * progress * (3 - 2 * progress)
        
        x = int(start_x + (end_x - start_x) * ease_progress)
        y = int(start_y + (end_y - start_y) * ease_progress)
        
        x += random.randint(-2, 2)
        y += random.randint(-1, 1)
        t = int(duration_ms * ease_progress)
        
        track_list.append({
            "x": x,
            "y": y,
            "type": "move",
            "t": t
        })
    
    # 添加终点（up事件）
    track_list.append({
        "x": end_x,
        "y": end_y,
        "type": "up",
        "t": duration_ms
    })
    
    # 转换时间戳为ISO格式字符串
    start_time_str = start_time.isoformat(timespec='milliseconds') + 'Z'
    end_time_str = end_time.isoformat(timespec='milliseconds') + 'Z'
    
    return {
        "startTime": start_time_str,
        "endTime": end_time_str,
        "duration_ms": duration_ms,
        "trackList": track_list
    }

# 获取滑块距离
def identify_gap(bg, tp):
    """
    bg: 背景图片
    tp: 缺口图片
    out: 输出图片
    """
    # 读取背景图片和缺口图片
    bg_img = cv2.imdecode(np.frombuffer(bg, np.uint8), cv2.IMREAD_GRAYSCALE)
    tp_img = cv2.imdecode(np.frombuffer(tp, np.uint8), cv2.IMREAD_GRAYSCALE)  # 缺口图片
    yy = []
    xx = []
    for y in range(tp_img.shape[0]):
        for x in range(tp_img.shape[1]):
            r = tp_img[y, x]
            if r < 200:
                yy.append(y)
                xx.append(x)
    tp_img = tp_img[min(yy):max(yy), min(xx):max(xx)]
    # 识别图片边缘
    bg_edge = cv2.Canny(bg_img, 100, 200)
    tp_edge = cv2.Canny(tp_img, 100, 200)
    # 转换图片格式
    bg_pic = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)
    tp_pic = cv2.cvtColor(tp_edge, cv2.COLOR_GRAY2RGB)
    # 缺口匹配
    res = cv2.matchTemplate(bg_pic, tp_pic, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)  # 寻找最优匹配
    # # 绘制方框
    th, tw = tp_pic.shape[:2]
    tl = max_loc  # 左上角点的坐标
    br = (tl[0] + tw, tl[1] + th)  # 右下角点的坐标
    cv2.rectangle(bg_img, tl, br, (0, 0, 255), 2)  # 绘制矩形
    cv2.imwrite('distinguish.jpg', bg_img)  # 保存在本地
    # 返回缺口的X坐标
    return max_loc[0]


class runningHubSilder():
    def __init__(self):
        self.session = requests.Session()
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.runninghub.cn",
            "Pragma": "no-cache",
            "Referer": "https://www.runninghub.cn/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"136\", \"Google Chrome\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        self.session.headers.update(headers)

    def genCaptcha(self):
        url = "https://www.runninghub.cn/uc/genCaptcha"
        params = {
            "type": "CURVE2"
        }
        data = {}
        data = json.dumps(data, separators=(',', ':'))
        response = self.session.post(url, params=params, data=data).json()
        # print(response)
        return response

    def checkCaptcha(self, genCaptcha_data):
        url = "https://www.runninghub.cn/uc/checkCaptcha"
        backgroundImage = base64.b64decode(genCaptcha_data['captcha']['backgroundImage'].replace('data:image/jpeg;base64,', ''))
        templateImage = base64.b64decode(genCaptcha_data['captcha']['templateImage'].replace('data:image/png;base64,',''))
        gay = int(identify_gap(backgroundImage, templateImage) * 0.512)
        # print(identify_gap(backgroundImage, templateImage))
        logger.debug(f'缺口距离:{gay}')
        result = generate_slide_track(distance_x=gay, distance_y=-2)
        data = {
            "id": genCaptcha_data["id"],
            "data": {
                "bgImageWidth": 300,
                "bgImageHeight": 180,
                "startTime": result['startTime'],
                "stopTime": result['endTime'],
                "trackList": result['trackList']
            }
        }
        data = json.dumps(data, separators=(',', ':'))
        response = self.session.post(url, data=data)
        logger.debug(f"请求结果: {response.text}")
        return response.json()

    def main(self):
        genCaptcha_data = self.genCaptcha()
        checkCaptcha_data = self.checkCaptcha(genCaptcha_data)



if __name__ == '__main__':
    success_count = 0
    total_count = 1

    for i in range(total_count):
        try:
            captcha_solver = runningHubSilder()
            genCaptcha_data = captcha_solver.genCaptcha()
            checkCaptcha_data = captcha_solver.checkCaptcha(genCaptcha_data)

            if checkCaptcha_data.get("code") == 200:
                success_count += 1
                logger.info(f"[{i+1}/{total_count}] 验证成功")
            else:
                logger.warning(f"[{i+1}/{total_count}] 验证失败，返回码: {checkCaptcha_data.get('code')}")
        except Exception as e:
            logger.error(f"[{i+1}/{total_count}] 异常: {e}")

    success_rate = (success_count / total_count) * 100
    logger.success(f"总共尝试: {total_count} 次")
    logger.success(f"成功次数: {success_count}")
    logger.success(f"成功率: {success_rate:.2f}%")
