def split_test_count_across_policies(total: int, policies: list[str]) -> dict[str, int]:
    """An even split; the remainder goes to the first policies, so some may get 0."""
    share, remainder = divmod(total, len(policies))
    return {
        policy: share + (1 if index < remainder else 0)
        for index, policy in enumerate(policies)
    }
