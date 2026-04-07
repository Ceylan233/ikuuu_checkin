"""
任务名称
name: iKuuu签到
定时规则
cron: 0 0 8 * * ?
"""
import smtplib
from email.mime.text import MIMEText
import requests
import re
import json
import os
import datetime
import urllib.parse
from urllib.parse import urlparse
import sys
import time
import base64
from bs4 import BeautifulSoup

LOGIN_ACCOUNTS = [
]

# 添加青龙脚本根目录到Python路径
QL_SCRIPTS_DIR = '/ql/scripts'  # 青龙脚本默认目录
sys.path.append(QL_SCRIPTS_DIR)

# 添加notify可能存在的其他路径
POSSIBLE_PATHS = [
    '/ql',  # 青龙根目录
    '/ql/data/scripts',  # 新版青龙数据目录
    '/ql/scripts/notify',  # 自定义通知目录
    os.path.dirname(__file__)  # 当前脚本目录
]

for path in POSSIBLE_PATHS:
    if os.path.exists(os.path.join(path, 'notify.py')):
        sys.path.append(path)
        break

try:
    from notify import send
except ImportError:
    # print("⚠️ 无法加载通知模块，请检查路径配置")
    send = lambda title, content: None  # 创建空函数防止报错

# 初始域名
ikun_host = "ikuuu.fyi"  # 自动更新于2025-07-25 09:56:36
backup_hosts = ["ikuuu.one", "ikuuu.nl", "ikuuu.de"]  # 备用域名列表

# 统一的User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "user-agent": USER_AGENT,
}

ORIGIN_BODY_RE = re.compile(r'originBody\s*=\s*"([^"]+)"', re.I)
CAPTCHA_ID_RE = re.compile(r"captchaId\s*[:=]\s*['\"]([a-f0-9]{16,})['\"]", re.I)
CAPTCHA_ID_ALT_RE = re.compile(r"captcha_id\s*[:=]\s*['\"]([a-f0-9]{16,})['\"]", re.I)
GT_RE = re.compile(r"\bgt\s*[:=]\s*['\"]([a-f0-9]{16,})['\"]", re.I)
RISK_TYPE_RE = re.compile(r"riskType\s*[:=]\s*['\"]([^'\"]+)['\"]", re.I)
HIDDEN_INPUT_RE = re.compile(r"<input[^>]+type=[\"']hidden[\"'][^>]*>", re.I)
NAME_RE = re.compile(r"name=[\"']([^\"']+)[\"']", re.I)
VALUE_RE = re.compile(r"value=[\"']([^\"']*)[\"']", re.I)
META_CSRF_RE = re.compile(r"<meta[^>]+name=[\"']csrf-token[\"'][^>]*content=[\"']([^\"']+)[\"']", re.I)
CAPTCHA_RE = re.compile(r"captcha|验证码|recaptcha|hcaptcha|geetest|initgeetest|captcha_result", re.I)


def _env_bool(*names, default=False):
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return str(value).strip().lower() in ('1', 'true', 'yes', 'on')
    return default


def _env_int(names, default):
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != '':
            try:
                return int(str(value).strip())
            except Exception:
                return default
    return default


def get_login_opts():
    enabled = _env_bool('IKUUU_CAPTCHA_SOLVER_ENABLED', 'CAPTCHA_SOLVER_ENABLED', default=True)
    provider = os.getenv('IKUUU_CAPTCHA_PROVIDER') or os.getenv('CAPTCHA_PROVIDER') or 'capsolver'
    fallback_provider = os.getenv('IKUUU_CAPTCHA_FALLBACK_PROVIDER') or os.getenv('CAPTCHA_FALLBACK_PROVIDER') or 'anticaptcha'
    timeout_seconds = _env_int(['IKUUU_CAPTCHA_TIMEOUT_SECONDS', 'CAPTCHA_TIMEOUT_SECONDS'], 120)
    poll_interval_seconds = _env_int(['IKUUU_CAPTCHA_POLL_INTERVAL_SECONDS', 'CAPTCHA_POLL_INTERVAL_SECONDS'], 3)
    remember_me = os.getenv('IKUUU_REMEMBER_ME')
    if remember_me is None:
        remember_me = 'off'
    two_fa_code = os.getenv('IKUUU_2FA_CODE') or os.getenv('TWO_FA_CODE') or ''
    ignore_captcha = _env_bool('IKUUU_IGNORE_CAPTCHA', 'IGNORE_CAPTCHA', default=False)

    return {
        'ignore_captcha': ignore_captcha,
        'two_fa_code': two_fa_code,
        'remember_me': remember_me,
        'captcha_result': {},
        'captcha_solver': {
            'enabled': enabled,
            'provider': provider,
            'fallback_provider': fallback_provider,
            'timeout_seconds': timeout_seconds,
            'poll_interval_seconds': poll_interval_seconds,
        }
    }

