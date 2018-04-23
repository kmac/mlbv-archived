"""pytest test cases for the util module
"""

from mlbam import util


def test_csv_list():
    l1 = ['e1', 'e2', 'e3']
    s1 = 'e1, e2, e3'
    assert l1[1] == util.get_csv_list(s1)[1]
