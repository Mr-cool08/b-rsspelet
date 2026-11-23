from unittest import TestCase

from stockfight.ranking import STARTING_ELO, league_progress, rating_changes, search_radius


class RankingTests(TestCase):
    def test_equal_ratings(self):
        self.assertEqual(STARTING_ELO, 100)
        self.assertEqual(rating_changes(100, 100, 1), (116, 84))
        self.assertEqual(rating_changes(100, 100, 0.5), (100, 100))
        self.assertEqual(rating_changes(100, 100, 0), (84, 116))

    def test_lower_rated_player_gains_points_from_a_draw(self):
        self.assertEqual(rating_changes(100, 500, 0.5), (113, 487))
        self.assertEqual(rating_changes(500, 100, 0.5), (487, 113))

    def test_upset_conserves_total_and_is_independent_of_player_order(self):
        self.assertEqual(rating_changes(100, 500, 1), (129, 471))
        self.assertEqual(rating_changes(500, 100, 0), (471, 129))

    def test_half_point_rounds_away_from_zero(self):
        self.assertEqual(rating_changes(100, 100, 0.5 + 0.5 / 32), (101, 99))
        self.assertEqual(rating_changes(100, 100, 0.5 - 0.5 / 32), (99, 101))

    def test_league_thresholds(self):
        for elo, league in (
            (49, "Iron"),
            (50, "Bronze"),
            (149, "Bronze"),
            (150, "Silver"),
            (249, "Silver"),
            (250, "Gold"),
            (349, "Gold"),
            (350, "Platinum"),
            (499, "Platinum"),
            (500, "Diamond"),
            (649, "Diamond"),
            (650, "Master"),
            (799, "Master"),
            (800, "Grandmaster"),
            (899, "Grandmaster"),
            (900, "Stock Legend"),
        ):
            with self.subTest(elo=elo):
                self.assertEqual(league_progress(elo)["league"], league)

    def test_league_progress(self):
        self.assertEqual(league_progress(-1)["progress"], 0)
        self.assertEqual(
            league_progress(100),
            {"league": "Bronze", "nextLeague": "Silver", "nextElo": 150, "progress": 50},
        )
        self.assertEqual(
            league_progress(900),
            {"league": "Stock Legend", "nextLeague": None, "nextElo": None, "progress": 100},
        )

    def test_search_radius_expands_at_fifteen_seconds(self):
        self.assertEqual(search_radius(0), 100)
        self.assertEqual(search_radius(14.99), 100)
        self.assertEqual(search_radius(15), 200)
        self.assertEqual(search_radius(16), 200)
