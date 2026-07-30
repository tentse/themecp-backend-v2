def get_rating_label(rating: int | None) -> str:
    """
    Return Codeforces-style rating label based on rating value.

    Args:
        rating: The user's last contest rating, or None if unrated (no contests)

    Returns:
        Label string (e.g. "Newbie", "Pupil", "Expert", "Unrated")
    """
    if rating is None:
        return "Unrated"
    if rating <= 1199:
        return "Newbie"
    if rating <= 1399:
        return "Pupil"
    if rating <= 1599:
        return "Specialist"
    if rating <= 1899:
        return "Expert"
    if rating <= 2099:
        return "Candidate Master"
    if rating <= 2299:
        return "Master"
    if rating <= 2399:
        return "International Master"
    if rating <= 2599:
        return "Grandmaster"
    if rating <= 2999:
        return "International Grandmaster"
    return "Legendary Grandmaster"
