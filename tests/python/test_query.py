from lab.query import query,where_filter
import pytest


def test_filter_values_are_sql_literals():
    result=where_filter(["O'Brien; $(echo nope)"],["0001"],True)
    assert "'O''Brien; $(echo nope)'" in result
    assert "Entity('fund')" in result
    assert "Dimension('fund__registrant_cik')" in result


def test_unknown_metrics_and_invalid_identifiers_fail_before_subprocess():
    with pytest.raises(ValueError,match='Unknown'):
        query(['made_up_metric'])
    with pytest.raises(ValueError,match='identifier'):
        query(['gross_sales'],group_by=['fund; drop table x'])
