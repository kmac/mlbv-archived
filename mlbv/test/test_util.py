"""pytest test cases for the util module
"""

from mlbv.mlbam.common import util


def test_csv_list():
    list1 = ['e1', 'e2', 'e3']
    string1 = 'e1, e2, e3'
    assert list1[1] == util.get_csv_list(string1)[1]