def extract_origin_body(html):
    if not html:
        return None
    match = ORIGIN_BODY_RE.search(html)
    if not match:
        return None
    try:
        return base64.b64decode(match.group(1)).decode('utf-8', errors='ignore')
    except Exception:
        return None


def extract_hidden_inputs(html):
    tokens = {}
    if not html:
        return tokens
    for match in HIDDEN_INPUT_RE.findall(html):
        name_match = NAME_RE.search(match)
        value_match = VALUE_RE.search(match)
        if not name_match:
            continue
        tokens[name_match.group(1)] = value_match.group(1) if value_match else ''
    return tokens


def extract_csrf_token(html):
    if not html:
        return None
    meta = META_CSRF_RE.search(html)
    return meta.group(1) if meta else None


def extract_geetest_params(html):
    if not html:
        return None, {}
    captcha_id = None
    for regex in (CAPTCHA_ID_RE, CAPTCHA_ID_ALT_RE, GT_RE):
        match = regex.search(html)
        if match:
            captcha_id = match.group(1)
            break
    init_params = {}
    risk = RISK_TYPE_RE.search(html)
    if risk:
        init_params['riskType'] = risk.group(1)
    return captcha_id, init_params


def get_captcha_api_key(provider, solver_cfg=None):
    if provider == 'capsolver':
        return os.getenv('IKUUU_CAPSOLVER_API_KEY') or os.getenv('CAPSOLVER_API_KEY')
    if provider == 'anticaptcha':
        return os.getenv('IKUUU_ANTICAPTCHA_API_KEY') or os.getenv('ANTICAPTCHA_API_KEY')
    return None


def solve_captcha_capsolver(base_url, captcha_id, solver_cfg, stats=None):
    api_key = get_captcha_api_key('capsolver', solver_cfg)
    if not api_key:
        return None, '缺少 CAPSOLVER_API_KEY'
    create_url = 'https://api.capsolver.com/createTask'
    result_url = 'https://api.capsolver.com/getTaskResult'
    payload = {
        'clientKey': api_key,
        'task': {
            'type': 'GeeTestTaskProxyLess',
            'websiteURL': base_url + '/auth/login',
            'captchaId': captcha_id,
        }
    }
    try:
        resp = requests.post(create_url, json=payload, timeout=30)
        data = resp.json()
    except Exception as e:
        return None, f'CapSolver createTask异常: {repr(e)}'
    if data.get('errorId', 0) != 0:
        return None, f"CapSolver createTask失败: {data.get('errorDescription', '')}"
    task_id = data.get('taskId')
    if not task_id:
        return None, 'CapSolver 未返回 taskId'

    timeout_seconds = int(solver_cfg.get('timeout_seconds', 120))
    poll_interval_seconds = int(solver_cfg.get('poll_interval_seconds', 3))
    start = time.time()
    while time.time() - start < timeout_seconds:
        time.sleep(max(poll_interval_seconds, 1))
        try:
            resp = requests.post(result_url, json={'clientKey': api_key, 'taskId': task_id}, timeout=30)
            data = resp.json()
        except Exception as e:
            return None, f'CapSolver getTaskResult异常: {repr(e)}'
        if data.get('errorId', 0) != 0:
            return None, f"CapSolver getTaskResult失败: {data.get('errorDescription', '')}"
        if data.get('status') == 'ready':
            return data.get('solution'), None
    return None, 'CapSolver 解码超时'


