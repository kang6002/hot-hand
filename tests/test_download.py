from download import month_ranges


def test_months_cover_october_to_august_without_gaps():
    ranges = month_ranges("2025-26")
    assert [label for label, _, _ in ranges] == [
        "2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
        "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
    ]
    assert ranges[0][1:] == ("10/01/2025", "10/31/2025")
    assert ranges[-1][1:] == ("08/01/2026", "08/31/2026")


def test_february_end_handles_leap_years():
    feb = {label: last for label, _, last in month_ranges("2019-20")}
    assert feb["2020-02"] == "02/29/2020"
    feb = {label: last for label, _, last in month_ranges("2020-21")}
    assert feb["2021-02"] == "02/28/2021"
