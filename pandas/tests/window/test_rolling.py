from datetime import timedelta

import numpy as np
import pytest

from pandas.errors import UnsupportedFunctionCall
import pandas.util._test_decorators as td

import pandas as pd
from pandas import DataFrame, Series
import pandas.core.window as rwindow
from pandas.tests.window.common import Base
import pandas.util.testing as tm


class TestRolling(Base):
    def setup_method(self, method):
        self._create_data()

    def test_doc_string(self):

        df = DataFrame({"B": [0, 1, 2, np.nan, 4]})
        df
        df.rolling(2).sum()
        df.rolling(2, min_periods=1).sum()

    @pytest.mark.parametrize("which", ["series", "frame"])
    def test_constructor(self, which):
        # GH 12669

        o = getattr(self, which)
        c = o.rolling

        # valid
        c(window=2)
        c(window=2, min_periods=1)
        c(window=2, min_periods=1, center=True)
        c(window=2, min_periods=1, center=False)

        # GH 13383
        with pytest.raises(ValueError):
            c(0)
            c(-1)

        # not valid
        for w in [2.0, "foo", np.array([2])]:
            with pytest.raises(ValueError):
                c(window=w)
            with pytest.raises(ValueError):
                c(window=2, min_periods=w)
            with pytest.raises(ValueError):
                c(window=2, min_periods=1, center=w)

    @td.skip_if_no_scipy
    @pytest.mark.parametrize("which", ["series", "frame"])
    def test_constructor_with_win_type(self, which):
        # GH 13383
        o = getattr(self, which)
        c = o.rolling
        with pytest.raises(ValueError):
            c(-1, win_type="boxcar")

    @pytest.mark.parametrize("window", [timedelta(days=3), pd.Timedelta(days=3)])
    def test_constructor_with_timedelta_window(self, window):
        # GH 15440
        n = 10
        df = DataFrame(
            {"value": np.arange(n)},
            index=pd.date_range("2015-12-24", periods=n, freq="D"),
        )
        expected_data = np.append([0.0, 1.0], np.arange(3.0, 27.0, 3))

        result = df.rolling(window=window).sum()
        expected = DataFrame(
            {"value": expected_data},
            index=pd.date_range("2015-12-24", periods=n, freq="D"),
        )
        tm.assert_frame_equal(result, expected)
        expected = df.rolling("3D").sum()
        tm.assert_frame_equal(result, expected)

    @pytest.mark.parametrize("window", [timedelta(days=3), pd.Timedelta(days=3), "3D"])
    def test_constructor_timedelta_window_and_minperiods(self, window, raw):
        # GH 15305
        n = 10
        df = DataFrame(
            {"value": np.arange(n)},
            index=pd.date_range("2017-08-08", periods=n, freq="D"),
        )
        expected = DataFrame(
            {"value": np.append([np.NaN, 1.0], np.arange(3.0, 27.0, 3))},
            index=pd.date_range("2017-08-08", periods=n, freq="D"),
        )
        result_roll_sum = df.rolling(window=window, min_periods=2).sum()
        result_roll_generic = df.rolling(window=window, min_periods=2).apply(
            sum, raw=raw
        )
        tm.assert_frame_equal(result_roll_sum, expected)
        tm.assert_frame_equal(result_roll_generic, expected)

    @pytest.mark.parametrize(
        "dataframe,expected,window",
        [
            (
                DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
                [({"A": [1, 2, 3], "B": [4, 5, 6]}, [0, 1, 2])],
                3,
            ),
            (
                DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
                [
                    ({"A": [1, 2], "B": [4, 5]}, [0, 1]),
                    ({"A": [2, 3], "B": [5, 6]}, [1, 2]),
                ],
                2,
            ),
            (
                DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
                [
                    ({"A": [1], "B": [4]}, [0]),
                    ({"A": [2], "B": [5]}, [1]),
                    ({"A": [3], "B": [6]}, [2]),
                ],
                1,
            ),
            (DataFrame({"A": [1], "B": [4]}), [], 1337),
            (DataFrame(), [({}, [])], 1337),
        ],
    )
    def test_iterator_dataframe(self, dataframe, expected, window):
        expected = [DataFrame(values, index=index) for (values, index) in expected]

        for (expected, actual) in zip(expected, dataframe.rolling(window)):
            tm.assert_frame_equal(actual, expected)

    @pytest.mark.parametrize(
        "series,expected,window",
        [
            (Series([1, 2, 3]), [([1, 2, 3], [0, 1, 2])], 3),
            (Series([1, 2, 3]), [([1, 2], [0, 1]), ([2, 3], [1, 2])], 2),
            (Series([1, 2, 3]), [([1], [0]), ([2], [1]), ([3], [2])], 1),
            (Series([1, 2]), [([1, 2], [0, 1])], 1337),
            (Series([]), [], 1337),
        ],
    )
    def test_iterator_series(self, series, expected, window):
        expected = [Series(values, index=index) for (values, index) in expected]

        for (expected, actual) in zip(expected, series.rolling(window)):
            tm.assert_series_equal(actual, expected)

    @pytest.mark.parametrize(
        "dataframe,expected,window,minp",
        [
            (
                DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
                [
                    ({"A": [1, 2], "B": [4, 5]}, [0, 1]),
                    ({"A": [1, 2, 3], "B": [4, 5, 6]}, [0, 1, 2])
                ],
                3,
                2
            ),
            (
                DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
                [],
                3,
                4
            ),
        ],
    )
    def test_iterator_dataframe_min_periods(self, dataframe, expected, window, minp):
        expected = [DataFrame(values, index=index) for (values, index) in expected]

        for (expected, actual) in zip(expected, dataframe.rolling(window, min_periods=minp)):
            tm.assert_frame_equal(actual, expected)

    @pytest.mark.parametrize(
        "series,expected,window,minp",
        [
            (Series([1, 2, 3]), [([1, 2], [0, 1]), ([1, 2, 3], [0, 1, 2])], 3, 2),
            (Series([1, 2, 3]), [], 3, 4)
        ],
    )
    def test_iterator_series_min_periods(self, series, expected, window, minp):
        expected = [Series(values, index=index) for (values, index) in expected]

        for (expected, actual) in zip(expected, series.rolling(window, min_periods=minp)):
            tm.assert_series_equal(actual, expected)

    @pytest.mark.parametrize("method", ["std", "mean", "sum", "max", "min", "var"])
    def test_numpy_compat(self, method):
        # see gh-12811
        r = rwindow.Rolling(Series([2, 4, 6]), window=2)

        msg = "numpy operations are not valid with window objects"

        with pytest.raises(UnsupportedFunctionCall, match=msg):
            getattr(r, method)(1, 2, 3)
        with pytest.raises(UnsupportedFunctionCall, match=msg):
            getattr(r, method)(dtype=np.float64)

    def test_closed(self):
        df = DataFrame({"A": [0, 1, 2, 3, 4]})
        # closed only allowed for datetimelike
        with pytest.raises(ValueError):
            df.rolling(window=3, closed="neither")

    @pytest.mark.parametrize("closed", ["neither", "left"])
    def test_closed_empty(self, closed, arithmetic_win_operators):
        # GH 26005
        func_name = arithmetic_win_operators
        ser = pd.Series(
            data=np.arange(5), index=pd.date_range("2000", periods=5, freq="2D")
        )
        roll = ser.rolling("1D", closed=closed)

        result = getattr(roll, func_name)()
        expected = pd.Series([np.nan] * 5, index=ser.index)
        tm.assert_series_equal(result, expected)

    @pytest.mark.parametrize("func", ["min", "max"])
    def test_closed_one_entry(self, func):
        # GH24718
        ser = pd.Series(data=[2], index=pd.date_range("2000", periods=1))
        result = getattr(ser.rolling("10D", closed="left"), func)()
        tm.assert_series_equal(result, pd.Series([np.nan], index=ser.index))

    @pytest.mark.parametrize("func", ["min", "max"])
    def test_closed_one_entry_groupby(self, func):
        # GH24718
        ser = pd.DataFrame(
            data={"A": [1, 1, 2], "B": [3, 2, 1]},
            index=pd.date_range("2000", periods=3),
        )
        result = getattr(
            ser.groupby("A", sort=False)["B"].rolling("10D", closed="left"), func
        )()
        exp_idx = pd.MultiIndex.from_arrays(
            arrays=[[1, 1, 2], ser.index], names=("A", None)
        )
        expected = pd.Series(data=[np.nan, 3, np.nan], index=exp_idx, name="B")
        tm.assert_series_equal(result, expected)

    @pytest.mark.parametrize("input_dtype", ["int", "float"])
    @pytest.mark.parametrize(
        "func,closed,expected",
        [
            ("min", "right", [0.0, 0, 0, 1, 2, 3, 4, 5, 6, 7]),
            ("min", "both", [0.0, 0, 0, 0, 1, 2, 3, 4, 5, 6]),
            ("min", "neither", [np.nan, 0, 0, 1, 2, 3, 4, 5, 6, 7]),
            ("min", "left", [np.nan, 0, 0, 0, 1, 2, 3, 4, 5, 6]),
            ("max", "right", [0.0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
            ("max", "both", [0.0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
            ("max", "neither", [np.nan, 0, 1, 2, 3, 4, 5, 6, 7, 8]),
            ("max", "left", [np.nan, 0, 1, 2, 3, 4, 5, 6, 7, 8]),
        ],
    )
    def test_closed_min_max_datetime(self, input_dtype, func, closed, expected):
        # see gh-21704
        ser = pd.Series(
            data=np.arange(10).astype(input_dtype),
            index=pd.date_range("2000", periods=10),
        )

        result = getattr(ser.rolling("3D", closed=closed), func)()
        expected = pd.Series(expected, index=ser.index)
        tm.assert_series_equal(result, expected)

    def test_closed_uneven(self):
        # see gh-21704
        ser = pd.Series(data=np.arange(10), index=pd.date_range("2000", periods=10))

        # uneven
        ser = ser.drop(index=ser.index[[1, 5]])
        result = ser.rolling("3D", closed="left").min()
        expected = pd.Series([np.nan, 0, 0, 2, 3, 4, 6, 6], index=ser.index)
        tm.assert_series_equal(result, expected)

    @pytest.mark.parametrize(
        "func,closed,expected",
        [
            ("min", "right", [np.nan, 0, 0, 1, 2, 3, 4, 5, np.nan, np.nan]),
            ("min", "both", [np.nan, 0, 0, 0, 1, 2, 3, 4, 5, np.nan]),
            ("min", "neither", [np.nan, np.nan, 0, 1, 2, 3, 4, 5, np.nan, np.nan]),
            ("min", "left", [np.nan, np.nan, 0, 0, 1, 2, 3, 4, 5, np.nan]),
            ("max", "right", [np.nan, 1, 2, 3, 4, 5, 6, 6, np.nan, np.nan]),
            ("max", "both", [np.nan, 1, 2, 3, 4, 5, 6, 6, 6, np.nan]),
            ("max", "neither", [np.nan, np.nan, 1, 2, 3, 4, 5, 6, np.nan, np.nan]),
            ("max", "left", [np.nan, np.nan, 1, 2, 3, 4, 5, 6, 6, np.nan]),
        ],
    )
    def test_closed_min_max_minp(self, func, closed, expected):
        # see gh-21704
        ser = pd.Series(data=np.arange(10), index=pd.date_range("2000", periods=10))
        ser[ser.index[-3:]] = np.nan
        result = getattr(ser.rolling("3D", min_periods=2, closed=closed), func)()
        expected = pd.Series(expected, index=ser.index)
        tm.assert_series_equal(result, expected)

    @pytest.mark.parametrize(
        "closed,expected",
        [
            ("right", [0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8]),
            ("both", [0, 0.5, 1, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]),
            ("neither", [np.nan, 0, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]),
            ("left", [np.nan, 0, 0.5, 1, 2, 3, 4, 5, 6, 7]),
        ],
    )
    def test_closed_median_quantile(self, closed, expected):
        # GH 26005
        ser = pd.Series(data=np.arange(10), index=pd.date_range("2000", periods=10))
        roll = ser.rolling("3D", closed=closed)
        expected = pd.Series(expected, index=ser.index)

        result = roll.median()
        tm.assert_series_equal(result, expected)

        result = roll.quantile(0.5)
        tm.assert_series_equal(result, expected)

    @pytest.mark.parametrize("roller", ["1s", 1])
    def tests_empty_df_rolling(self, roller):
        # GH 15819 Verifies that datetime and integer rolling windows can be
        # applied to empty DataFrames
        expected = DataFrame()
        result = DataFrame().rolling(roller).sum()
        tm.assert_frame_equal(result, expected)

        # Verifies that datetime and integer rolling windows can be applied to
        # empty DataFrames with datetime index
        expected = DataFrame(index=pd.DatetimeIndex([]))
        result = DataFrame(index=pd.DatetimeIndex([])).rolling(roller).sum()
        tm.assert_frame_equal(result, expected)

    def test_empty_window_median_quantile(self):
        # GH 26005
        expected = pd.Series([np.nan, np.nan, np.nan])
        roll = pd.Series(np.arange(3)).rolling(0)

        result = roll.median()
        tm.assert_series_equal(result, expected)

        result = roll.quantile(0.1)
        tm.assert_series_equal(result, expected)

    def test_missing_minp_zero(self):
        # https://github.com/pandas-dev/pandas/pull/18921
        # minp=0
        x = pd.Series([np.nan])
        result = x.rolling(1, min_periods=0).sum()
        expected = pd.Series([0.0])
        tm.assert_series_equal(result, expected)

        # minp=1
        result = x.rolling(1, min_periods=1).sum()
        expected = pd.Series([np.nan])
        tm.assert_series_equal(result, expected)

    def test_missing_minp_zero_variable(self):
        # https://github.com/pandas-dev/pandas/pull/18921
        x = pd.Series(
            [np.nan] * 4,
            index=pd.DatetimeIndex(
                ["2017-01-01", "2017-01-04", "2017-01-06", "2017-01-07"]
            ),
        )
        result = x.rolling(pd.Timedelta("2d"), min_periods=0).sum()
        expected = pd.Series(0.0, index=x.index)
        tm.assert_series_equal(result, expected)

    def test_multi_index_names(self):

        # GH 16789, 16825
        cols = pd.MultiIndex.from_product(
            [["A", "B"], ["C", "D", "E"]], names=["1", "2"]
        )
        df = DataFrame(np.ones((10, 6)), columns=cols)
        result = df.rolling(3).cov()

        tm.assert_index_equal(result.columns, df.columns)
        assert result.index.names == [None, "1", "2"]

    def test_rolling_axis_sum(self, axis_frame):
        # see gh-23372.
        df = DataFrame(np.ones((10, 20)))
        axis = df._get_axis_number(axis_frame)

        if axis == 0:
            expected = DataFrame({i: [np.nan] * 2 + [3.0] * 8 for i in range(20)})
        else:
            # axis == 1
            expected = DataFrame([[np.nan] * 2 + [3.0] * 18] * 10)

        result = df.rolling(3, axis=axis_frame).sum()
        tm.assert_frame_equal(result, expected)

    def test_rolling_axis_count(self, axis_frame):
        # see gh-26055
        df = DataFrame({"x": range(3), "y": range(3)})

        axis = df._get_axis_number(axis_frame)

        if axis in [0, "index"]:
            expected = DataFrame({"x": [1.0, 2.0, 2.0], "y": [1.0, 2.0, 2.0]})
        else:
            expected = DataFrame({"x": [1.0, 1.0, 1.0], "y": [2.0, 2.0, 2.0]})

        result = df.rolling(2, axis=axis_frame).count()
        tm.assert_frame_equal(result, expected)