def solve_captcha_anticaptcha(base_url, captcha_id, init_params, solver_cfg):
    api_key = get_captcha_api_key('anticaptcha', solver_cfg)
    if not api_key:
        return None, '缺少 ANTICAPTCHA_API_KEY'
    create_url = 'https://api.anti-captcha.com/createTask'
    result_url = 'https://api.anti-captcha.com/getTaskResult'
    task = {
        'type': 'GeeTestTaskProxyless',
        'websiteURL': base_url + '/auth/login',
        'gt': captcha_id,
        'version': 4,
    }
    if init_params:
        task['initParameters'] = init_params
    try:
        resp = requests.post(create_url, json={'clientKey': api_key, 'task': task}, timeout=30)
        data = resp.json()
    except Exception as e:
        return None, f'Anti-Captcha createTask异常: {repr(e)}'
    if data.get('errorId', 0) != 0:
        return None, f"Anti-Captcha createTask失败: {data.get('errorDescription', '')}"
    task_id = data.get('taskId')
    if not task_id:
        return None, 'Anti-Captcha 未返回 taskId'

    timeout_seconds = int(solver_cfg.get('timeout_seconds', 120))
    poll_interval_seconds = int(solver_cfg.get('poll_interval_seconds', 3))
    start = time.time()
    while time.time() - start < timeout_seconds:
        time.sleep(max(poll_interval_seconds, 1))
        try:
            resp = requests.post(result_url, json={'clientKey': api_key, 'taskId': task_id}, timeout=30)
            data = resp.json()
        except Exception as e:
            return None, f'Anti-Captcha getTaskResult异常: {repr(e)}'
        if data.get('errorId', 0) != 0:
            return None, f"Anti-Captcha getTaskResult失败: {data.get('errorDescription', '')}"
        if data.get('status') == 'ready':
            return data.get('solution'), None
    return None, 'Anti-Captcha 解码超时'


def solve_geetest_v4(base_url, captcha_id, init_params, solver_cfg, stats=None):
    providers = []
    primary = solver_cfg.get('provider', 'capsolver')
    fallback = solver_cfg.get('fallback_provider')
    if primary:
        providers.append(primary)
    if fallback and fallback not in providers:
        providers.append(fallback)

    attempted = 0
    last_err = None
    for provider in providers:
        if provider in ('capsolver', 'anticaptcha') and not get_captcha_api_key(provider, solver_cfg):
            continue
        attempted += 1
        if provider == 'capsolver':
            solution, err = solve_captcha_capsolver(base_url, captcha_id, solver_cfg, stats=stats)
        elif provider == 'anticaptcha':
            solution, err = solve_captcha_anticaptcha(base_url, captcha_id, init_params, solver_cfg)
        else:
            solution, err = None, f'未知captcha provider: {provider}'
        if solution:
            return solution, None
        last_err = err or ''

    if attempted == 0:
        return None, '未配置验证码服务API Key'
    return None, last_err or 'captcha solve failed'

def get_captcha_info():
    enabled = os.getenv("IKUUU_CAPTCHA_SOLVER_ENABLED", "0") == "1"
    provider = os.getenv("IKUUU_CAPTCHA_PROVIDER", "capsolver")

    if not enabled:
        return None  # 不显示

    if provider == "capsolver":
        api_key = os.getenv("IKUUU_CAPSOLVER_API_KEY") or os.getenv("CAPSOLVER_API_KEY")
        if not api_key:
            return "已使用 capsolver | 未配置API Key"

        try:
            resp = requests.post(
                "https://api.capsolver.com/getBalance",
                json={"clientKey": api_key},
                timeout=15
            )
            data = resp.json()

            if data.get("errorId", 0) != 0:
                return "已使用 capsolver | 余额获取失败"

            balance = data.get("balance")
            if balance is None:
                return "已使用 capsolver | 余额未知"

            return f"已使用 capsolver | 剩余余额 ${balance:.4f}"
        except:
            return "已使用 capsolver | 余额获取异常"

    elif provider == "anticaptcha":
        return "已使用 anticaptcha"  # 这个接口你暂时没写余额查询

    return f"已使用 {provider}"

def get_captcha_provider_only():
    enabled = os.getenv("IKUUU_CAPTCHA_SOLVER_ENABLED", "0") == "1"
    if not enabled:
        return None

    provider = os.getenv("IKUUU_CAPTCHA_PROVIDER", "capsolver")
    return f"已使用 {provider}"

def detect_captcha(html):
    return bool(html and CAPTCHA_RE.search(html))


