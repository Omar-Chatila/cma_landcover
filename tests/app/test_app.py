import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import movingpandas as mpd

from app.app import App
from environmentcma import RangeType
from sdk.moveapps_io import MoveAppsIo
from tests.config.definitions import ROOT_DIR


class MyTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.sut = App(moveapps_io=MoveAppsIo())

    @staticmethod
    def _fixture(name):
        return pd.read_pickle(Path(ROOT_DIR) / "tests" / "resources" / "app" / name)

    def assert_input_schema_is_preserved(self, original, result):
        """Reusable MoveApp contract: extra columns are allowed, input schema is not changed."""
        original_gdf = original.to_point_gdf()
        result_gdf = result.to_point_gdf()

        self.assertEqual(original_gdf.index.name, result_gdf.index.name)
        self.assertEqual(original_gdf.index.dtype, result_gdf.index.dtype)
        self.assertEqual(original.get_crs(), result.get_crs())
        self.assertTrue(set(original_gdf.columns).issubset(result_gdf.columns))
        for column, expected_dtype in original_gdf.dtypes.items():
            self.assertEqual(
                expected_dtype,
                result_gdf[column].dtype,
                f"dtype changed for input column {column!r}",
            )

    def test_id_dtype_patch_handles_all_available_pickles(self):
        for pickle_path in sorted(Path(ROOT_DIR).rglob("*.pickle")):
            with self.subTest(pickle=pickle_path.name):
                original = pd.read_pickle(pickle_path)
                original_gdf = original.to_point_gdf()
                rebuilt = mpd.TrajectoryCollection(
                    original_gdf.copy(),
                    traj_id_col=original.get_traj_id_col(),
                    t=original_gdf.index.name,
                    crs=original.get_crs(),
                )

                id_column = original.get_traj_id_col()
                self.assertEqual(object, original_gdf[id_column].dtype)
                self.assertEqual(object, rebuilt.to_point_gdf()[id_column].dtype)

    @patch("app.app.annotate_study_pickle")
    def test_execute_preserves_input_schema_and_allows_added_columns(self, annotate):
        data = self._fixture("input4_LatLon.pickle")
        source = data.to_point_gdf().copy()
        source["landcover"] = 42
        annotate.return_value = mpd.TrajectoryCollection(
            source,
            traj_id_col=data.get_traj_id_col(),
            t=source.index.name,
            crs=data.get_crs(),
        )

        actual = self.sut.execute(
            data=data,
            config={
                "range_type": "local",
                "addUtm": "false",
                "keepGeoTiffs": "false",
            },
        )

        self.assert_input_schema_is_preserved(data, actual)
        self.assertIn("landcover", actual.to_point_gdf().columns)

    @patch("app.app.annotate_study_pickle")
    def test_long_range_study_is_annotated_without_an_artifact(self, annotate):
        data = self._fixture("input4_LatLon.pickle")
        annotate.return_value = data

        with tempfile.TemporaryDirectory() as artifacts_dir:
            with patch.dict(
                os.environ, {"APP_ARTIFACTS_DIR": artifacts_dir}, clear=False
            ):
                actual = self.sut.execute(
                    data=data,
                    config={
                        "range_type": "long_range",
                        "addUtm": "false",
                        "keepGeoTiffs": "false",
                    },
                )

            self.assertIs(actual, data)
            self.assertEqual([], list(Path(artifacts_dir).iterdir()))

        arguments = annotate.call_args.kwargs
        self.assertIs(arguments["trajectories"], data)
        self.assertEqual(RangeType.LONG_RANGE, arguments["range_type"])
        self.assertEqual(1000, arguments["resolution"])
        self.assertFalse(arguments["add_utm"])

    @patch("app.app.annotate_study_pickle")
    def test_all_generated_geotiffs_are_zipped(self, annotate):
        data = self._fixture("input2_LatLon.pickle")

        def create_test_outputs(**arguments):
            landcover_dir = Path(arguments["output_directory"]) / "landcover"
            nested_dir = landcover_dir / "nested"
            nested_dir.mkdir(parents=True)
            (landcover_dir / "animal-a.tif").write_bytes(b"first raster")
            (nested_dir / "animal-b.tiff").write_bytes(b"second raster")
            (landcover_dir / "animal-a_1000.txt").write_text(
                "10 80\n", encoding="utf-8"
            )
            return data

        annotate.side_effect = create_test_outputs

        with tempfile.TemporaryDirectory() as artifacts_dir:
            with patch.dict(
                os.environ, {"APP_ARTIFACTS_DIR": artifacts_dir}, clear=False
            ):
                actual = self.sut.execute(
                    data=data,
                    config={
                        "range_type": "local",
                        "addUtm": "true",
                        "keepGeoTiffs": "true",
                    },
                )

            archive_path = Path(artifacts_dir) / "tiffs.zip"
            self.assertTrue(archive_path.is_file())
            with ZipFile(archive_path) as archive:
                self.assertEqual(
                    [
                        "landcover/animal-a.tif",
                        "landcover/nested/animal-b.tiff",
                    ],
                    archive.namelist(),
                )
                self.assertEqual(
                    b"first raster", archive.read("landcover/animal-a.tif")
                )
                self.assertEqual(
                    b"second raster",
                    archive.read("landcover/nested/animal-b.tiff"),
                )

        self.assertIs(actual, data)
        arguments = annotate.call_args.kwargs
        self.assertEqual(RangeType.LOCAL, arguments["range_type"])
        self.assertTrue(arguments["add_utm"])


if __name__ == "__main__":
    unittest.main()
