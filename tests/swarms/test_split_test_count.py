from swarms.split import split_test_count_across_policies


def test_remainder_goes_to_the_first_policies():
    counts = split_test_count_across_policies(12, ["a", "b", "c", "d", "e"])

    assert list(counts.values()) == [3, 3, 2, 2, 2]


def test_fewer_tests_than_policies_leaves_some_untested():
    counts = split_test_count_across_policies(4, ["a", "b", "c", "d", "e", "f"])

    assert list(counts.values()) == [1, 1, 1, 1, 0, 0]
