import unittest

import router
from router import RouterOutput, route_query


class BrokenRouterChain:
    def invoke(self, _):
        raise RuntimeError("Error code: 400 invalid_request_error tool_use_failed")


class RouterFallbackTests(unittest.TestCase):
    def test_invalid_groq_tool_call_falls_back_to_structured_route(self):
        original_chain = router.router_chain
        router.router_chain = BrokenRouterChain()
        self.addCleanup(setattr, router, "router_chain", original_chain)

        result = route_query(
            "Which country had the highest number of political violence events in 2020?"
        )

        self.assertEqual(result.query_type, "STRUCTURED")
        self.assertEqual(result.date_from, "2020-01-01")
        self.assertEqual(result.date_to, "2020-12-31")
        self.assertEqual(result.disorder_type, "Political violence")

    def test_temporal_hybrid_ranking_intent_is_extracted(self):
        original_chain = router.router_chain
        router.router_chain = BrokenRouterChain()
        self.addCleanup(setattr, router, "router_chain", original_chain)

        month_result = route_query(
            "Which month had the most explosions or remote violence in Ukraine in 2022, and what happened during that period?"
        )
        year_result = route_query(
            "Tell me about the most dangerous year for civilians in Syria."
        )
        deadliest_month_result = route_query(
            "What was the deadliest month for civilians in Yemen in 2021?"
        )
        protest_year_result = route_query(
            "Which year had the most protests in Nigeria?"
        )

        self.assertEqual(month_result.query_type, "HYBRID")
        self.assertEqual(month_result.time_granularity, "month")
        self.assertEqual(month_result.ranking_metric, "events")
        self.assertEqual(year_result.query_type, "HYBRID")
        self.assertEqual(year_result.time_granularity, "year")
        self.assertEqual(year_result.ranking_metric, "fatalities")
        self.assertEqual(year_result.civilian_targeting, "Civilian targeting")
        self.assertEqual(deadliest_month_result.time_granularity, "month")
        self.assertEqual(deadliest_month_result.ranking_metric, "fatalities")
        self.assertEqual(protest_year_result.time_granularity, "year")
        self.assertEqual(protest_year_result.ranking_metric, "events")
        self.assertEqual(protest_year_result.query_type, "STRUCTURED")

    def test_requested_grouping_phrases_extract_actor_and_region_dimensions(self):
        original_chain = router.router_chain
        router.router_chain = BrokenRouterChain()
        self.addCleanup(setattr, router, "router_chain", original_chain)

        region_result = route_query(
            "Show the trend of events by region from 2015 to 2023."
        )
        actor_result = route_query(
            "Which armed groups were most active in the Middle East region?"
        )
        associated_actor_result = route_query(
            "Which armed group is most associated with 'Explosions/Remote violence'?"
        )

        self.assertEqual(region_result.query_type, "STRUCTURED")
        self.assertEqual(region_result.group_by, "region")
        self.assertEqual(region_result.region, None)
        self.assertEqual(actor_result.query_type, "STRUCTURED")
        self.assertEqual(actor_result.group_by, "actor1")
        self.assertEqual(actor_result.region, "Middle East")
        self.assertEqual(associated_actor_result.group_by, "actor1")
        self.assertEqual(
            associated_actor_result.event_type,
            "Explosions/Remote violence",
        )

    def test_complex_requested_questions_extract_comparisons_nested_dimensions_and_growth(self):
        original_chain = router.router_chain
        router.router_chain = BrokenRouterChain()
        self.addCleanup(setattr, router, "router_chain", original_chain)

        comparison = route_query(
            "Compare the sub-event distribution between two rival armed groups (e.g., ISIS and Boko Haram)."
        )
        nested = route_query(
            "Break down events by country within each region for 2021."
        )
        combination = route_query(
            "Which combination of country, actor, and sub-event type had the highest fatality count in 2020?"
        )
        region_comparison = route_query(
            "Compare political violence trends between two regions, broken down by actor type."
        )
        growth = route_query(
            "Which region-country-actor combination shows the fastest growth in events between 2019 and 2022?"
        )

        self.assertEqual(comparison.comparison_entities, ["ISIS", "Boko Haram"])
        self.assertEqual(comparison.comparison_dimension, "actor1")
        self.assertEqual(comparison.group_by_dimensions, ["sub_event_type"])
        self.assertEqual(nested.group_by_dimensions, ["region", "country"])
        self.assertEqual(
            combination.group_by_dimensions,
            ["country", "actor1", "sub_event_type"],
        )
        self.assertEqual(region_comparison.comparison_dimension, "region")
        self.assertEqual(region_comparison.group_by_dimensions, ["actor1"])
        self.assertEqual(growth.group_by_dimensions, ["region", "country", "actor1"])
        self.assertEqual(growth.growth_metric, "growth_pct")


if __name__ == "__main__":
    unittest.main()
