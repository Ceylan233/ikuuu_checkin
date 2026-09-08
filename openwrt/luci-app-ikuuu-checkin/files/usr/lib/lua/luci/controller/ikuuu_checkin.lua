module("luci.controller.ikuuu_checkin", package.seeall)

local http = require "luci.http"
local sys = require "luci.sys"

function index()
	if not nixio.fs.access("/etc/config/ikuuu-checkin") then
		return
	end
	local page = entry(
		{"admin", "services", "ikuuu-checkin"},
		cbi("ikuuu-checkin"),
		_("iKuuu 签到"),
		67
	)
	page.dependent = true
	entry({"admin", "services", "ikuuu-checkin", "log"}, call("log"), nil).leaf = true
end

function log()
	http.prepare_content("text/plain; charset=utf-8")
	http.write(sys.exec("tail -n 200 /tmp/ikuuu-checkin.log 2>/dev/null"))
end
