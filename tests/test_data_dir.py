import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from biovector.bv_utils import Biovector


class TestRuntimeDataDirectory(unittest.TestCase):
    def setUp(self):
        self.original_data_dir = os.environ.get(Biovector.DATA_DIR_ENV_VAR)
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ[Biovector.DATA_DIR_ENV_VAR] = self.temp_dir.name

    def tearDown(self):
        if self.original_data_dir is None:
            os.environ.pop(Biovector.DATA_DIR_ENV_VAR, None)
        else:
            os.environ[Biovector.DATA_DIR_ENV_VAR] = self.original_data_dir
        self.temp_dir.cleanup()

    def test_bootstrap_seeds_runtime_data_directory(self):
        biovector = Biovector(selected=["sets", "exercises", "workouts", "weight"])

        self.assertFalse(biovector.sets.empty)
        self.assertFalse(biovector.exercises.empty)
        self.assertTrue(list(biovector.workouts.columns))
        self.assertTrue(list(biovector.weight.columns))

        data_root = Path(self.temp_dir.name) / "data"
        self.assertTrue((data_root / "sets.csv").exists())
        self.assertTrue((data_root / "exercises.csv").exists())
        self.assertTrue((data_root / "workouts.csv").exists())
        self.assertTrue((data_root / "weight.csv").exists())

    def test_dataset_path_uses_environment_directory(self):
        sets_path = Biovector.dataset_path("sets")
        self.assertTrue(str(sets_path).startswith(self.temp_dir.name))

    def test_additional_datasets_are_created(self):
        biovector = Biovector(selected=["cardio", "kettlebell", "imports", "ocr_notes"])
        self.assertEqual(
            list(biovector.cardio.columns),
            ["Timestamp", "Date", "Workout Name", "Type", "DurationSec", "DistanceKm", "AvgHeartRate", "Calories", "Notes"],
        )
        self.assertEqual(
            list(biovector.kettlebell.columns),
            ["Timestamp", "Date", "Workout Name", "Exercise", "WeightKg", "Reps", "Sets", "Style", "DurationSec", "Notes"],
        )
        self.assertEqual(
            list(biovector.imports.columns),
            ["Timestamp", "Source", "FilePath", "ImportedRows", "Status", "Notes"],
        )
        self.assertEqual(
            list(biovector.ocr_notes.columns),
            ["Timestamp", "SourceImage", "RawText", "ParsedType", "Confidence", "Status", "Notes"],
        )

    def test_import_records_from_csv(self):
        biovector = Biovector(selected=["cardio", "imports"])
        source_file = Path(self.temp_dir.name) / "incoming_cardio.csv"
        pd.DataFrame([
            {
                "Timestamp": 1.0,
                "Date": "2026-01-01 10:00:00",
                "Workout Name": "Morning Run",
                "Type": "run",
                "DurationSec": 1800,
                "DistanceKm": 5.2,
                "AvgHeartRate": 148,
                "Calories": 360,
                "Notes": "steady",
            }
        ]).to_csv(source_file, index=False)

        count = biovector.import_records_from_csv("garmin", str(source_file), "cardio")
        self.assertEqual(count, 1)

        cardio_df = pd.read_csv(Biovector.dataset_path("cardio"))
        imports_df = pd.read_csv(Biovector.dataset_path("imports"))
        self.assertEqual(len(cardio_df), 1)
        self.assertEqual(len(imports_df), 1)


if __name__ == "__main__":
    unittest.main()
