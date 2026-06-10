from __future__ import annotations

# ======================= Core Service ====================== #
API_HOST = "127.0.0.1"
API_PORT = 18080
USE_STREAM_RESPONSE = True
ENABLE_DATABASE_WRITE = True

# ======================= Dashen Upstream ====================== #
# Configure at least one account.
DASHEN_ACCOUNTS = [
    {
        "name": "account-1",
        "role_id": 123456789,
        "token": "replace-with-your-token",
    },
    # {
    #     "name": "account-2",
    #     "role_id": 987654321,
    #     "token": "replace-with-your-token",
    # },
]

DASHEN_DTS = 2026
DASHEN_SERVER = 1
DASHEN_ACCOUNT_MAX_REQUESTS_PER_SECOND = 5
DASHEN_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS = 1.0
DASHEN_CLIENT_TYPE = "60"
DASHEN_ORIGIN = "https://act.ds.163.com"
DASHEN_REFERER = "https://act.ds.163.com/"
DASHEN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 "
    "app/df_client dfVersion/100111"
)
DASHEN_ACCOUNT_FAILURE_COOLDOWN_SECONDS = 60
DASHEN_MAX_CONCURRENT_REQUESTS = 2
# Main v2 Dashen endpoints accept at most account-pool-size * 4 requests
# (active + queued) by default. Extra requests receive HTTP 429.
DASHEN_MAX_ACCEPTED_REQUESTS = max(len(DASHEN_ACCOUNTS) * 4, 1)

# Optional proxy settings.
DASHEN_INTERNATIONAL_PROXY = ""
DASHEN_NETEASE_PROXIES = [
    None,
    # "http://your-netease-proxy:port",
]

# OW esports PandaScore API key.
#如何获取ow赛事的apikey:访问https://app.pandascore.co/dashboard/main，注册并生成api key，每小时1000次免费调用
OW_ESPORTS_API_KEY = ""

# ======================= OW Hero Leaderboard ====================== #
OW_HERO_LEADERBOARD_CN_SEASON = 2

# ======================= Match Analysis ====================== #
# OpenAI-compatible base URL, for example:
# - https://api.openai.com/v1
# - https://api.deepseek.com/v1
# - https://generativelanguage.googleapis.com/v1beta/openai
# You can also provide the full /chat/completions endpoint directly.
ANALYSIS_BASE_URL = ""
ANALYSIS_API_KEY = "replace-with-your-analysis-api-key"
# Optional proxy for OpenAI official and Google OpenAI-compatible endpoints.
ANALYSIS_PROXY = ""

# ANALYSIS_GOOGLE_MODEL = "gemini-3.1-flash-lite-preview"
#ANALYSIS_DEEPSEEK_MODEL = "deepseek-chat"
#除谷歌和deepseek以外的模型使用下面配置
ANALYSIS_OPENAI_MODEL = ""


# Optional external patch-note fetch proxy.
PATCH_NOTES_USE_INTERNATIONAL_PROXY = False
PATCH_NOTES_INTERNATIONAL_PROXY = ""

# Only put AI persona/tone here.
# Task instructions and the JSON schema remain in service.py.
ANALYSIS_PERSONA_PROMPT = """
【核心原则】
请保持绝对客观中立，拒绝阿谀奉承！不要因为查询指令的是焦点玩家就一味夸奖，如果焦点玩家表现平庸或拉垮请直接批评。所有毒舌点评必须围绕本局数据、英雄选择、站位、团战处理和资源交换，不攻击现实身份，不涉及歧视性内容，不虚构不存在的对局细节。

【人格设定】
你的说话人设是一位非常毒舌的守望先锋评论员：语句犀利、节奏快、结论明确，允许适当使用守望先锋梗和中文互联网梗。可以阴阳怪气，但必须有数据依据；可以狠，但不要脏；像赛后复盘台上那个一眼看穿问题、嘴上完全不留情的评论员。
""".strip()
