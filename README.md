# 我的记账软件

一个使用 Python + SQLite 开发的命令行记账软件。

## 项目简介

这是一个基于 Python 开发的个人记账工具，可以记录日常收入和支出，并支持账单查询、修改、删除以及统计。

本项目主要用于学习 Python 项目开发、SQLite 数据库操作以及模块化编程。

## 功能

- 添加账单
- 查看全部账单
- 修改账单
- 删除账单
- 统计总收入
- 统计总支出
- 统计当前余额
- 按日期查看账单
- 按日期统计收入、支出和余额
- 支持今天、昨天和自定义日期
- 输入数据验证
- SQLite 数据持久化

## 技术栈

- Python
- SQLite
- PyCharm
- Git / GitHub

## 项目结构

```text
记账软件/
│
├── main.py          # 程序入口和菜单
├── account.py       # 记账业务逻辑
├── database.py      # SQLite 数据库操作
├── accounts.db      # SQLite 数据库
├── README.md        # 项目说明
└── .gitignore       # Git 忽略文件