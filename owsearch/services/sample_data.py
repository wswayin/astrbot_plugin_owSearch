from __future__ import annotations

from .analysis import AnalysisResult
from ..models import MatchDetail, MatchSummary, PlayerIdentity


def build_sample_match_detail() -> MatchDetail:
    identity = PlayerIdentity(
        query="Player#12345",
        full_id="Player#12345",
        bnet_id="12345",
        customer_token="sample-customer-token",
        title="联调样例玩家",
        level=4,
        game_time="888.8",
    )
    source_match = {
        "matchId": "sample-match-1",
        "matchRet": 1,
        "gameMode": "SportPreset",
        "beginTs": 1777212060658,
        "teamScore": 3,
        "opponentScore": 1,
        "kill": 21,
        "assist": 8,
        "death": 3,
        "heroDamage": 12800,
        "cure": 0,
        "resistDamage": 1200,
        "roleType": "dps",
    }
    payload = {
        "code": 0,
        "success": True,
        "data": {
            "matchRet": 1,
            "mapGuid": "sample-map",
            "gameTimeSec": 955,
            "startTime": 1777212060,
            "teamScore": 3,
            "opponentScore": 1,
            "teammateList": [
                {
                    "name": "Player#12345",
                    "bnetId": "12345",
                    "roleType": "dps",
                    "kill": 21,
                    "assist": 8,
                    "death": 3,
                    "heroDamage": 12800,
                    "cure": 0,
                    "resistDamage": 1200,
                    "finalHit": 7,
                    "damageTaken": 4300,
                    "healingTaken": 2900,
                    "rankInfo": {"rank_name": "Diamond", "rank_sub_tier": 2},
                },
                {
                    "name": "Tank#1111",
                    "bnetId": "1111",
                    "roleType": "tank",
                    "kill": 12,
                    "assist": 13,
                    "death": 4,
                    "heroDamage": 7600,
                    "cure": 0,
                    "resistDamage": 15400,
                    "rankInfo": {"rank_name": "Platinum", "rank_sub_tier": 1},
                },
                {
                    "name": "Support#2222",
                    "bnetId": "2222",
                    "roleType": "healer",
                    "kill": 4,
                    "assist": 21,
                    "death": 5,
                    "heroDamage": 2200,
                    "cure": 13200,
                    "resistDamage": 0,
                    "rankInfo": {"rank_name": "Diamond", "rank_sub_tier": 4},
                },
            ],
            "enemyList": [
                {
                    "name": "EnemyDps#9999",
                    "bnetId": "9999",
                    "roleType": "dps",
                    "kill": 16,
                    "assist": 3,
                    "death": 8,
                    "heroDamage": 10100,
                    "cure": 0,
                    "resistDamage": 300,
                    "rankInfo": {"rank_name": "Diamond", "rank_sub_tier": 3},
                },
                {
                    "name": "EnemyTank#8888",
                    "bnetId": "8888",
                    "roleType": "tank",
                    "kill": 7,
                    "assist": 10,
                    "death": 7,
                    "heroDamage": 6900,
                    "cure": 0,
                    "resistDamage": 12100,
                    "rankInfo": {"rank_name": "Platinum", "rank_sub_tier": 2},
                },
            ],
        },
    }
    return MatchDetail(
        identity=identity,
        summary=MatchSummary.from_payload(source_match),
        payload=payload,
        source_match=source_match,
        match_kind="normal",
    )


def build_sample_analysis() -> AnalysisResult:
    return AnalysisResult(
        ok=True,
        model="sample-model",
        data={
            "score": "A",
            "verdict": "焦点玩家输出稳定，死亡控制不错，是本局主要推进点。",
            "highlights": ["击杀效率高", "死亡控制干净", "关键输出压住敌方输出位"],
            "problems": ["承伤略高", "治疗资源吃得偏多"],
            "advice": ["继续保持站位纪律", "优势局少贪深追", "多和坦克同步节奏"],
            "meme_line": "man! what can i say, mamba out。",
        },
    )
