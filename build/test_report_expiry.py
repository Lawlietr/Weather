"""W-C0033-002 特報／W-C0034-001 警報的「有效時間」判定迴歸（2026-11-14 定案的伴生回歸）。

跑法：python3 build/test_report_expiry.py     （退出碼 0＝全過、1＝有失敗）
不連 CWA、不寫檔：只把 `cwa.datetime` 暫時換成固定時鐘，餵合成資料驗
`current_risk_level()` 與 `render_alert_card()`。案例 1 是 2026-11-11 16:16 那筆
把首頁 🟡 拖了 2 天 11 小時的實際記錄形狀；案例 5 守 2026-10-25 的解除判定修正不迴歸。
設計脈絡 → design/site.md「特報/警報的有效時間判定」。
"""
import os
import sys
import datetime as dt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import cwa  # noqa: E402

TZ = cwa.TZ_TW


def D(s):
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


# 2026-11-11 16:16 那筆（實際把首頁推成 🟡 2 天 11 小時的記錄形狀）
R_1111 = {"name": "陸上強風特報", "issue": "2026-11-11 16:16:00",
          "valid": "2026-11-11 16:16:00 ~ 2026-11-11 23:00:00",
          "valid_start": "2026-11-11 16:16:00", "valid_end": "2026-11-11 23:00:00",
          "phenomena": ["陸上強風"], "areas": ["桃園市", "澎湖縣"],
          "content": "一、概述：……\n二、注意(警戒)事項\n黃色燈號：注意！"}

# 2026-11-14 10:23 實際在 feed 裡的那筆（有效起點在未來）
R_LIVE = {"name": "陸上強風特報", "issue": "2026-11-14 10:23:00",
          "valid": "2026-11-14 20:00:00 ~ 2026-11-15 23:00:00",
          "valid_start": "2026-11-14 20:00:00", "valid_end": "2026-11-15 23:00:00",
          "phenomena": ["陸上強風"], "areas": ["桃園市"], "content": "黃色燈號：注意！"}

# CWA 明發解除報的形状（名稱只有「大雨特報」、解除寫在內文、phenomena 空）
R_LIFTED = {"name": "大雨特報", "issue": "2026-10-25 03:25:00",
            "valid": "2026-10-25 03:25:00 ~ 2026-10-25 11:00:00",
            "valid_start": "2026-10-25 03:25:00", "valid_end": "2026-10-25 11:00:00",
            "phenomena": [], "areas": [],
            "content": "由於降雨趨於緩和……故解除大雨特報。"}

# 10/25 那版修正要守住的案例：生效特報內文順帶提到「解除大雨特報」
R_MENTION = {"name": "豪雨特報", "issue": "2026-10-25 03:30:00",
             "valid": "2026-10-25 03:30:00 ~ 2026-10-25 17:00:00",
             "valid_start": "2026-10-25 03:30:00", "valid_end": "2026-10-25 17:00:00",
             "phenomena": ["豪雨"], "areas": ["南投縣"],
             "content": "解除大雨特報，改發豪雨特報。"}

TYPHOON = [{"name": "薔琵", "intl": "CHAMPI", "analysis": [
    {"DateTime": "2026-10-25 08:00:00", "MaxWindSpeed": "28"}]}]

M_ACTIVE = [{"title": "海上颱風警報", "category": "", "typhoon_name": "薔琵",
             "effective": "2026-10-24 20:30:00", "expires": "2026-10-25 23:00:00",
             "content": "…"}]
M_EXPIRED = [{"title": "海上颱風警報", "category": "", "typhoon_name": "薔琵",
              "effective": "2026-10-22 20:30:00", "expires": "2026-10-23 14:00:00",
              "content": "…"}]
M_LIFTED = [{"title": "海上颱風警報解除", "category": "END", "typhoon_name": "薔琵",
             "effective": "2026-10-24 20:30:00", "expires": "", "content": "…"}]

results = []


def check(case, cond, detail=""):
    results.append((case, bool(cond), detail))


def risk(reports=None, marine=None, typhoons=None):
    data = {"typhoons": typhoons or [], "marine_alert": marine or [],
            "reports": reports or [], "rain": []}
    lv, items = cwa.current_risk_level("zh-Hant", data, stale={}, mode="live")
    txt = "；".join(cwa.t("zh-Hant", k, **p) for _, k, p in items)
    return lv, txt


# 1) 11/11 那筆，過期 61 小時 → 不進風險列、連中性列註記都不留、卡整張隱藏
cwa_now = D("2026-11-14 10:00")
orig_now = cwa.datetime


class _FixedDT(cwa.datetime):
    @classmethod
    def now(cls, tz=None):
        return cwa_now.replace(tzinfo=tz) if tz else cwa_now.replace(tzinfo=TZ)


