import importlib.util
import sys
import types
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import pandas as pd

sys.modules['akshare'] = types.ModuleType('akshare')
spec = importlib.util.spec_from_file_location('market_update', Path(__file__).parent / 'scripts/update_market_data.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class MarketTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({'名称': m.INDEX_NAMES, '最新价': [3000, 10000, 2000, 1000], '涨跌幅': [1, 2, 3, 4]})
        self.api = types.SimpleNamespace(stock_zh_a_spot_em=Mock(return_value=pd.DataFrame()), stock_zh_index_spot_em=Mock(return_value=self.frame), stock_board_concept_name_em=Mock(return_value=pd.DataFrame()), stock_zh_a_spot=Mock(return_value=pd.DataFrame()), stock_zh_index_spot_sina=Mock(return_value=self.frame))
    def test_explicit_index_universe(self):
        with patch.object(m, 'ak', self.api):
            result = m.fetch_market_frames()
        self.api.stock_zh_index_spot_em.assert_called_once_with(symbol='沪深重要指数')
        self.assertEqual(result[3], '东方财富')
        snapshot = {'indices': [{'name': n} for n in m.INDEX_NAMES]}
        self.assertEqual(m.update_indices(snapshot, result[1]), [1, 2, 3, 4])
    def test_incomplete_primary_uses_fallback(self):
        self.api.stock_zh_index_spot_em.return_value = self.frame.iloc[:1]
        with patch.object(m, 'ak', self.api), patch.object(m.time_module, 'sleep'):
            result = m.fetch_market_frames()
        self.assertEqual(result[3], '新浪财经（备用源）')
        self.assertEqual(self.api.stock_zh_index_spot_em.call_count, 2)
    def test_both_incomplete_leave_snapshot_untouched(self):
        self.api.stock_zh_index_spot_em.return_value = self.frame.iloc[:1]
        self.api.stock_zh_index_spot_sina.return_value = self.frame.iloc[:1]
        with patch.object(m, 'ak', self.api), patch.object(m.time_module, 'sleep'), patch.object(m, 'load_snapshot', return_value={}), patch.object(m, 'update_portfolios') as write:
            m.update_snapshot('close-decision')
            write.assert_not_called()

if __name__ == '__main__':
    unittest.main()
