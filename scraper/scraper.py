#!/usr/bin/env python3
"""
国家地表水水质实时数据抓取脚本
数据来源: 国家地表水水质实时数据发布系统
URL: https://szzdjc.cnemc.cn:8070/GJZ/Business/Publish/Main.html

功能:
  - 从国家地表水水质实时数据发布系统抓取所有断面的实时监测数据
  - 支持分页获取全部数据
  - 按天保存为CSV文件 (National_Water_YYYYMMDD.csv)
  - 同一断面同一监测时间的数据自动去重
  - 每次抓取的数据追加到当天已有文件中 (不覆盖)
  - 时间按北京时间 (UTC+8) 计算
"""

import requests
import csv
import os
import re
import urllib3
from datetime import datetime, timezone, timedelta

# 禁用SSL警告 (该网站使用自签名证书)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 北京时间 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# API配置
API_URL = "https://szzdjc.cnemc.cn:8070/GJZ/Ajax/Publish.ashx"
REQUEST_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://szzdjc.cnemc.cn:8070/GJZ/Business/Publish/RealDatas.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://szzdjc.cnemc.cn:8070",
}

# CSV列名 (与网页表头对应，已清理HTML标签)
COLUMNS = [
    "省份",
    "流域",
    "断面名称",
    "监测时间",
    "水质类别",
    "水温(℃)",
    "pH(无量纲)",
    "溶解氧(mg/L)",
    "电导率(μS/cm)",
    "浊度(NTU)",
    "高锰酸盐指数(mg/L)",
    "氨氮(mg/L)",
    "总磷(mg/L)",
    "总氮(mg/L)",
    "叶绿素α(mg/L)",
    "藻密度(cells/L)",
]


def clean_value(text):
    """
    从API返回的HTML片段中提取纯数据值。

    API返回的数据值可能包含以下格式:
      - "--" 表示无数据
      - "<span title='原始值：27.78'>27.8</span>" 优先提取原始值
      - 纯文本数字 如 "2"
    """
    if not text or text == "--":
        return ""
    # 尝试从 title 属性中提取原始值
    match = re.search(r"原始值：([0-9.]+)", text)
    if match:
        return match.group(1)
    # 尝试提取 span 标签内的显示文本
    match = re.search(r">([^<]+)<", text)
    if match:
        val = match.group(1).strip()
        return "" if val == "--" else val
    # 无HTML标签，直接返回
    return text.strip()


def fetch_all_data():
    """
    从API获取所有断面的实时监测数据。

    支持分页: 当数据量超过单页上限时自动获取后续页面。
    返回: list of list, 每个内部列表代表一条记录 (已清洗)
    """
    all_data = []
    page_index = 1
    page_size = 200  # API有每页最大返回限制，PageSize过大会导致数据截断
    total_pages = 1

    while page_index <= total_pages:
        params = {
            "action": "getRealDatas",
            "AreaID": "",
            "RiverID": "",
            "MNName": "",
            "PageIndex": str(page_index),
            "PageSize": str(page_size),
        }

        try:
            response = requests.post(
                API_URL,
                data=params,
                headers=REQUEST_HEADERS,
                verify=False,  # 该网站使用自签名证书
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"[ERROR] 第 {page_index} 页数据获取失败: {e}")
            break

        if result.get("result") == 0 or "tbody" not in result:
            print(f"[WARN] 第 {page_index} 页无数据返回")
            break

        # 第一页时获取总页数
        if page_index == 1:
            total_pages = result.get("total", 1)
            records = result.get("records", "unknown")
            print(f"总页数: {total_pages}, 总记录数: {records}")

        tbody = result["tbody"]
        for row in tbody:
            cleaned_row = [clean_value(cell) for cell in row]
            all_data.append(cleaned_row)

        print(f"第 {page_index}/{total_pages} 页: 获取 {len(tbody)} 条数据")
        page_index += 1

        # 页间短暂延迟，避免请求过快被限制
        if page_index <= total_pages:
            import time
            time.sleep(1)

    return all_data


def add_year_to_monitor_time(time_str, now):
    """
    为监测时间添加年份。

    API返回的监测时间格式为 "MM-DD HH:MM" (无年份)，
    此函数根据当前北京时间推断年份并补全为 "YYYY-MM-DD HH:MM"。

    跨年处理: 如果当前是1月而监测时间是12月，则年份为上一年。
    """
    if not time_str:
        return ""
    try:
        parts = time_str.strip().split(" ")
        date_part = parts[0]  # MM-DD
        time_part = parts[1] if len(parts) > 1 else ""
        month_day = date_part.split("-")
        month = int(month_day[0])

        current_year = now.year
        current_month = now.month

        # 处理跨年情况: 1月份看到12月的数据，应为去年
        if month == 12 and current_month == 1:
            year = current_year - 1
        else:
            year = current_year

        return f"{year}-{date_part} {time_part}".strip()
    except Exception:
        return time_str


def main():
    """主函数: 抓取数据 -> 去重合并 -> 保存CSV"""
    # 获取当前北京时间
    now = datetime.now(BEIJING_TZ)
    today_str = now.strftime("%Y%m%d")
    filename = f"National_Water_{today_str}.csv"
    data_dir = "Data"
    filepath = os.path.join(data_dir, filename)

    # 创建数据目录
    os.makedirs(data_dir, exist_ok=True)

    # ===== 第一步: 抓取新数据 =====
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取数据...")
    new_data = fetch_all_data()
    print(f"共抓取到 {len(new_data)} 条数据")

    if not new_data:
        print("[ERROR] 未获取到任何数据，程序退出")
        return

    # 为监测时间添加年份
    for row in new_data:
        if len(row) > 3:
            row[3] = add_year_to_monitor_time(row[3], now)

    # ===== 第二步: 读取已有数据 =====
    existing_data = []
    existing_keys = set()
    file_exists = os.path.exists(filepath)

    if file_exists:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # 跳过表头
            for row in reader:
                existing_data.append(row)
                # 去重键: (断面名称, 监测时间)
                key = (row[2], row[3]) if len(row) > 3 else None
                if key:
                    existing_keys.add(key)
        print(f"已有数据: {len(existing_data)} 条")
    else:
        print("首次抓取，创建新文件")

    # ===== 第三步: 去重并合并数据 =====
    merged_data = list(existing_data)
    new_count = 0
    for row in new_data:
        key = (row[2], row[3]) if len(row) > 3 else None
        if key and key not in existing_keys:
            merged_data.append(row)
            existing_keys.add(key)
            new_count += 1

    print(f"新增数据: {new_count} 条, 合并后总计: {len(merged_data)} 条")

    # ===== 第四步: 写入CSV文件 =====
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(merged_data)

    print(f"数据已保存到: {filepath}")
    print("抓取完成!")


if __name__ == "__main__":
    main()
