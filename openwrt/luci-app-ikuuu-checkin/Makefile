include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-ikuuu-checkin
PKG_VERSION:=1.0.1
PKG_RELEASE:=1
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-ikuuu-checkin
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=iKuuu check-in
  PKGARCH:=all
  DEPENDS:=+luci-base +python3 +python3-pip +python3-requests +python3-lxml +ca-bundle
endef

define Package/luci-app-ikuuu-checkin/description
 LuCI configuration and scheduler for iKuuu check-in.
endef

define Build/Compile
endef

define Package/luci-app-ikuuu-checkin/install
	$(CP) ./files/* $(1)/
endef

define Package/luci-app-ikuuu-checkin/conffiles
/etc/config/ikuuu-checkin
endef

define Package/luci-app-ikuuu-checkin/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
chmod 600 /etc/config/ikuuu-checkin 2>/dev/null || true
mkdir -p /etc/ikuuu-checkin
if ! /usr/bin/python3 -c 'import bs4' >/dev/null 2>&1; then
	/usr/bin/pip3 install --no-cache-dir 'beautifulsoup4>=4.12,<5' || \
		/usr/bin/pip3 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple 'beautifulsoup4>=4.12,<5' || exit 1
fi
rm -f /tmp/luci-indexcache /tmp/luci-modulecache/* 2>/dev/null || true
/etc/init.d/ikuuu-checkin enable 2>/dev/null || true
[ "$$(uci -q get ikuuu-checkin.main.enabled)" = "1" ] && \
	/etc/init.d/ikuuu-checkin restart 2>/dev/null || true
exit 0
endef

define Package/luci-app-ikuuu-checkin/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/ikuuu-checkin stop 2>/dev/null || true
/etc/init.d/ikuuu-checkin disable 2>/dev/null || true
exit 0
endef

$(eval $(call BuildPackage,luci-app-ikuuu-checkin))
