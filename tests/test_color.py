import pytest

import color


def test_parse_hex_roundtrip():
    assert color.parse_hex("#ff8800") == (255, 136, 0)
    assert color.rgb_to_hex((255, 136, 0)).lower() == "#ff8800"


def test_parse_hex_rejects_garbage():
    assert not color.parse_hex("not-a-color")


@pytest.mark.parametrize("fg,bg,expected", [
    ("#000000", "#ffffff", 21.0),
    ("#ffffff", "#ffffff", 1.0),
])
def test_contrast_ratio_extremes(fg, bg, expected):
    assert color.contrast_ratio(fg, bg) == pytest.approx(expected, abs=0.01)


def test_wcag_grades():
    assert color.wcag_grade("#000000", "#ffffff")["tag"] == "AAA"
    assert color.wcag_grade("#767676", "#ffffff")["tag"] == "AA"
    assert color.wcag_grade("#ffffff", "#ffffff")["tag"] == "fail"


def test_oklab_roundtrip():
    for rgb in [(255, 0, 0), (12, 200, 90), (128, 128, 128)]:
        back = color.oklab_to_rgb(color.rgb_to_oklab(rgb))
        assert all(abs(a - b) <= 1 for a, b in zip(rgb, back))
