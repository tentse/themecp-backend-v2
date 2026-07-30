"""
Unit tests for performance and rating calculation formulas.

Tests the static methods:
- ContestSessionService._calculate_performance
- ContestSessionService._calculate_rating

Uses 85 rows of real contest data from a spreadsheet to verify correctness.
The rows are sequential contests for one user, where each row's output rating
feeds into the next row as last_rating. Row 0's expected rating (1952) is the
starting baseline.
"""

import pytest
from types import SimpleNamespace

from api.contest_session.contest_session_services import ContestSessionService


STARTING_RATING = 1952

# Each tuple: (level, r1, r2, r3, r4, t1, t2, t3, t4, expected_perf, expected_rating)
# Empty solve times are None. Row 0's expected_rating is the starting baseline.
CONTEST_DATA = [
    # Row 0
    (44, 1600, 1800, 2000, 2100, 25, 48, 91, None, 2033, 1952),
    # Row 1
    (45, 1600, 1800, 2000, 2200, 17, 44, 65, None, 2104, 1962),
    # Row 2
    (41, 1500, 1700, 1900, 2100, 9, 20, 58, 94, 2187, 1977),
    # Row 3
    (41, 1500, 1700, 1900, 2100, 14, 28, 39, 74, 2253, 1995),
    # Row 4
    (41, 1500, 1700, 1900, 2100, 14, 19, 81, 114, 2120, 2003),
    # Row 5
    (41, 1500, 1700, 1900, 2100, 45, 57, 82, 103, 2157, 2013),
    # Row 6
    (42, 1500, 1700, 1900, 2200, 10, 37, 80, None, 2022, 2014),
    # Row 7
    (41, 1500, 1700, 1900, 2100, 8, 39, 51, 112, 2127, 2022),
    # Row 8
    (42, 1600, 1700, 1900, 2100, 6, 22, 38, 64, 2299, 2040),
    # Row 9
    (43, 1600, 1800, 1900, 2100, 18, 68, None, None, 1850, 2027),
    # Row 10
    (41, 1500, 1700, 1900, 2100, 15, 46, 82, 107, 2143, 2035),
    # Row 11
    (43, 1600, 1800, 1900, 2100, 4, 79, 110, None, 1937, 2028),
    # Row 12
    (42, 1600, 1700, 1900, 2100, 6, 41, 67, 103, 2169, 2037),
    # Row 13
    (43, 1600, 1800, 1900, 2100, 8, 46, 72, None, 1993, 2034),
    # Row 14
    (42, 1600, 1700, 1900, 2100, 19, 31, 75, None, 1989, 2031),
    # Row 15
    (41, 1500, 1700, 1900, 2100, 8, 31, 59, None, 2013, 2030),
    # Row 16
    (40, 1500, 1700, 1900, 2000, 18, 55, 73, 102, 2098, 2035),
    # Row 17
    (41, 1500, 1700, 1900, 2100, 20, 37, 82, None, 1979, 2031),
    # Row 18
    (40, 1500, 1700, 1900, 2000, 9, 27, 52, None, 1961, 2026),
    # Row 19
    (39, 1500, 1700, 1800, 2000, 12, 40, 66, 111, 2055, 2028),
    # Row 20
    (40, 1500, 1700, 1900, 2000, 12, 49, 102, None, 1924, 2021),
    # Row 21
    (42, 1600, 1700, 1900, 2100, 11, 23, 79, 100, 2179, 2032),
    # Row 22
    (43, 1600, 1800, 1900, 2100, 57, 77, 113, None, 1933, 2025),
    # Row 23
    (42, 1600, 1700, 1900, 2100, 15, 29, 62, 89, 2216, 2038),
    # Row 24
    (43, 1600, 1800, 1900, 2100, 14, 33, 44, 61, 2322, 2057),
    # Row 25
    (44, 1600, 1800, 2000, 2100, 18, 36, 59, 80, 2271, 2071),
    # Row 26
    (45, 1600, 1800, 2000, 2200, 9, 25, 44, 68, 2373, 2091),
    # Row 27
    (46, 1700, 1800, 2000, 2200, 23, 46, 83, None, 2077, 2090),
    # Row 28
    (45, 1600, 1800, 2000, 2200, 10, 36, None, None, 1947, 2080),
    # Row 29
    (44, 1600, 1800, 2000, 2100, 8, 19, 27, 69, 2308, 2095),
    # Row 30
    (45, 1600, 1800, 2000, 2200, 6, 17, 45, None, 2133, 2098),
    # Row 31
    (44, 1600, 1800, 2000, 2100, 7, 42, 118, None, 2013, 2092),
    # Row 32
    (43, 1600, 1800, 1900, 2100, 22, 42, 62, 90, 2225, 2101),
    # Row 33
    (44, 1600, 1800, 2000, 2100, 10, 21, 37, 54, 2358, 2118),
    # Row 34
    (45, 1600, 1800, 2000, 2200, 6, 27, 64, 119, 2203, 2124),
    # Row 35
    (46, 1700, 1800, 2000, 2200, 12, 21, 41, 77, 2356, 2139),
    # Row 36
    (47, 1700, 1900, 2000, 2200, 8, 30, 52, 79, 2362, 2154),
    # Row 37
    (48, 1700, 1900, 2100, 2200, 19, 28, 62, None, 2154, 2154),
    # Row 38
    (47, 1700, 1900, 2000, 2200, 18, 48, 94, None, 2061, 2148),
    # Row 39
    (46, 1700, 1800, 2000, 2200, 17, 50, 73, None, 2092, 2144),
    # Row 40
    (45, 1600, 1800, 2000, 2200, 9, 30, 68, None, 2099, 2141),
    # Row 41
    (44, 1600, 1800, 2000, 2100, 6, 39, 61, 109, 2174, 2143),
    # Row 42
    (45, 1600, 1800, 2000, 2200, 30, 48, 92, None, 2064, 2138),
    # Row 43
    (44, 1600, 1800, 2000, 2100, 16, 37, 63, None, 2053, 2132),
    # Row 44
    (43, 1600, 1800, 1900, 2100, 4, 28, 51, 94, 2212, 2137),
    # Row 45
    (44, 1600, 1800, 2000, 2100, 13, 37, 66, 93, 2228, 2143),
    # Row 46
    (45, 1600, 1800, 2000, 2200, 9, 26, 49, 90, 2300, 2153),
    # Row 47
    (46, 1700, 1800, 2000, 2200, 11, 42, 94, None, 2061, 2147),
    # Row 48
    (45, 1600, 1800, 2000, 2200, 9, 26, 90, 115, 2217, 2152),
    # Row 49
    (46, 1700, 1800, 2000, 2200, 20, 37, 64, None, 2105, 2149),
    # Row 50
    (45, 1600, 1800, 2000, 2200, 15, 37, 68, None, 2099, 2146),
    # Row 51
    (44, 1600, 1800, 2000, 2100, 21, 47, 64, 99, 2208, 2150),
    # Row 52
    (45, 1600, 1800, 2000, 2200, 14, 38, None, None, 1944, 2136),
    # Row 53
    (44, 1600, 1800, 2000, 2100, 10, 54, 86, 109, 2174, 2139),
    # Row 54
    (45, 1600, 1800, 2000, 2200, 15, 34, 67, 95, 2283, 2149),
    # Row 55
    (46, 1700, 1800, 2000, 2200, 24, 43, 77, None, 2086, 2145),
    # Row 56
    (45, 1600, 1800, 2000, 2200, 8, 28, 82, None, 2079, 2141),
    # Row 57
    (44, 1600, 1800, 2000, 2100, 19, 41, 59, 96, 2218, 2146),
    # Row 58
    (45, 1600, 1800, 2000, 2200, 12, 31, 76, 100, 2267, 2154),
    # Row 59
    (46, 1700, 1800, 2000, 2200, 24, 37, 80, 104, 2266, 2161),
    # Row 60
    (47, 1700, 1900, 2000, 2200, None, None, None, None, 1650, 2127),
    # Row 61
    (46, 1700, 1800, 2000, 2200, 11, 35, 116, None, 2028, 2120),
    # Row 62
    (45, 1600, 1800, 2000, 2200, 19, 33, None, None, 1951, 2109),
    # Row 63
    (44, 1600, 1800, 2000, 2100, 11, 30, 57, 119, 2141, 2111),
    # Row 64
    (45, 1600, 1800, 2000, 2200, 8, 20, 59, None, 2113, 2111),
    # Row 65
    (44, 1600, 1800, 2000, 2100, 18, 28, 66, 110, 2171, 2115),
    # Row 66
    (45, 1600, 1800, 2000, 2200, 11, 26, 38, 75, 2350, 2131),
    # Row 67
    (46, 1700, 1800, 2000, 2200, 13, 25, 67, 109, 2249, 2139),
    # Row 68
    (47, 1700, 1900, 2000, 2200, 12, 27, 53, 105, 2275, 2148),
    # Row 69
    (48, 1700, 1900, 2100, 2200, 10, 66, 95, 112, 2264, 2156),
    # Row 70
    (49, 1700, 1900, 2100, 2300, 15, 28, 82, None, 2179, 2158),
    # Row 71
    (48, 1700, 1900, 2100, 2200, 19, 49, 86, 113, 2261, 2165),
    # Row 72
    (49, 1700, 1900, 2100, 2300, 22, None, None, None, 1867, 2145),
    # Row 73
    (48, 1700, 1900, 2100, 2200, 11, 44, 58, 116, 2251, 2152),
    # Row 74
    (49, 1700, 1900, 2100, 2300, 12, 56, 110, None, 2137, 2151),
    # Row 75
    (48, 1700, 1900, 2100, 2200, 38, None, None, None, 1844, 2131),
    # Row 76
    (47, 1700, 1900, 2000, 2200, 25, 73, None, None, 1946, 2119),
    # Row 77
    (46, 1700, 1800, 2000, 2200, 29, 60, None, None, 1911, 2105),
    # Row 78
    (45, 1600, 1800, 2000, 2200, 12, 26, 46, 94, 2287, 2117),
    # Row 79
    (46, 1700, 1800, 2000, 2200, 29, 38, 50, 97, 2289, 2128),
    # Row 80
    (47, 1700, 1900, 2000, 2200, 14, 52, 87, None, 2071, 2124),
    # Row 81
    (46, 1700, 1800, 2000, 2200, 11, 21, 70, None, 2096, 2122),
    # Row 82
    (45, 1600, 1800, 2000, 2200, 10, 25, 56, 82, 2327, 2136),
    # Row 83
    (46, 1700, 1800, 2000, 2200, 7, 50, 62, 87, 2323, 2148),
    # Row 84
    (47, 1700, 1900, 2000, 2200, 8, 23, 35, 62, 2418, 2166),
    # Row 85
    (48, 1700, 1900, 2100, 2200, 28, 59, None, None, 2013, 2156),
    # Row 86
    (47, 1700, 1900, 2000, 2200, 16, 23, 43, 78, 2365, 2170),
]


