import unittest
from datetime import date
from unittest.mock import patch

from pyspark.sql import Row, SparkSession

import structured
from router import RouterOutput


class StructuredAggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (
            SparkSession.builder
            .master("local[2]")
            .appName("StructuredAggregationTests")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
        cls.dataframe = cls.spark.createDataFrame(
            [
                Row(country="Alpha", region="North", event_date=date(2020, 1, 5), fatalities=3, event_type="Battles", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="North", event_date=date(2020, 2, 5), fatalities=2, event_type="Battles", civilian_targeting="Civilian targeting"),
                Row(country="Beta", region="South", event_date=date(2020, 1, 5), fatalities=9, event_type="Battles", civilian_targeting="Civilian targeting"),
                Row(country="Beta", region="South", event_date=date(2020, 3, 5), fatalities=1, event_type="Protests", civilian_targeting="Not civilian targeting"),
            ]
        )
        structured.get_spark_session = lambda: cls.spark
        structured.load_structured_df = lambda spark: cls.dataframe

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_country_and_region_rankings_use_same_aggregation_path(self):
        region_result = structured.run_structured_query(
            RouterOutput(query_type="STRUCTURED"),
            "Which region had the highest number of battles in 2020?",
        )
        country_result = structured.run_structured_query(
            RouterOutput(query_type="STRUCTURED"),
            "Which country had the highest number of battles in 2020?",
        )

        self.assertIn("The top regions by event count were:", region_result["text"])
        self.assertIn("1. North: 2 events", region_result["text"])
        self.assertIn("The top countries by event count were:", country_result["text"])
        self.assertIn("1. Alpha: 2 events", country_result["text"])
        self.assertNotIn("ERROR", region_result["text"])
        self.assertNotIn("ERROR", country_result["text"])

    def test_country_and_region_fatality_rankings_sum_fatalities(self):
        region_result = structured.run_structured_query(
            RouterOutput(query_type="STRUCTURED", event_type="Battles"),
            "Which region had the highest number of fatalities from battles in 2020?",
        )
        country_result = structured.run_structured_query(
            RouterOutput(query_type="STRUCTURED", event_type="Battles"),
            "Which country had the highest number of fatalities from battles in 2020?",
        )

        self.assertIn("1. South: 9 fatalities", region_result["text"])
        self.assertIn("1. Beta: 9 fatalities", country_result["text"])

    def test_country_filter_event_type_and_date_range(self):
        result = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                country="Alpha",
                date_from="2020-01-01",
                date_to="2020-12-31",
                event_type="Battles",
            ),
            "How many fatalities occurred in country Alpha between 2020-01-01 and 2020-12-31?",
        )

        self.assertIn("Alpha (5)", result["text"])

    def test_political_violence_region_ranking_is_numbered(self):
        dataframe = self.spark.createDataFrame(
            [
                Row(country="Alpha", region="North", event_date=date(2020, 1, 1), fatalities=1, event_type="Battles", disorder_type="Political violence"),
                Row(country="Beta", region="South", event_date=date(2020, 1, 1), fatalities=2, event_type="Battles", disorder_type="Political violence"),
                Row(country="Beta", region="South", event_date=date(2020, 2, 1), fatalities=1, event_type="Battles", disorder_type="Political violence"),
            ]
        )
        original_dataframe = self.__class__.dataframe
        self.__class__.dataframe = dataframe
        self.addCleanup(setattr, self.__class__, "dataframe", original_dataframe)

        result = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                date_from="2020-01-01",
                date_to="2020-12-31",
                disorder_type="Political violence",
                group_by="region",
                ranking_metric="events",
            ),
            "Which region had the highest number of political violence events in 2020?",
        )

        self.assertIn("The top regions by event count in 2020 were:", result["text"])
        self.assertIn("1. South: 2 events", result["text"])
        self.assertIn("2. North: 1 event", result["text"])

    def test_temporal_aggregation_is_available_with_country_filter(self):
        result = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                country="Alpha",
                date_from="2020-01-01",
                date_to="2020-12-31",
                event_type="Battles",
            ),
            "What is the monthly trend of battles in country Alpha in 2020?",
        )

        self.assertIn("2020-01 (1)", result["text"])
        self.assertIn("2020-02 (1)", result["text"])

    def test_temporal_ranking_returns_complete_series_and_winner(self):
        result = structured.run_structured_query(
            RouterOutput(
                query_type="HYBRID",
                country="Alpha",
                date_from="2020-01-01",
                date_to="2020-12-31",
                event_type="Battles",
                time_granularity="month",
                ranking_metric="events",
            ),
            "Which month had the most battles in Alpha in 2020?",
        )

        self.assertEqual(result["chart"]["labels"], ["2020-01", "2020-02"])
        self.assertEqual(result["ranking"]["winner"], "2020-01")
        self.assertEqual(result["chart"]["highlighted_label"], "2020-01")

    def test_deadliest_temporal_ranking_sums_fatalities(self):
        result = structured.run_structured_query(
            RouterOutput(
                query_type="HYBRID",
                country="Alpha",
                civilian_targeting="Civilian targeting",
                time_granularity="year",
                ranking_metric="fatalities",
            ),
            "What was the deadliest year for civilians in Alpha?",
        )

        self.assertEqual(result["chart"]["values"], [5])
        self.assertEqual(result["ranking"]["metric"], "fatalities")

    def test_requested_questions_return_consistent_text_buckets_and_charts(self):
        dataframe = self.spark.createDataFrame(
            [
                Row(country="Alpha", region="Middle East", event_date=date(2015, 1, 1), fatalities=1, event_type="Battles", sub_event_type="Armed clash", actor1="Group A", actor2="Group B", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="Middle East", event_date=date(2018, 1, 1), fatalities=2, event_type="Battles", sub_event_type="Armed clash", actor1="Group A", actor2="Group B", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="Middle East", event_date=date(2019, 1, 1), fatalities=3, event_type="Battles", sub_event_type="Armed clash", actor1="Group B", actor2="Group A", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="Middle East", event_date=date(2020, 1, 1), fatalities=4, event_type="Explosions/Remote violence", sub_event_type="Attack", actor1="Group B", actor2="Group C", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="Middle East", event_date=date(2021, 1, 1), fatalities=5, event_type="Battles", sub_event_type="Armed clash", actor1="Group C", actor2="Group A", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="Middle East", event_date=date(2022, 1, 1), fatalities=6, event_type="Battles", sub_event_type="Armed clash", actor1="Group C", actor2="Group B", civilian_targeting="Civilian targeting"),
                Row(country="Alpha", region="Middle East", event_date=date(2023, 1, 1), fatalities=7, event_type="Battles", sub_event_type="Armed clash", actor1="Group C", actor2="Group B", civilian_targeting="Civilian targeting"),
                Row(country="Beta", region="North", event_date=date(2015, 1, 1), fatalities=1, event_type="Battles", sub_event_type="Armed clash", actor1="Group A", actor2="Group C", civilian_targeting="Not civilian targeting"),
            ]
        )
        original_dataframe = self.__class__.dataframe
        self.__class__.dataframe = dataframe
        self.addCleanup(setattr, self.__class__, "dataframe", original_dataframe)

        questions = [
            "How many sub-events are classified as 'Battles'?",
            "How did the number of events change year over year between 2018 and 2022?",
            "Show the trend of events by region from 2015 to 2023.",
            "Which armed groups were most active in the Middle East region?",
            "Which armed group is most associated with 'Explosions/Remote violence'?",
        ]
        with patch.object(
            structured,
            "_generate_breakdown_commentary",
            side_effect=lambda rows, label, metric, dimension, question: (
                "The aggregate pattern has a clear maximum and minimum."
                if len(rows) > 1 else ""
            ),
        ):
            answers = [
                structured.run_structured_query(
                    RouterOutput(query_type="STRUCTURED", event_type="Battles"),
                    questions[0],
                ),
                structured.run_structured_query(
                    RouterOutput(query_type="STRUCTURED", date_from="2018-01-01", date_to="2022-12-31", group_by="year"),
                    questions[1],
                ),
                structured.run_structured_query(
                    RouterOutput(query_type="STRUCTURED", date_from="2015-01-01", date_to="2023-12-31", group_by="region"),
                    questions[2],
                ),
                structured.run_structured_query(
                    RouterOutput(query_type="STRUCTURED", region="Middle East", group_by="actor1"),
                    questions[3],
                ),
                structured.run_structured_query(
                    RouterOutput(query_type="STRUCTURED", event_type="Explosions/Remote violence", group_by="actor1"),
                    questions[4],
                ),
            ]

        self.assertIn("7 battles", answers[0]["text"])
        self.assertEqual(
            answers[0]["chart"]["labels"],
            ["2015", "2018", "2019", "2021", "2022", "2023"],
        )
        self.assertEqual(answers[0]["chart"]["values"], [2, 1, 1, 1, 1, 1])
        self.assertIn("2018 (1)", answers[1]["text"])
        self.assertIn("2022 (1)", answers[1]["text"])
        self.assertIn("clear maximum", answers[1]["text"])
        self.assertEqual(answers[1]["chart"]["labels"], ["2018", "2019", "2020", "2021", "2022"])
        self.assertEqual(answers[2]["chart"]["labels"], ["Middle East", "North"])
        self.assertEqual(answers[2]["chart"]["values"], [7, 1])
        self.assertEqual(answers[3]["chart"]["labels"], ["Group C", "Group A", "Group B"])
        self.assertEqual(answers[3]["chart"]["values"], [3, 2, 2])
        self.assertIn("The top armed groups by event count in Middle East were:", answers[3]["text"])
        self.assertIn("1. Group C: 3 events", answers[3]["text"])
        self.assertEqual(answers[4]["chart"]["labels"], ["Group B"])
        self.assertEqual(answers[4]["chart"]["values"], [1])

    def test_comparison_nested_and_growth_questions_return_complete_structures(self):
        dataframe = self.spark.createDataFrame(
            [
                Row(country="Iraq", region="Middle East", event_date=date(2020, 1, 1), fatalities=5, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="ISIS"),
                Row(country="Iraq", region="Middle East", event_date=date(2020, 2, 1), fatalities=2, event_type="Battles", disorder_type="Political violence", sub_event_type="Attack", actor1="ISIS"),
                Row(country="Nigeria", region="Western Africa", event_date=date(2020, 1, 1), fatalities=3, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Boko Haram"),
                Row(country="Nigeria", region="Western Africa", event_date=date(2020, 2, 1), fatalities=4, event_type="Battles", disorder_type="Political violence", sub_event_type="Attack", actor1="Boko Haram"),
                Row(country="Syria", region="Middle East", event_date=date(2021, 1, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="ISIS"),
                Row(country="Lebanon", region="Middle East", event_date=date(2021, 1, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Attack", actor1="Boko Haram"),
                Row(country="Iraq", region="Middle East", event_date=date(2019, 1, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group A"),
                Row(country="Iraq", region="Middle East", event_date=date(2022, 1, 1), fatalities=5, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group A"),
                Row(country="Iraq", region="Middle East", event_date=date(2022, 2, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group A"),
                Row(country="Iraq", region="Middle East", event_date=date(2022, 3, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group A"),
                Row(country="Iraq", region="Middle East", event_date=date(2022, 4, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group A"),
                Row(country="Iraq", region="Middle East", event_date=date(2022, 5, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group A"),
                Row(country="Syria", region="Middle East", event_date=date(2019, 1, 1), fatalities=1, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group B"),
                Row(country="Syria", region="Middle East", event_date=date(2022, 1, 1), fatalities=2, event_type="Battles", disorder_type="Political violence", sub_event_type="Armed clash", actor1="Group B"),
            ]
        )
        original_dataframe = self.__class__.dataframe
        self.__class__.dataframe = dataframe
        self.addCleanup(setattr, self.__class__, "dataframe", original_dataframe)

        comparison = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                comparison_entities=["ISIS", "Boko Haram"],
                comparison_dimension="actor1",
                group_by_dimensions=["sub_event_type"],
            ),
            "Compare the sub-event distribution between two rival armed groups (e.g., ISIS and Boko Haram).",
        )
        nested = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                date_from="2021-01-01",
                date_to="2021-12-31",
                group_by_dimensions=["region", "country"],
            ),
            "Break down events by country within each region for 2021.",
        )
        combination = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                date_from="2020-01-01",
                date_to="2020-12-31",
                ranking_metric="fatalities",
                group_by_dimensions=["country", "actor1", "sub_event_type"],
            ),
            "Which combination of country, actor, and sub-event type had the highest fatality count in 2020?",
        )
        region_comparison = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                disorder_type="Political violence",
                comparison_entities=["Middle East", "Western Africa"],
                comparison_dimension="region",
                group_by_dimensions=["actor1"],
            ),
            "Compare political violence trends between two regions, broken down by actor type.",
        )
        growth = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                date_from="2019-01-01",
                date_to="2022-12-31",
                group_by_dimensions=["region", "country", "actor1"],
                growth_metric="growth_pct",
            ),
            "Which region-country-actor combination shows the fastest growth in events between 2019 and 2022?",
        )
        missing_entities = structured.run_structured_query(
            RouterOutput(
                query_type="STRUCTURED",
                group_by_dimensions=["sub_event_type"],
            ),
            "Compare the sub-event distribution between two rival armed groups.",
        )

        self.assertEqual(comparison["chart"]["chart_type"], "grouped_bar")
        self.assertEqual(comparison["chart"]["labels"], ["Armed clash", "Attack"])
        comparison_series = {
            series["label"]: series["values"]
            for series in comparison["chart"]["series"]
        }
        self.assertEqual(comparison_series["ISIS"], [2, 1])
        self.assertEqual(comparison_series["Boko Haram"], [1, 2])
        self.assertIn("ISIS", comparison["text"])
        self.assertEqual(nested["dimensions"], ["region", "country"])
        self.assertEqual(len(nested["rows"]), 2)
        self.assertEqual(nested["chart"]["labels"], ["Middle East | Lebanon", "Middle East | Syria"])
        self.assertIn("The top combinations of region and country by event count in 2021 were:", nested["text"])
        self.assertIn("1. Middle East — Lebanon: 1 event", nested["text"])
        self.assertEqual(combination["dimensions"], ["country", "actor1", "sub_event_type"])
        self.assertEqual(combination["rows"][0]["fatalities"], 5)
        self.assertIn(
            "The top combinations of country, actor, and sub-event type by fatality count in 2020 were:",
            combination["text"],
        )
        self.assertIn("1. Iraq — ISIS — Armed clash: 5 fatalities", combination["text"])
        self.assertNotIn("=", combination["text"])
        self.assertNotIn(" + ", combination["text"])
        self.assertEqual(region_comparison["chart"]["chart_type"], "grouped_bar")
        self.assertEqual(
            region_comparison["chart"]["labels"],
            ["Boko Haram", "Group A", "Group B", "ISIS"],
        )
        self.assertEqual(growth["rows"][0]["growth_pct"], 400.0)
        self.assertEqual(growth["dimensions"], ["region", "country", "actor1"])
        self.assertIn("1. Middle East — Iraq — Group A:", growth["text"])
        self.assertTrue(missing_entities["needs_clarification"])
        self.assertIsNone(missing_entities["chart"])


if __name__ == "__main__":
    unittest.main()