def is_already_checked_in(msg):
    if not msg:
        return False
    low = str(msg).lower()
    patterns = ['已签到', '已经签到', '已簽到', '已签', '已簽', '已打卡', 'already']
    return any(p in str(msg) for p in patterns) or 'already' in low


def build_login_body(base_url, email, password, login_opts, session):
    body = {'email': email, 'password': password, 'passwd': password}
    try:
        host = urlparse(base_url).netloc
        if host:
            body['host'] = host
    except Exception:
        pass
    body['pageLoadedAt'] = int(time.time() * 1000)

    two_fa_code = login_opts.get('two_fa_code')
    if two_fa_code:
        body['code'] = two_fa_code

    captcha_result = login_opts.get('captcha_result')
    if isinstance(captcha_result, dict) and captcha_result:
        body['captcha_result'] = json.dumps(captcha_result, separators=(',', ':'))
        for key, value in captcha_result.items():
            body[f'captcha_result[{key}]'] = value

    remember_me = login_opts.get('remember_me')
    if remember_me is not None:
        body['remember_me'] = remember_me

    login_page_html = ''
    login_page_url = None
    try:
        page_resp = session.get(base_url + '/auth/login', headers=HEADERS, timeout=12, allow_redirects=True)
        login_page_html = page_resp.text or ''
        login_page_url = page_resp.url
    except Exception:
        pass

    analysis_html = extract_origin_body(login_page_html) or login_page_html
    post_base_url = base_url
    if login_page_url:
        login_page_domain = normalize_url_as_base(login_page_url)
        if login_page_domain and login_page_domain != base_url:
            post_base_url = login_page_domain

    if analysis_html:
        hidden = extract_hidden_inputs(analysis_html)
        if hidden:
            body.update(hidden)
        csrf = extract_csrf_token(analysis_html)
        if csrf and '_token' not in body:
            body['_token'] = csrf
        if detect_captcha(analysis_html) and not (isinstance(captcha_result, dict) and captcha_result):
            if login_opts.get('ignore_captcha'):
                return None, post_base_url, '登录页面包含验证码(GeeTest)，已配置忽略但服务端通常会拒绝'
            solver_cfg = login_opts.get('captcha_solver', {}) or {}
            if not solver_cfg.get('enabled'):
                return None, post_base_url, '登录页面包含验证码(GeeTest)，未启用解码服务'
            captcha_id, init_params = extract_geetest_params(analysis_html)
            if not captcha_id:
                return None, post_base_url, '检测到验证码，但未能解析 captchaId'
            solution, err = solve_geetest_v4(post_base_url, captcha_id, init_params, solver_cfg)
            if not solution:
                return None, post_base_url, '验证码解码失败: ' + (err or '')
            body['captcha_result'] = json.dumps(solution, separators=(',', ':'))
            for key, value in solution.items():
                body[f'captcha_result[{key}]'] = value

    return body, post_base_url, None


def normalize_url_as_base(value):
    if not value:
        return None
    try:
        parsed = urlparse(value.strip())
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc.lower().rstrip(".")}'
    except Exception:
        return None
    return None



def get_accounts():
    """
    获取账户列表，优先使用硬编码账户，其次使用环境变量
    """
    accounts = []

    # 方法1: 检查硬编码账户
    if LOGIN_ACCOUNTS and len(LOGIN_ACCOUNTS) > 0:
        accounts = LOGIN_ACCOUNTS
    else:
        # 方法2: 检查环境变量
        account_str = os.getenv('ACCOUNTS')
        if account_str and account_str.strip():
            print("🔧 使用环境变量账户")
            for line in account_str.strip().splitlines():
                line = line.strip()
                if line and ':' in line:
                    email, pwd = line.split(':', 1)
                    accounts.append((email.strip(), pwd.strip()))
                elif line:
                    print(f"⚠️ 忽略无效账户行: {line}")
        else:
            print("❌ 未找到任何账户配置（配置LOGIN_ACCOUNTS和环境变量均为空）")
            return None

    print(f"📋 找到 {len(accounts)} 个账户")
    return accounts


