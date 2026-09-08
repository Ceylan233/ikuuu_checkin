# ikuuu机场签到

## 作用
> 每天进行签到，获取额外的流量奖励<br/>
> 2026年4月ikuuu新增登录请求验证Geetest v4，不使用过验证方式已无法正常签到<br/>
> 支持登录邮箱验证码：账号配置提供邮箱密码或授权码时，通过 IMAP 自动读取 8 位验证码<br/>
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
| ACCOUNTS | ⚠ 必须 | 每行 `账号邮箱:iKuuu密码:邮箱密码或授权码`，第三段可省略 |
| IKUUU_DOMAIN | 可选 | 自定义 iKuuu 域名，支持填写域名或完整 URL |
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
| IKUUU_IMAP_PROVIDER | 可选 | 邮箱类型，默认 auto 自动识别 |
| IKUUU_IMAP_HOST | 自定义时 | IMAP 服务器 |
| IKUUU_IMAP_PORT | 可选 | IMAP 端口，默认 993 |
| IKUUU_IMAP_SECURITY | 可选 | ssl/starttls/plain |
| IKUUU_IMAP_FOLDER | 可选 | 验证码邮件目录，默认 INBOX |
| IKUUU_EMAIL_CODE_TIMEOUT_SECONDS | 可选 | 等待邮箱验证码超时，默认 120 秒 |
| IKUUU_EMAIL_CODE_POLL_INTERVAL_SECONDS | 可选 | 邮箱轮询间隔，默认 2 秒 |

推荐使用 CapSolver 过验证，使用此链接注册后充值可额外获得 6% 充值额度：  
https://dashboard.capsolver.com/passport/register?inviteCode=xtoNMmGLED4g  

平台最低充值 6 美元。  

签到价格约为 0.0016 美元(0.011￥)/次（单账号），重复签到仍会计费。  

---
**ACCOUNTS 写法：**  
每行一个账号，支持以下两种格式：

```text
账号邮箱:iKuuu密码
账号邮箱:iKuuu密码:邮箱密码或授权码
```

第三段可省略。省略时保持原有登录逻辑；站点要求邮箱验证码时会提示缺少邮箱授权码。填写第三段后，脚本会根据账号邮箱自动识别 QQ/Foxmail、163、126、Gmail、Yahoo 或 Outlook 的 IMAP 服务，读取本次登录邮件中的 8 位验证码并继续登录。

QQ、163、126 等邮箱通常应填写邮箱后台生成的授权码，不要填写网页登录密码。请先在邮箱设置中开启 IMAP 服务。GitHub Actions 用户应将完整多行内容放在 `ACCOUNTS` Secret 中；OpenWrt 配置文件权限会设置为 `600`。

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
opkg install luci-app-ikuuu-checkin_1.2.2-1_all.ipk
```

安装后进入 LuCI 的“服务 → iKuuu 签到”，可配置多账号、自定义 iKuuu 域名、验证码服务、登录邮箱验证、通知邮箱和每日定时，也可手动签到或发送测试邮件。常见邮箱保持“自动识别”即可，自建邮箱可在“邮箱验证”标签页填写 IMAP 参数。

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
<img width="750" height="555" alt="image" src="https://github.com/user-attachments/assets/cc8eef80-286b-4d4d-9ddb-059313780cc9" />
<img width="565" height="564" alt="image" src="https://github.com/user-attachments/assets/4f45b50a-4fb0-41b1-89fd-97850e2c9db6" />


**未添加过验证api：** <br/><br/>
<img src="https://github.com/user-attachments/assets/9103aa0a-d4e9-4f60-9244-0d615386c0d8" width="400"><br/>

---
**添加过验证api：** <br/><br/>
<img src="https://github.com/user-attachments/assets/aaf9a41d-df84-495a-b391-306ad3701c55" width="400"/>


