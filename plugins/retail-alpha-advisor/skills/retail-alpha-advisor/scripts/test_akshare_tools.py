#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).with_name("akshare_tools.py")
SPEC = importlib.util.spec_from_file_location("akshare_tools", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeFrame:
    def __init__(self, rows):
        self.rows = rows
        self.empty = not rows

    def to_dict(self, orient):
        assert orient == "records"
        return self.rows


class FakeAkshare:
    __version__ = "1.18-test"

    def stock_individual_info_em(self, **kwargs):
        return FakeFrame([{"item": "股票代码", "value": kwargs["symbol"]}, {"item": "行业", "value": "白酒"}])

    def stock_individual_basic_info_xq(self, **kwargs):
        return FakeFrame([{"item": "公司名称", "value": "贵州茅台酒股份有限公司"}, {"item": "主营业务", "value": "白酒"}])

    def stock_profile_cninfo(self, **kwargs):
        return FakeFrame([{"证券代码": kwargs["symbol"], "公司名称": "贵州茅台酒股份有限公司"}])

    def stock_bid_ask_em(self, **kwargs):
        return FakeFrame([{"item": "最新", "value": 1500.0}])

    def stock_individual_spot_xq(self, **kwargs):
        return FakeFrame([{"item": "现价", "value": 1499.0}])

    def stock_zh_a_spot(self):
        return FakeFrame([{"代码": "sh600519", "名称": "贵州茅台", "最新价": 1498.0}])

    def stock_zh_a_hist(self, **kwargs):
        return FakeFrame(
            [
                {"日期": "2026-06-27", "开盘": 10, "最高": 11, "最低": 9, "收盘": 10.5, "成交量": 100},
                {"日期": "2026-06-28", "开盘": 10.5, "最高": 12, "最低": 10, "收盘": 11.5, "成交量": 120},
            ]
        )

    def stock_zh_a_hist_tx(self, **kwargs):
        return FakeFrame([{"date": "2026-06-28", "open": 10, "high": 12, "low": 10, "close": 11.5, "amount": 120}])

    def stock_zh_a_daily(self, **kwargs):
        return FakeFrame([{"date": "2026-06-28", "open": 10, "high": 12, "low": 10, "close": 11.5, "volume": 120}])

    def stock_zyjs_ths(self, **kwargs):
        return FakeFrame([{"股票代码": kwargs["symbol"], "主营业务": "白酒生产与销售", "产品名称": "茅台酒"}])

    def stock_zygc_em(self, **kwargs):
        return FakeFrame([{"报告日期": "2025-12-31", "分类类型": "产品", "主营收入": 100}])

    def stock_board_industry_spot_em(self, **kwargs):
        raise RuntimeError("spot unavailable")

    def stock_board_industry_name_em(self):
        raise RuntimeError("industry list unavailable")

    def stock_board_industry_name_ths(self):
        return FakeFrame([{"name": "白酒"}])

    def stock_board_industry_hist_em(self, **kwargs):
        return FakeFrame([{"日期": "2026-06-28", "收盘": 1234}])

    def stock_board_industry_cons_em(self, **kwargs):
        return FakeFrame([{"代码": "600519", "名称": "贵州茅台"}])


class AkshareToolsTests(unittest.TestCase):
    def setUp(self):
        MODULE._AKSHARE = FakeAkshare()

    def tearDown(self):
        MODULE._AKSHARE = None

    def test_profile_preserves_provenance(self):
        result = MODULE.get_instrument_profile("600519", "stock")
        self.assertTrue(result["ok"])
        self.assertEqual("白酒", result["data"]["行业"])
        self.assertEqual("stock_individual_info_em", result["source"]["function"])

    def test_price_history_is_normalized(self):
        result = MODULE.get_price_history("600519", "20260601", "20260629", limit=10)
        self.assertEqual("2026-06-28", result["latest_data_date"])
        self.assertEqual(11.5, result["data"][1]["close"])
        self.assertEqual("EastMoney", result["selected_provider"])

    def test_price_history_falls_back_to_tencent_with_attempt_trace(self):
        MODULE._AKSHARE.stock_zh_a_hist = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("eastmoney down"))
        result = MODULE.get_price_history("600519", "20260601", "20260629", limit=10)
        self.assertEqual("Tencent", result["selected_provider"])
        self.assertEqual("stock_zh_a_hist_tx", result["source"]["function"])
        self.assertEqual(["failed", "success"], [item["status"] for item in result["attempts"]])

    def test_profile_falls_back_to_xueqiu(self):
        MODULE._AKSHARE.stock_individual_info_em = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("eastmoney down"))
        result = MODULE.get_instrument_profile("600519", "stock")
        self.assertEqual("Xueqiu", result["selected_provider"])
        self.assertEqual("贵州茅台酒股份有限公司", result["data"]["公司名称"])

    def test_profile_falls_back_to_cninfo_after_xueqiu_failure(self):
        MODULE._AKSHARE.stock_individual_info_em = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("eastmoney down"))
        MODULE._AKSHARE.stock_individual_basic_info_xq = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("xueqiu down"))
        result = MODULE.get_instrument_profile("600519", "stock")
        self.assertEqual("CNInfo", result["selected_provider"])
        self.assertEqual("stock_profile_cninfo", result["selected_function"])

    def test_realtime_quote_falls_back_to_xueqiu(self):
        MODULE._AKSHARE.stock_bid_ask_em = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("eastmoney down"))
        result = MODULE.get_realtime_quote("600519", "stock")
        self.assertEqual("Xueqiu", result["selected_provider"])
        self.assertEqual(1499.0, result["data"]["现价"])

    def test_realtime_quote_falls_back_to_sina_after_xueqiu_failure(self):
        MODULE._AKSHARE.stock_bid_ask_em = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("eastmoney down"))
        MODULE._AKSHARE.stock_individual_spot_xq = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("xueqiu down"))
        result = MODULE.get_realtime_quote("600519", "stock")
        self.assertEqual("Sina", result["selected_provider"])
        self.assertEqual(1498.0, result["data"]["最新价"])

    def test_company_business_includes_introduction_and_composition(self):
        result = MODULE.get_company_business("600519")
        self.assertEqual("白酒生产与销售", result["data"]["business_introduction"][0]["主营业务"])
        self.assertEqual(100, result["data"]["main_business_composition"][0]["主营收入"])
        self.assertEqual("stock_zyjs_ths", result["selected_function"])

    def test_price_history_drops_incomplete_current_day(self):
        original = MODULE._china_now
        MODULE._china_now = lambda: datetime(2026, 6, 28, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        try:
            result = MODULE.get_price_history("600519", "20260601", "20260629", limit=10)
        finally:
            MODULE._china_now = original
        self.assertEqual("2026-06-27", result["latest_data_date"])
        self.assertIn("excluded incomplete current-day bar", result["quality_flags"][0])

    def test_industry_snapshot_preserves_partial_error(self):
        result = MODULE.get_industry_snapshot("白酒", "20260601", "20260629")
        self.assertEqual("2026-06-28", result["latest_data_date"])
        self.assertIn("stock_board_industry_spot_em", result["component_errors"])
        self.assertEqual("600519", result["data"]["constituents"][0]["代码"])

    def test_industry_list_uses_disclosed_fallback(self):
        result = MODULE.list_industries(limit=10)
        self.assertEqual("白酒", result["data"][0]["name"])
        self.assertIn("stock_board_industry_name_em", result["component_errors"])
        self.assertEqual("stock_board_industry_name_ths", result["source"]["function"])
        self.assertEqual("10jqka", result["selected_provider"])

    def test_tool_schemas_and_unknown_tool(self):
        names = {item["function"]["name"] for item in MODULE.get_tool_definitions()}
        self.assertIn("get_stock_financials", names)
        self.assertIn("get_company_business", names)
        self.assertIn("get_realtime_quote", names)
        with self.assertRaises(MODULE.ToolError):
            MODULE.call_tool("delete_everything", {})


if __name__ == "__main__":
    unittest.main()
