# ikuuu机场签到

## 作用
> 每天进行签到，获取额外的流量奖励

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

| 参数 | 是否必须 | 说明 |
|------|----------|------|
| ACCOUNTS | ✅ 必须 | 账号密码 |
| MAIL_USER | ❌ 可选 | 发件邮箱 |
| MAIL_PASS | ❌ 可选 | 邮箱应用密码 |
| MAIL_TO | ❌ 可选 | 收件邮箱 |
| IKUUU_CAPTCHA_SOLVER_ENABLED | ❌ 可选 | 是否启用验证码 |
| IKUUU_CAPTCHA_PROVIDER | ❌ 可选 | 验证码服务商 |
| IKUUU_CAPSOLVER_API_KEY | ❌ 可选 | CapSolver Key |
| IKUUU_ANTICAPTCHA_API_KEY | ❌ 可选 | AntiCaptcha Key |
| IKUUU_CAPTCHA_TIMEOUT_SECONDS | ❌ 可选 | 验证码超时 |
| IKUUU_CAPTCHA_POLL_INTERVAL_SECONDS | ❌ 可选 | 轮询间隔 |

---

## 3. ACCOUNTS 写法

```text
邮箱:密码
邮箱:密码
