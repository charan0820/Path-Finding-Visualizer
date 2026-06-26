
    def test_runtime_ms_non_negative(self, direct_graph):
        result = AStarPathfinder(direct_graph).find_path(0, 1)
        metrics = metrics_from_result(result, "A*", 0, 1)
        assert metrics.runtime_ms >= 0.0