def _build_problem_statuses(r1, r2, r3, r4, t1, t2, t3, t4):
    """Build a list of mock problem status objects from ratings and solve times."""
    return [
        SimpleNamespace(problem_rating=r1, solved_in_min=t1),
        SimpleNamespace(problem_rating=r2, solved_in_min=t2),
        SimpleNamespace(problem_rating=r3, solved_in_min=t3),
        SimpleNamespace(problem_rating=r4, solved_in_min=t4),
    ]


@pytest.mark.parametrize(
    "level, r1, r2, r3, r4, t1, t2, t3, t4, expected_perf, expected_rating",
    CONTEST_DATA,
    ids=[f"row_{i}" for i in range(len(CONTEST_DATA))],
)
def test_calculate_performance(
    level, r1, r2, r3, r4, t1, t2, t3, t4, expected_perf, expected_rating
):
    """Verify _calculate_performance matches expected performance for each row."""
    problem_statuses = _build_problem_statuses(r1, r2, r3, r4, t1, t2, t3, t4)
    actual_perf = ContestSessionService._calculate_performance(
        level=level, problem_statuses=problem_statuses
    )
    assert actual_perf == expected_perf, (
        f"Performance mismatch: got {actual_perf}, expected {expected_perf}"
    )


def test_calculate_rating_sequential():
    """
    Verify _calculate_rating produces correct ratings across all 87 sequential
    contests. Row 0's expected rating (1952) is the starting baseline.
    From row 1 onward, each row's last_rating is the previous row's expected rating.
    """
    last_rating = STARTING_RATING

    for i in range(1, len(CONTEST_DATA)):
        row = CONTEST_DATA[i]
        level, r1, r2, r3, r4, t1, t2, t3, t4, expected_perf, expected_rating = row

        actual_rating = ContestSessionService._calculate_rating(
            performance=expected_perf,
            last_rating=last_rating,
            first_problem_solve_time=t1,
        )

        assert actual_rating == expected_rating, (
            f"Row {i}: Rating mismatch: got {actual_rating}, expected {expected_rating} "
            f"(last_rating={last_rating}, performance={expected_perf}, t1={t1})"
        )

        last_rating = expected_rating


def test_calculate_rating_with_codeforces_rating_as_last_rating():
    """
    When last_rating is provided (e.g. Codeforces rating fallback), formula is unchanged.
    performance=1193, last_rating=1600, first_problem_solve_time=10 -> 1573.
    """
    actual = ContestSessionService._calculate_rating(
        performance=1193,
        last_rating=1600,
        first_problem_solve_time=10,
    )
    assert actual == 1573