def extract_domains_from_content(content):
    """
    从网页内容中提取可用域名
    """
    domains = []

    # 多种域名提取模式
    patterns = [
        # 匹配 <h2>新域名: xxx.com</h2> 或类似格式
        r'<h[1-6][^>]*>.*?(?:域名|domain|新域名|最新域名)[：:]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        # 匹配JavaScript中的跳转域名
        r'(?:location\.href|window\.location)\s*=\s*["\']https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        # 匹配登录链接
        r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/auth/login',
        # 匹配任何完整的链接
        r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        # 匹配文本中的域名描述
        r'(?:域名|domain|网址|地址)[：:\s]*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        # 匹配ikuuu相关域名
        r'(ikuuu\.[a-zA-Z0-9.-]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            domain = match.strip().lower()
            # 过滤掉明显不是域名的内容
            if (domain and
                    '.' in domain and
                    not domain.startswith('.') and
                    not domain.endswith('.') and
                    len(domain) > 3 and
                    len(domain) < 50 and
                    not any(char in domain for char in [' ', '\n', '\t', '<', '>', '"', "'"])):
                domains.append(domain)

    # 去重并返回
    return list(set(domains))


def get_available_domains_from_old_domain(old_domain):
    """
    从旧域名页面获取新的可用域名
    """
    available_domains = []

    try:
        print(f"🔍 从域名 {old_domain} 获取新域名信息...")
        response = requests.get(f"https://{old_domain}/",
                                headers={"User-Agent": USER_AGENT},
                                timeout=15,
                                allow_redirects=True)

        if response.status_code == 200:
            content = response.text

            # 检查是否包含域名变更信息
            change_indicators = [
                '官网域名已更改', 'Domain deprecated', '域名已更新',
                '新域名', '最新域名', '域名变更', '网站已迁移'
            ]

            has_change_info = any(indicator in content for indicator in change_indicators)

            if has_change_info:
                print("✅ 检测到域名变更通知")
                domains = extract_domains_from_content(content)
                available_domains.extend(domains)
            else:
                print("ℹ️ 未检测到域名变更通知，但尝试解析可能的域名")
                domains = extract_domains_from_content(content)
                # 只保留ikuuu相关域名
                ikuuu_domains = [d for d in domains if 'ikuuu' in d]
                available_domains.extend(ikuuu_domains)

        else:
            print(f"⚠️ 域名 {old_domain} 返回状态码: {response.status_code}")

    except requests.exceptions.Timeout:
        print(f"⏰ 域名 {old_domain} 请求超时")
    except requests.exceptions.ConnectionError:
        print(f"🔌 域名 {old_domain} 连接失败")
    except Exception as e:
        print(f"❌ 检查域名 {old_domain} 时出错: {e}")

    return available_domains


def get_latest_ikun_host():
    """
    获取最新可用域名
    """
    # 首先检查当前域名
    test_url = f"https://{ikun_host}/"
    try:
        response = requests.get(test_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if response.status_code == 200:
            # 检查是否有域名变更通知
            change_indicators = [
                '官网域名已更改', 'Domain deprecated', '域名已更新',
                '新域名', '最新域名', '域名变更'
            ]

            if any(indicator in response.text for indicator in change_indicators):
                print("🔄 检测到域名变更通知，正在提取新域名...")
                domains = extract_domains_from_content(response.text)

                # 优先返回ikuuu相关域名
                for domain in domains:
                    if 'ikuuu' in domain and domain != ikun_host:
                        print(f"🎯 找到新域名: {domain}")
                        return domain

                # 如果没有ikuuu域名，返回第一个有效域名
                if domains:
                    print(f"🎯 找到域名: {domains[0]}")
                    return domains[0]

                print("⚠️ 检测到域名变更但无法提取新域名")
                return None
            else:
                print("✅ 当前域名正常")
                return None
    except Exception as e:
        print(f"🔍 当前域名检测异常: {e}")

    return None


def update_self_host(new_host):
    """
    更新脚本中的域名
    """
    script_path = os.path.abspath(__file__)
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith("ikun_host = "):
                lines[
                    i] = f'ikun_host = "{new_host}"  # 自动更新于{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                updated = True
                break

        if updated:
            with open(script_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"✅ 脚本已更新至域名: {new_host}")
            return True
        else:
            print("⚠️ 未找到域名配置行，无法自动更新")
            return False
    except Exception as e:
        print(f"⚠️ 域名更新失败: {e}")
        return False


def test_host_reachable(host):
    """
    测试域名是否可达
    """
    try:
        print(f"🔗 测试域名: {host}")
        response = requests.get(f"https://{host}/",
                                headers={"User-Agent": USER_AGENT},
                                timeout=10)
        if response.status_code == 200:
            print(f"✅ 域名 {host} 可用")
            return True
        else:
            print(f"⚠️ 域名 {host} 返回状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 域名 {host} 不可用: {e}")
        return False


def find_working_domain():
    """
    寻找可用的域名
    """
    global ikun_host

    # 1. 首先检查当前域名
    print(f"🏠 当前域名: {ikun_host}")
    if test_host_reachable(ikun_host):
        return ikun_host

    # 2. 从当前域名和备用域名中获取新域名信息
    all_domains_to_check = [ikun_host] + backup_hosts
    discovered_domains = []

    for domain in all_domains_to_check:
        new_domains = get_available_domains_from_old_domain(domain)
        discovered_domains.extend(new_domains)

    # 去重
    discovered_domains = list(set(discovered_domains))
    print(f"🔍 发现的域名: {discovered_domains}")

    # 3. 测试发现的域名
    for domain in discovered_domains:
        if domain != ikun_host and test_host_reachable(domain):
            print(f"🎉 找到可用域名: {domain}")
            ikun_host = domain
            # 尝试更新脚本
            update_self_host(domain)
            return domain

    # 4. 测试备用域名
    print("🔄 测试备用域名列表...")
    for host in backup_hosts:
        if host != ikun_host and test_host_reachable(host):
            print(f"🎉 备用域名可用: {host}")
            ikun_host = host
            return host

    # 5. 都不可用
    print("❌ 所有域名均不可用")
    return None


def get_remaining_flow(cookies):
    """获取用户剩余流量信息"""
    user_url = f'https://{ikun_host}/user'
    try:
        # 获取用户页面
        user_page = requests.get(user_url, cookies=cookies, headers={"User-Agent": USER_AGENT}, timeout=20)
        if user_page.status_code != 200:
            return "获取流量失败", "状态码: " + str(user_page.status_code)

        # 提取并解码Base64内容
        match = re.search(r'var originBody = "([^"]+)"', user_page.text)
        if not match:
            return "未找到Base64内容", ""

        base64_content = match.group(1)
        decoded_content = base64.b64decode(base64_content).decode('utf-8')

        # 使用BeautifulSoup解析解码后的HTML
        soup = BeautifulSoup(decoded_content, 'html.parser')

        # 查找包含剩余流量的卡片
        flow_cards = soup.find_all('div', class_='card card-statistic-2')
        for card in flow_cards:
            h4_tag = card.find('h4')
            if h4_tag and '剩余流量' in h4_tag.text:
                # 查找流量数值
                counter_span = card.find('span', class_='counter')
                if counter_span:
                    flow_value = counter_span.text.strip()

                    # 查找流量单位
                    unit_text = ""
                    next_sibling = counter_span.next_sibling
                    if next_sibling:
                        unit_text = next_sibling.strip()

                    return flow_value, unit_text

        return "未找到", "流量信息"

    except Exception as e:
        return "流量获取异常", str(e)


def ikuuu_signin(email, password):
    base_url = f'https://{ikun_host}'
    login_opts = get_login_opts()
    session = requests.session()
    try:
        body, post_base_url, build_err = build_login_body(base_url, email, password, login_opts, session)
        if build_err:
            return False, f"登录失败：{build_err}", "登录失败", "无法获取"

        login_res = session.post(
            post_base_url + '/auth/login',
            data=body,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True,
        )
        if login_res.status_code == 405 or '405 Not Allowed' in (login_res.text or ''):
            return False, '登录失败：登录被拒绝(405)', '登录失败', '无法获取'
        if login_res.status_code != 200:
            return False, f"登录失败（状态码{login_res.status_code}）", "登录失败", "无法获取"

        try:
            login_data = login_res.json()
        except json.JSONDecodeError:
            return False, '响应解析失败', '未知', '未知'

        if login_data.get('ret') != 1:
            return False, f"登录失败：{login_data.get('msg', '未知错误')}", '登录失败', '无法获取'

        flow_value, flow_unit = get_remaining_flow(session.cookies)

        checkin_res = session.post(
            post_base_url + '/user/checkin',
            headers=HEADERS,
            timeout=20,
            allow_redirects=True,
        )
        if checkin_res.status_code != 200:
            return False, f"签到失败（状态码{checkin_res.status_code}）", flow_value, flow_unit

        try:
            checkin_data = checkin_res.json()
        except json.JSONDecodeError:
            return False, '响应解析失败', flow_value, flow_unit

        if checkin_data.get('ret') == 1:
            return True, f"成功 | {checkin_data.get('msg', '')}", flow_value, flow_unit

        checkin_msg = str(checkin_data.get('msg', '未知错误'))
        if is_already_checked_in(checkin_msg):
            return True, f"成功 | {checkin_msg}", flow_value, flow_unit
        return False, f"签到失败：{checkin_msg}", flow_value, flow_unit
    except requests.exceptions.Timeout:
        return False, '请求超时', '未知', '未知'
    except Exception as e:
        return False, f"请求异常：{str(e)}", '未知', '未知'


def send_qinglong_notification(results, current_domain):
    """
    使用青龙面板内置通知系统发送通知
    需要青龙面板已配置通知渠道（如钉钉、企业微信等）
    """
    title = "iKuuu签到通知"

    # 构建消息内容
    success_count = sum(1 for res in results if res['success'])
    failure_count = len(results) - success_count

    message = [
        f"🔔 签到完成 | 成功：{success_count} 失败：{failure_count}",
        f"🌐 当前域名：{current_domain}",
        "================================"
    ]

    for index, res in enumerate(results, 1):
        status = "✅ 成功" if res['success'] else "❌ 失败"
        message.append(f"{index}. {res['email']}")
        message.append(f"  状态：{status}")
        message.append(f"  详情：{res['message']}")
        message.append(f"  剩余流量：{res['flow_value']} {res['flow_unit']}")
        message.append("--------------------------------")

    # 添加统计信息
    message.append("\n🕒 执行时间：" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    try:
        # 发送通知（青龙自动处理多通知渠道）
        send(title, "\n".join(message))
        print("✅ 通知已发送")
    except Exception as e:
        print(f"⚠️ 通知发送失败，请检查通知配置: {str(e)}")


def send_163mail_notification(results, current_domain, captcha_info=None):
    """
    使用 163 SMTP 发送邮件通知
    """
    title = "iKuuu 签到通知"

    success_count = sum(1 for res in results if res["success"])
    failure_count = len(results) - success_count

    message = [
        f"🔔 签到完成 | 成功：{success_count} 失败：{failure_count}",
        f"🌐 当前域名：{current_domain}",
    ]

    # ✅ 在这里加（关键位置）
    if captcha_info:
        message.append(f"🔐 {captcha_info}")

    message.append("=" * 50)

    for index, res in enumerate(results, 1):
        status = "✅ 成功" if res["success"] else "❌ 失败"
        message.append(f"{index}. {res['email']}")
        message.append(f"   状态：{status}")
        message.append(f"   详情：{res['message']}")
        message.append(f"   剩余流量：{res['flow_value']} {res['flow_unit']}")
        message.append("-" * 50)

    message.append(
        "🕒 执行时间：" +
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    try:
        send_mail_163(title, "\n".join(message))
        print("✅ 邮件通知已发送")
    except Exception as e:
        print(f"⚠️ 邮件发送失败: {e}")


def send_mail_163(subject, content):
    mail_user = os.getenv("MAIL_USER")
    mail_pass = os.getenv("MAIL_PASS")
    mail_to = os.getenv("MAIL_TO")

    if not all([mail_user, mail_pass, mail_to]):
        raise RuntimeError("缺少邮件相关 Secrets")

    receivers = [x.strip() for x in mail_to.split(",") if x.strip()]

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_user
    msg["To"] = ", ".join(receivers)

    server = smtplib.SMTP_SSL("smtp.163.com", 465)
    server.login(mail_user, mail_pass)
    server.send_message(msg, from_addr=mail_user, to_addrs=receivers)
    server.quit()


def send_outlookmail_notification(results, current_domain):
    """
    使用 Outlook SMTP 发送邮件通知
    适用于 GitHub Actions
    """
    title = "iKuuu 签到通知"

    success_count = sum(1 for res in results if res['success'])
    failure_count = len(results) - success_count

    message = [
        f"🔔 签到完成 | 成功：{success_count} 失败：{failure_count}",
        f"🌐 当前域名：{current_domain}",
        "================================"
    ]

    for index, res in enumerate(results, 1):
        status = "✅ 成功" if res['success'] else "❌ 失败"
        message.append(f"{index}. {res['email']}")
        message.append(f"  状态：{status}")
        message.append(f"  详情：{res['message']}")
        message.append(f"  剩余流量：{res['flow_value']} {res['flow_unit']}")
        message.append("--------------------------------")

    message.append(
        "\n🕒 执行时间：" +
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    try:
        send_outlook_mail(title, "\n".join(message))
        print("✅ 邮件通知已发送")
    except Exception as e:
        print(f"⚠️ 邮件发送失败: {str(e)}")


def send_outlook_mail(subject, content):
    print("MAIL_USER exists:", bool(os.getenv("MAIL_USER")))
    print("MAIL_PASS exists:", bool(os.getenv("MAIL_PASS")))
    print("MAIL_TO exists:", bool(os.getenv("MAIL_TO")))

    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASS = os.getenv("MAIL_PASS")
    MAIL_TO = os.getenv("MAIL_TO")

    if not MAIL_USER or not MAIL_PASS or not MAIL_TO:
        raise RuntimeError("MAIL_USER / MAIL_PASS / MAIL_TO 未完整配置")

    receivers = [x.strip() for x in MAIL_TO.split(",") if x.strip()]

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = MAIL_USER
    msg["To"] = ", ".join(receivers)

    server = smtplib.SMTP("smtp.office365.com", 587)
    server.starttls()
    server.login(MAIL_USER, MAIL_PASS)
    server.send_message(msg, from_addr=MAIL_USER, to_addrs=receivers)
    server.quit()


if __name__ == "__main__":
    print("🚀 iKuuu签到脚本启动")
    print("=" * 50)

    # ==================== 域名检查和更新 ====================
    # 首先检查是否有域名更新通知
    latest_host = get_latest_ikun_host()
    if latest_host and latest_host != ikun_host:
        print(f"🔄 检测到新域名: {latest_host}")
        if update_self_host(latest_host):
            ikun_host = latest_host

    # 寻找可用域名
    working_domain = find_working_domain()
    if not working_domain:
        print("💥 无法找到可用域名，脚本退出")
        exit(1)

    print(f"🎯 使用域名: {working_domain}")
    print("=" * 50)

    # ==================== 账户处理 ====================
    accounts = get_accounts()
    provider_info = get_captcha_provider_only()
    if provider_info:
        print(f"🔐 {provider_info}")

    if not accounts:
        print("❌ 未找到有效账户")
        exit(1)

    # ==================== 执行签到 ====================
    results = []
    for index, (email, pwd) in enumerate(accounts, 1):
        print(f"\n👤 [{index}/{len(accounts)}] 处理账户: {email}")
        success, msg, flow_value, flow_unit = ikuuu_signin(email, pwd)
        results.append({
            'email': email,
            'success': success,
            'message': msg,
            'flow_value': flow_value,
            'flow_unit': flow_unit
        })

        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} 结果: {msg}")
        print(f"  📊 剩余流量: {flow_value} {flow_unit}")

        # 账户间延迟防止请求过快
        if index < len(accounts):  # 最后一个账户不需要延迟
            time.sleep(2)
    captcha_info = get_captcha_info()
    # ==================== 结果通知 ====================
    print("\n📢 正在发送通知...")
    # send_qinglong_notification(results, working_domain)
    # send_mail_notification(results, working_domain)
    send_163mail_notification(results, working_domain, captcha_info)
    # ==================== 本地结果输出 ====================
    print("\n📊 签到结果汇总:")
    print("=" * 50)
    success_count = sum(1 for res in results if res['success'])
    print(f"🎯 总账户数: {len(results)}")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {len(results) - success_count}")
    print(f"🌐 使用域名: {working_domain}")
    if captcha_info:
        print(f"🔐 {captcha_info}")
    print("=" * 50)

    for res in results:
        status_icon = "✅" if res['success'] else "❌"
        print(f"{status_icon} {res['email']}")
        print(f"   详情: {res['message']}")
        print(f"   流量: {res['flow_value']} {res['flow_unit']}")

    print("=" * 50)
    print("🏁 脚本执行完成")
