class WeightService:
    """Per-channel weight in the composite danger score.

    Weights reflect operational priority: dp_kp_oo (контайнмент —
    критичний показник герметичності) gets the largest single share,
    secondary diff channels vote together, GU walls/gaps show containment
    integrity, σ channels capture turbulence. Total ≈ 1.00.
    """

    CHANNEL_WEIGHTS: dict[str, float] = {
        # primary safety channels
        "dp_kp_oo":              0.13,
        "pressure_kp":           0.10,
        "pressure_oo":           0.08,
        "flow_kp_in":            0.06,
        "flow_oo_out":           0.06,

        # secondary differential channels
        "dp_kp_os":              0.04,
        "dp_oo_os_8":            0.04,
        "dp_oo_os_9":            0.04,
        "dp_kp_oo_by":           0.04,
        "dp_kp_oo_bz":           0.04,
        "dp_kp_oo_ca":           0.04,
        "flow_oo_in":            0.02,

        # GU containment integrity
        "gu_pressure_west_wall": 0.04,
        "gu_pressure_east_wall": 0.04,
        "gu_pressure_cyl_wall":  0.03,
        "gu_pressure_west_gap":  0.03,
        "gu_pressure_east_gap":  0.03,
        "gu_pressure_vsro":      0.03,

        # turbulence proxies (СКО тиску)
        "gu_sigma_008":          0.02,
        "gu_sigma_009":          0.02,
        "gu_sigma_kp_os":        0.02,

        # environmental
        "wind_speed":            0.04,
    }

    @classmethod
    def for_channels(cls, channels: list[str]) -> dict[str, float]:
        """Return weights for the subset of channels present in the dataset."""
        return {c: cls.CHANNEL_WEIGHTS[c] for c in channels if c in cls.CHANNEL_WEIGHTS}

    @classmethod
    def known_channels(cls) -> set[str]:
        return set(cls.CHANNEL_WEIGHTS) | {"wind_direction", "air_density"}
