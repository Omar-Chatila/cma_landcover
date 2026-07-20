import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd

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
