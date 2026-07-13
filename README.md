# ikuuu机场签到

## 作用
> 每天进行签到，获取额外的流量奖励<br/>
> 2026年4月ikuuu新增登录请求验证Geetest v4，不使用过验证方式已无法正常签到<br/>
> 添加cookie缓存登陆，帐密登录后自动记录cookie，有效期内进行签到不消耗token，单账号理论7天最低0.0016$(0.011￥)，单次充值6美元单账号可用27000+天

---

## 推送方式
- 🚀 auto_check_in_ikuuu.py 支持：
  - 青龙面板通知
  - 163、126、QQ/Foxmail、Gmail、Yahoo、Outlook 邮箱
  - 自定义 SMTP、多个收件人

---

# 部署过程
 
## 1. Fork 仓库
点击右上角 Fork 此仓库

---

## 2. 配置环境变量
进入：

Settings → Secrets and variables → Actions

新建以下变量：<br/>

| 参数 | 是否必须 | 说明 |
|------|----------|------|
| ACCOUNTS | ⚠ 必须 | ikuuu账号密码 |
| MAIL_USER | 可选 | 发件邮箱 |
| MAIL_PASS | 可选 | 邮箱应用密码 |
| MAIL_TO | 可选 | 收件邮箱 |
| MAIL_PROVIDER | 可选 | 邮箱类型，默认自动识别 |
| SMTP_HOST | 自定义时 | SMTP 服务器 |
| SMTP_USERNAME | 可选 | SMTP 登录用户名，默认与发件邮箱相同 |
| SMTP_PORT | 可选 | SMTP 端口 |
| SMTP_SECURITY | 可选 | ssl/starttls/plain |
| IKUUU_CAPTCHA_SOLVER_ENABLED | 可选 | 是否启用验证码(0/1) |
| IKUUU_CAPTCHA_PROVIDER | 可选 | 验证码服务商(capsolver/anticaptcha) |
| IKUUU_CAPSOLVER_API_KEY | 可选 | CapSolver Api Key |
| IKUUU_ANTICAPTCHA_API_KEY | 可选 | AntiCaptcha Api Key |
| IKUUU_CAPTCHA_TIMEOUT_SECONDS | 可选 | 验证码超时时间(秒) |
| IKUUU_CAPTCHA_POLL_INTERVAL_SECONDS | 可选 | 轮询间隔(秒) |

推荐使用 CapSolver 过验证，使用此链接注册后充值可额外获得 6% 充值额度：  
https://dashboard.capsolver.com/passport/register?inviteCode=xtoNMmGLED4g  

平台最低充值 6 美元。  

签到价格约为 0.0016 美元(0.011￥)/次（单账号），重复签到仍会计费。  

---
**ACCOUNTS 写法：**  
账号:密码（使用冒号`:`分隔），有多个账户则配置多行`回车换行`

**MAIL_TO：**  
有多个接收通知的账户用逗号 `,` 分割  

不需要通知可不填写邮箱相关参数

---
## 3. 自动运行
### 方式一：GitHub Actions
创建 workflow 后运行一次，之后每天自动执行
### 方式二：云服务器（推荐）
更推荐使用云服务器，更稳定，时间更精准，不会被github检测为薅羊毛。<br/> 
**优点：**

- 更稳定  
- 时间更精准  
- 不易被风控  

---

### 方式三：OpenWrt / iStoreOS 软件包

从 [Releases](https://github.com/Ceylan233/ikuuu_checkin/releases) 下载 IPK 后安装：

```sh
opkg install luci-app-ikuuu-checkin_1.0.1-1_all.ipk
```

安装后进入 LuCI 的“服务 → iKuuu 签到”，可配置多账号、验证码服务、邮箱、每日定时，也可手动签到或发送测试邮件。

---

#### Linux 启动脚本

```bash
#!/bin/bash
source /etc/profile

cd /root/ikuuu_checkin || exit 1

export ACCOUNTS=""
export MAIL_USER=""
export MAIL_PASS=""
export MAIL_TO=""

export IKUUU_CAPTCHA_SOLVER_ENABLED="1"
export IKUUU_CAPTCHA_PROVIDER="capsolver"
export IKUUU_CAPSOLVER_API_KEY=""
export IKUUU_CAPTCHA_TIMEOUT_SECONDS="120"
export IKUUU_CAPTCHA_POLL_INTERVAL_SECONDS="3"

/usr/bin/python3 /root/ikuuu_checkin/auto_check_in_ikuuu.py
```

---

## 4. 最后，可以到Run sign查看签到情况，同时也会也会将签到详情推送。

## 运行截图

**未添加过验证api：** <br/><br/>
<img src="https://github.com/user-attachments/assets/9103aa0a-d4e9-4f60-9244-0d615386c0d8" width="400"><br/>

---
**添加过验证api：** <br/><br/>
<img src="https://github.com/user-attachments/assets/aaf9a41d-df84-495a-b391-306ad3701c55" width="400"/>