cwa.datetime = _FixedDT
try:
    lv, txt = risk([R_1111])
    check("1a 11/11 案過期 61h → 🟢（不誤推 🟡）", lv == "green", f"level={lv} txt={txt}")
    card = cwa.render_alert_card("zh-Hant", [], [R_1111])
    check("1b 11/11 案過期 61h → 卡面不出現該筆", "陸上強風特報" not in card, card[:80])

    # 2) 過期 30 分鐘 → ⚪ 中性列帶「已過有效時間」；卡面轉灰＋註記
    cwa_now = D("2026-11-11 23:30")
    lv, txt = risk([R_1111])
    check("2a 過期 30min → neutral", lv == "neutral", f"level={lv}")
    check("2b 中性列帶已過有效時間", "已過有效時間" in txt, txt)
    card = cwa.render_alert_card("zh-Hant", [], [R_1111])
    check("2c 卡面轉灰＋過期註記",
          "sev-grey" in card and "有效時間已過" in card, card[:120])

    # 3) 效期內的特報照樣計入（黃）
    cwa_now = D("2026-11-14 12:00")
    lv, txt = risk([R_LIVE])
    check("3a 11/14 10:23 那筆（有效至 11/15 23:00）→ 🟡", lv == "yellow", f"level={lv}")
    check("3b 風險列措辭為「有效 …~…」", "有效 2026/11/14 20:00 ~ 2026/11/15 23:00" in txt, txt)
    card = cwa.render_alert_card("zh-Hant", [], [R_LIVE])
    check("3c 卡面保持黃色 badge（不轉灰）", "sev-yellow" in card and "有效時間已過" not in card)

    # 4) 解除報：不計入風險、中性列帶「已解除」
    cwa_now = D("2026-10-25 06:00")
    lv, txt = risk([R_LIFTED])
    check("4a 解除特報不推風險", lv == "neutral", f"level={lv}")
    check("4b 中性列帶已解除", "已解除" in txt, txt)

    # 5) 10/25 迴歸：生效豪雨特報內文含「解除大雨特報」→ 仍計入
    lv, txt = risk([R_MENTION])
    check("5a 生效豪雨特報（內文提到解除大雨）仍 🟡/🔴", lv in ("yellow", "red"), f"level={lv} {txt}")

    # 6) 全空 → 🟢
    lv, txt = risk([])
    check("6a 全空 → green", lv == "green", f"level={lv}")

    # 7) 海上警報 CAP 已到 expires、未發 END：不推紅、氣旋 badge 轉「已過效期」
    cwa_now = D("2026-10-25 12:00")
    lv, txt = risk(marine=M_EXPIRED, typhoons=TYPHOON)
    check("7a 過效期海上警報不計入紅", lv != "red", f"level={lv} {txt}")
    st = cwa.typhoon_alert_state(TYPHOON[0], M_EXPIRED)
    check("7b 氣旋狀態 → expired", st == "expired", f"state={st}")
    # 7c：過效期未過 24h → 卡面轉灰＋註記；超過 24h → 整筆移除
    M_EXP_FRESH = [{"title": "海上颱風警報", "category": "", "typhoon_name": "薔琵",
                    "effective": "2026-11-13 20:00:00", "expires": "2026-11-14 08:00:00",
                    "content": "…"}]
    cwa_now = D("2026-11-14 10:00")
    cwa.datetime = _FixedDT
    card = cwa.render_alert_card("zh-Hant", M_EXP_FRESH, [])
    check("7c 過效期 2h 的海上警報 → 卡面轉灰＋過期註記",
          "sev-grey" in card and "有效時間已過" in card, card[:160])
    cwa_now = D("2026-10-25 12:00")   # M_EXPIRED 已過期 46h > EXPIRED_TTL_HOURS
    cwa.datetime = _FixedDT
    card = cwa.render_alert_card("zh-Hant", M_EXPIRED, [])
    check("7d 過效期 46h 的海上警報 → 整筆移除", not card, card[:120])

    # 8) 生效中的海上警報照舊紅、狀態 active
    cwa_now = D("2026-10-25 09:00")
    lv, txt = risk(marine=M_ACTIVE, typhoons=TYPHOON)
    check("8a 生效海上警報 → red", lv == "red", f"level={lv}")
    check("8b 氣旋狀態 active", cwa.typhoon_alert_state(TYPHOON[0], M_ACTIVE) == "active")

    # 9) 解除報（END）行為不變：lifted、不計入風險
    cwa_now = D("2026-10-25 09:00")
    lv, txt = risk(marine=M_LIFTED, typhoons=TYPHOON)
    check("9a END 警報 → lifted（不計入紅）",
          cwa.typhoon_alert_state(TYPHOON[0], M_LIFTED) == "lifted" and lv != "red", f"lv={lv}")

    # 10) 舊快取相容：只有 'valid' 字串、無 valid_end → 仍能判過期
    old_cache = {k: v for k, v in R_1111.items() if k != "valid_end"}
    cwa_now = D("2026-11-14 10:00")
    lv, txt = risk([old_cache])
    check("10a 舊快取（無 valid_end 欄）仍判過期 → green", lv == "green", f"level={lv}")

    # 11) 日文介面：中性列與卡面註記走 ja 字串
    cwa_now = D("2026-11-11 23:30")
    lvj, itemj = cwa.current_risk_level("ja", {"typhoons": [], "marine_alert": [],
                                               "reports": [R_1111], "rain": []},
                                        stale={}, mode="live")
    jtxt = cwa.t("ja", itemj[0][1], **itemj[0][2]) if itemj else ""
    check("11a ja 中性列帶「有効時間経過」", lvj == "neutral" and "有効時間経過" in jtxt, jtxt)
finally:
    cwa.datetime = orig_now

fails = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (("  ← " + detail) if (not ok and detail) else ""))
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
