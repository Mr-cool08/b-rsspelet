from unittest import TestCase

from stockfight.ranking import STARTING_ELO, league_progress, rating_changes, search_radius


class RankingTests(TestCase):
    def test_equal_ratings(self):
        self.assertEqual(STARTING_ELO, 1000)
        self.assertEqual(rating_changes(1000, 1000, 1), (1016, 984))
        self.assertEqual(rating_changes(1000, 1000, 0.5), (1000, 1000))
        self.assertEqual(rating_changes(1000, 1000, 0), (984, 1016))

    def test_lower_rated_player_gains_points_from_a_draw(self):
        self.assertEqual(rating_changes(1000, 1400, 0.5), (1013, 1387))
        self.assertEqual(rating_changes(1400, 1000, 0.5), (1387, 1013))

    def test_upset_conserves_total_and_is_independent_of_player_order(self):
        self.assertEqual(rating_changes(1000, 1400, 1), (1029, 1371))
        self.assertEqual(rating_changes(1400, 1000, 0), (1371, 1029))

    def test_half_point_rounds_away_from_zero(self):
        self.assertEqual(rating_changes(1000, 1000, 0.5 + 0.5 / 32), (1001, 999))
        self.assertEqual(rating_changes(1000, 1000, 0.5 - 0.5 / 32), (999, 1001))

    def test_league_thresholds(self):
        for elo, league in (
            (899, "Bronze"),
            (900, "Silver"),
            (1099, "Silver"),
            (1100, "Gold"),
            (1299, "Gold"),
            (1300, "Platinum"),
            (1499, "Platinum"),
            (1500, "Diamond"),
            (1799, "Diamond"),
            (1800, "Stock Legend"),
        ):
            with self.subTest(elo=elo):
                self.assertEqual(league_progress(elo)["league"], league)

    def test_league_progress(self):
        self.assertEqual(league_progress(-1)["progress"], 0)
        self.assertEqual(
            league_progress(1000),
            {"league": "Silver", "nextLeague": "Gold", "nextElo": 1100, "progress": 50},
        )
        self.assertEqual(
            league_progress(1800),
            {"league": "Stock Legend", "nextLeague": None, "nextElo": None, "progress": 100},
        )

    def test_search_radius_expands_at_fifteen_seconds(self):
        self.assertEqual(search_radius(0), 100)
        self.assertEqual(search_radius(14.99), 100)
        self.assertEqual(search_radius(15), 200)
        self.assertEqual(search_radius(16), 200)
