module("luci.controller.ikuuu_checkin", package.seeall)

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
end
