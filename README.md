# ikuuu机场签到

## 作用
> 每天进行签到，获取额外的流量奖励
> 2026年4月ikuuu新增登录请求验证Geetest v4，不使用过验证方式已无法正常签到

---

## 推送方式
- 🚀 auto_check_in_ikuuu.py 支持：
  - 青龙面板通知
  - Outlook 邮箱
  - 163 邮箱

---

# 部署过程
 
## 1. Fork 仓库
点击右上角 Fork 此仓库

---

## 2. 配置环境变量
进入：

Settings → Secrets and variables → Actions

新建以下变量：
推荐使用CapSolver过验证，使用此链接注册后充值可额外获得6%充值额度：https://dashboard.capsolver.com/passport/register?inviteCode=xtoNMmGLED4g<br/>
平台最低充值6美元。<br/>
签到价格约为0.0016美元/次(单账号)，重复签到仍会计费。
| 参数 | 是否必须 | 说明 |
|------|----------|------|
| ACCOUNTS | ⚠ 必须 | ikuuu账号密码 |
| MAIL_USER | 可选 | 发件邮箱 |
| MAIL_PASS | 可选 | 邮箱应用密码 |
| MAIL_TO | 可选 | 收件邮箱 |
| IKUUU_CAPTCHA_SOLVER_ENABLED | 可选 | 是否启用验证码(0/1) |
| IKUUU_CAPTCHA_PROVIDER | 可选 | 验证码服务商(capsolver/anticaptcha) |
| IKUUU_CAPSOLVER_API_KEY | 可选 | CapSolver Api Key |
| IKUUU_ANTICAPTCHA_API_KEY | 可选 | AntiCaptcha Api Key |
| IKUUU_CAPTCHA_TIMEOUT_SECONDS | 可选 | 验证码超时时间(秒) |
| IKUUU_CAPTCHA_POLL_INTERVAL_SECONDS | 可选 | 轮询间隔(秒) |

ACCOUNTS写法：账号:密码(使用冒号:分隔)，有多个账户则配置多行<br/> 
MAIL_TO：有多个接收通知的账户用逗号‘,’分割 不需要通知可不填写邮箱相关参数 
---
## 3. 到Actions中创建一个workflow，运行一次，以后每天项目都会自动运行。<br/> 
---
## 4. 最后，可以到Run sign查看签到情况，同时也会也会将签到详情推送。
