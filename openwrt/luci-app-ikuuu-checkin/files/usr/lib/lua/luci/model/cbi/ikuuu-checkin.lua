local sys = require "luci.sys"
local util = require "luci.util"

local function trim(value)
	return (value or ""):match("^%s*(.-)%s*$")
end

local m = Map("ikuuu-checkin", translate("iKuuu 签到"))
local s = m:section(NamedSection, "main", "ikuuu", translate("管理"))
s.addremove = false
s:tab("status", translate("运行状态"))

local o = s:taboption("status", DummyValue, "_service", translate("定时服务"))
o.rawhtml = true
function o.cfgvalue()
	if sys.call("/etc/init.d/ikuuu-checkin status >/dev/null 2>&1") == 0 then
		return '<span style="color:#2d8a34;font-weight:bold">运行中</span>'
	end
	return '<span style="color:#b33a3a;font-weight:bold">未运行</span>'
end

o = s:taboption("status", Button, "_run", translate("立即签到"))
o.inputstyle = "apply"
function o.write()
	sys.call("/usr/libexec/ikuuu-checkin/run run >/tmp/ikuuu-checkin.log 2>&1 &")
	m.message = translate("签到任务已启动。")
end

o = s:taboption("status", Button, "_test", translate("发送测试邮件"))
o.inputstyle = "apply"
function o.write()
	local result = sys.call("/usr/libexec/ikuuu-checkin/run test >/tmp/ikuuu-checkin.log 2>&1")
	m.message = result == 0 and translate("测试邮件发送成功。") or translate("发送失败，请查看运行日志。")
end

o = s:taboption("status", DummyValue, "_log", translate("运行日志"))
o.rawhtml = true
function o.cfgvalue()
	local output = trim(sys.exec("tail -n 50 /tmp/ikuuu-checkin.log 2>/dev/null"))
	return '<pre style="max-height:360px;overflow:auto;white-space:pre-wrap">' .. util.pcdata(output ~= "" and output or translate("暂无日志")) .. '</pre>'
end

s:tab("schedule", translate("定时与账号"))
s:tab("captcha", translate("验证码设置"))
s:tab("mail", translate("邮件设置"))
o = s:taboption("schedule", Flag, "enabled", translate("启用每日签到"))
o.default = 0
o.rmempty = false
o = s:taboption("schedule", Value, "hour", translate("小时"))
o.datatype = "range(0,23)"
o.default = 8
o.rmempty = false
o = s:taboption("schedule", Value, "minute", translate("分钟"))
o.datatype = "range(0,59)"
o.default = 0
o.rmempty = false
o = s:taboption("schedule", TextValue, "accounts", translate("签到账号"))
o.rows = 4
o.rmempty = false
o.description = translate("每行一个账号，格式为 邮箱:密码。")

o = s:taboption("captcha", Flag, "captcha_enabled", translate("启用验证码服务"))
o.default = 1
o.rmempty = false
o = s:taboption("captcha", ListValue, "captcha_provider", translate("验证码服务商"))
o:value("capsolver", "CapSolver")
o:value("anticaptcha", "Anti-Captcha")
o.default = "capsolver"
o = s:taboption("captcha", Value, "capsolver_api_key", "CapSolver API Key")
o.password = true
o:depends("captcha_enabled", "1")
o = s:taboption("captcha", Value, "anticaptcha_api_key", "Anti-Captcha API Key")
o.password = true
o:depends("captcha_enabled", "1")
o = s:taboption("captcha", Value, "captcha_timeout", translate("验证码超时（秒）"))
o.datatype = "range(30,600)"
o.default = 120
o = s:taboption("captcha", Value, "captcha_poll_interval", translate("轮询间隔（秒）"))
o.datatype = "range(1,30)"
o.default = 3

o = s:taboption("mail", ListValue, "mail_provider", translate("发件邮箱类型"))
o:value("163", "163 邮箱")
o:value("126", "126 邮箱")
o:value("qq", "QQ / Foxmail")
o:value("gmail", "Gmail")
o:value("yahoo", "Yahoo Mail")
o:value("outlook", "Outlook / Hotmail")
o:value("custom", translate("自定义 SMTP"))
o.default = "163"
o.rmempty = false
o = s:taboption("mail", Value, "smtp_host", translate("SMTP 服务器"))
o:depends("mail_provider", "custom")
o = s:taboption("mail", Value, "smtp_username", translate("SMTP 登录用户名"))
o:depends("mail_provider", "custom")
o.description = translate("留空时使用发件邮箱作为登录用户名。")
o = s:taboption("mail", Value, "smtp_port", translate("SMTP 端口"))
o.datatype = "port"
o.default = 465
o:depends("mail_provider", "custom")
o = s:taboption("mail", ListValue, "smtp_security", translate("SMTP 加密"))
o:value("ssl", "SSL/TLS")
o:value("starttls", "STARTTLS")
o:value("plain", translate("不加密"))
o.default = "ssl"
o:depends("mail_provider", "custom")
o = s:taboption("mail", Value, "mail_user", translate("发件邮箱"))
o.rmempty = false
o = s:taboption("mail", Value, "mail_pass", translate("SMTP 授权码或应用密码"))
o.password = true
o.rmempty = false
o = s:taboption("mail", DynamicList, "mail_to", translate("收件邮箱"))
o.rmempty = false
o = s:taboption("mail", Value, "subject_prefix", translate("邮件主题"))
o.default = "iKuuu 签到通知"
o.rmempty = false

function m.on_after_commit()
	sys.call("chmod 600 /etc/config/ikuuu-checkin 2>/dev/null")
	sys.call("/etc/init.d/ikuuu-checkin restart >/dev/null 2>&1")
end

return m
