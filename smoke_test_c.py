from data.data_aggregator import DataAggregator
import inspect

# Verify _chain method exists and has correct signature
assert hasattr(DataAggregator, '_chain'), '_chain method missing'
sig = inspect.signature(DataAggregator._chain)
params = list(sig.parameters.keys())
assert 'providers' in params, 'providers param missing'
assert 'empty_default' in params, 'empty_default param missing'
print('_chain signature OK:', params)

# Verify _chain logic with a mock
class MockSource:
    def get_x(self): return []
    def get_y(self): return {'data': 1}
    def get_z(self): raise RuntimeError('boom')

agg = DataAggregator.__new__(DataAggregator)
import logging
agg.logger = logging.getLogger('test')

s = MockSource()

# Empty result should fall through
r1 = agg._chain([(s, 'get_x'), (s, 'get_y')], empty_default=None)
assert r1 == {'data': 1}, f'Expected fallthrough to get_y, got {r1}'
print('Fallthrough on empty list: OK')

# Exception should fall through
r2 = agg._chain([(s, 'get_z'), (s, 'get_y')], empty_default=None)
assert r2 == {'data': 1}, f'Expected fallthrough after exception, got {r2}'
print('Fallthrough on exception: OK')

# None source should be skipped
r3 = agg._chain([(None, 'get_y'), (s, 'get_y')], empty_default=None)
assert r3 == {'data': 1}, f'Expected skip None source, got {r3}'
print('Skip None source: OK')

# All fail returns default
r4 = agg._chain([(s, 'get_x'), (None, 'get_x')], empty_default=[])
assert r4 == [], f'Expected empty default, got {r4}'
print('All-fail returns default: OK')

# Verify get_company_data uses _chain (source inspection)
src = inspect.getsource(DataAggregator.get_company_data)
assert '_chain' in src, '_chain not used in get_company_data'
print('get_company_data uses _chain: OK')

print()
print('All Sub-task B checks passed')
