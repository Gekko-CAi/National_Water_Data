# National Water Quality Data

国家地表水水质实时数据自动抓取系统

## 简介

本项目利用 GitHub Actions 每2小时自动从 [国家地表水水质实时数据发布系统](https://szzdjc.cnemc.cn:8070/GJZ/Business/Publish/Main.html) 抓取全国地表水水质实时监测数据，并保存为 CSV 文件。

## 数据说明

| 项目 | 说明 |
|------|------|
| 数据来源 | 中国环境监测总站 - 国家水质自动综合监管平台 |
| 抓取频率 | 每2小时一次 |
| 时区 | 北京时间 (UTC+8) |
| 文件格式 | CSV (UTF-8-BOM 编码) |
| 文件命名 | `National_Water_YYYYMMDD.csv` (按天保存) |
| 存储路径 | `Data/` 文件夹 |

### 数据字段

| 序号 | 字段 | 说明 |
|------|------|------|
| 1 | 省份 | 监测断面所在省份 |
| 2 | 流域 | 监测断面所在流域 |
| 3 | 断面名称 | 监测断面名称 |
| 4 | 监测时间 | 数据监测时间 (YYYY-MM-DD HH:MM) |
| 5 | 水质类别 | I-V类及劣V类 |
| 6 | 水温(℃) | 水温 |
| 7 | pH(无量纲) | pH值 |
| 8 | 溶解氧(mg/L) | 溶解氧浓度 |
| 9 | 电导率(μS/cm) | 电导率 |
| 10 | 浊度(NTU) | 浊度 |
| 11 | 高锰酸盐指数(mg/L) | 高锰酸盐指数 |
| 12 | 氨氮(mg/L) | 氨氮浓度 |
| 13 | 总磷(mg/L) | 总磷浓度 |
| 14 | 总氮(mg/L) | 总氮浓度 |
| 15 | 叶绿素α(mg/L) | 叶绿素a浓度 |
| 16 | 藻密度(cells/L) | 藻类密度 |

### 去重规则

每次抓取的数据会与当天已有数据进行去重，以 **断面名称** 和 **监测时间** 作为唯一键。同一断面同一监测时间的数据只保留一条记录，不重复添加。

### 数据追加

每次抓取的数据不会覆盖上一次的数据，而是与已有数据进行融合：
- 首次抓取：创建当天CSV文件，写入所有数据
- 后续抓取：读取已有文件，去重后追加新数据

## 项目结构

```
National_Water_Data/
├── .github/
│   └── workflows/
│       └── scrape.yml          # GitHub Actions 工作流配置
├── scraper/
│   ├── scraper.py              # 数据抓取脚本
│   └── requirements.txt        # Python 依赖
├── Data/                       # 数据存储文件夹
│   └── National_Water_YYYYMMDD.csv
├── .gitignore
└── README.md
```

## 使用方法

### 自动运行

GitHub Actions 会每2小时自动运行一次抓取任务，无需手动干预。

### 手动触发

1. 进入 GitHub 仓库的 **Actions** 页面
2. 选择 **Scrape Water Quality Data** 工作流
3. 点击 **Run workflow** 按钮手动触发

### 本地运行

```bash
# 安装依赖
pip install -r scraper/requirements.txt

# 运行抓取脚本
python scraper/scraper.py
```

## 免责声明

- 数据未经审核，仅供参考
- 本项目仅供学习和研究使用
- 数据版权归中国环境监测总站所有
