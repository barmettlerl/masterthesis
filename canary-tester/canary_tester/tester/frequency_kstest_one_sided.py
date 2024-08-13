import scipy as sp
import numpy as np
import logging

logger = logging.getLogger("root")


class FrequencyKSTestOneSided:
    """
    A class that calculates the confidence interval based on the Kolmogorov-Smirnov test.
    We use the [Dvoretzky–Kiefer–Wolfowitz inequality]
    (https://en.wikipedia.org/wiki/Dvoretzky%E2%80%93Kiefer%E2%80%93Wolfowitz_inequality).
    We only consider the one-sided test, such that A <= B in distribution.
    """

    def ci(A_bucket: list[float], B_bucket: list[float], alpha: float, avi=False):
        """
        Tests that A <= B in distribution.
        For the approach we've taken inspiration from Table 1 of the paper
        https://arxiv.org/abs/2205.14762.
        """
        n_a = len(A_bucket)
        n_b = len(B_bucket)

        res_a = sp.stats.ecdf(A_bucket)
        res_b = sp.stats.ecdf(B_bucket)
        a_y = res_a.cdf.probabilities
        a_x = res_a.cdf.quantiles
        b_y = res_b.cdf.probabilities
        b_x = res_b.cdf.quantiles

        F_u_a, F_u_b, F_l_a, F_l_b = FrequencyKSTestOneSided._calculate_bounds(
            a_x, a_y, b_x, b_y, n_a, n_b, alpha, avi
        )

        D_u = [F_u_b[i] - F_l_a[i] for i in range(len(F_u_b))]
        D_l = [F_l_b[i] - F_u_a[i] for i in range(len(F_l_b))]

        l_a_b = np.max([np.min(D_u), np.max(D_l)])
        u_a_b = np.max([np.min(D_l), np.max(D_u)])

        return l_a_b, u_a_b

    def p_value(A_bucket: list[float], B_bucket: list[float], avi=False):
        n_a = len(A_bucket)
        n_b = len(B_bucket)

        res_a = sp.stats.ecdf(A_bucket)
        res_b = sp.stats.ecdf(B_bucket)
        a_y = res_a.cdf.probabilities
        a_x = res_a.cdf.quantiles
        b_y = res_b.cdf.probabilities
        b_x = res_b.cdf.quantiles
        min, max = np.minimum(a_x[0], b_x[0]), np.maximum(a_x[-1], b_x[-1])
        sample_points = np.linspace(min, max, np.max([n_a, n_b]))
        D_ab = [
            np.maximum(
                FrequencyKSTestOneSided._interpolate_linear(b_x, b_y, p)
                - FrequencyKSTestOneSided._interpolate_linear(a_x, a_y, p),
                0,
            )
            for p in sample_points
        ]

        sup_D = np.linalg.norm(D_ab, np.inf)

        if avi is True:

            def p_bound(n):
                return 3624 / np.exp(
                    (n * (((sup_D / 2) / 0.85) ** 2) - np.log(np.log(np.e * n))) / 0.8
                )

        else:

            def p_bound(n):
                return 4 * np.exp(-n * sup_D**2 / 2)

        p_upper_bound = np.min([p_bound(np.minimum(n_a, n_b)), 1])
        p_lower_bound = np.min([p_bound(np.maximum(n_a, n_b)), 1])

        try:
            if avi:
                p_approx = sp.optimize.bisect(
                    lambda a: FrequencyKSTestOneSided.f_alpha_avi(sup_D, n_a, n_b, a),
                    p_lower_bound,
                    p_upper_bound,
                )
            else:
                p_approx = sp.optimize.bisect(
                    lambda a: FrequencyKSTestOneSided.f_alpha_gst(sup_D, n_a, n_b, a),
                    p_lower_bound,
                    p_upper_bound,
                )
        except ValueError as e:
            p_approx = p_upper_bound

        return p_approx

    def f_alpha_gst(d_plus_inf, n_a, n_b, alpha):
        return (
            d_plus_inf
            - FrequencyKSTestOneSided.error_fn_gst(n_a, alpha / 2)
            - FrequencyKSTestOneSided.error_fn_gst(n_b, alpha / 2)
        )

    def error_fn_gst(n, alpha):
        return np.sqrt(np.log(2 / alpha) / (2 * n))

    def f_alpha_avi(d_plus_inf, n_a, n_b, alpha):
        return (
            d_plus_inf
            - FrequencyKSTestOneSided.error_fn_avi(n_a, alpha / 2)
            - FrequencyKSTestOneSided.error_fn_avi(n_b, alpha / 2)
        )

    def error_fn_avi(n, alpha):
        return 0.85 * np.sqrt(
            (np.log(np.log(np.e * n)) + 0.8 * np.log(1612 / alpha)) / n
        )

    def _interpolate_linear(a_x, a_y, q):
        """
        Do linear interpolation between the two points that q is between.
        """
        # find the two points that q is between
        for i in range(0, len(a_x)):
            if q < a_x[i]:
                break
        i = i - 1

        if a_x[i] == a_x[i + 1]:
            return a_y[i]

        res = a_y[i] + (q - a_x[i]) * (a_y[i + 1] - a_y[i]) / (a_x[i + 1] - a_x[i])

        # interpolate between the two points
        return np.min([np.max([res, 0]), 1])

    def _error_fn(n, alpha, avi):
        """
        Building the error bounds based on the Dvoretzky–Kiefer–Wolfowitz inequality.
        """
        if n == 0 or alpha > 1 or alpha < 0:
            raise ValueError(
                "n should be greater than 0 and alpha should be between 0 and 1"
            )
        if avi:
            return FrequencyKSTestOneSided.error_fn_avi(n, alpha)
        else:
            return FrequencyKSTestOneSided.error_fn_gst(n, alpha)

    def _calculate_bounds(a_x, a_y, b_x, b_y, n_a, n_b, alpha, avi=False):
        """
        Calculate the upper and lower bound of distribution of A and B based
        on their empiric distribution, as described in
        [Two-sample Kolmogorov–Smirnov test]
        (https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test).
        """

        min, max = np.minimum(a_x[0], b_x[0]), np.maximum(a_x[-1], b_x[-1])
        sample_points = np.linspace(min, max, np.max([n_a, n_b]))
        F_u_a = [
            np.minimum(
                FrequencyKSTestOneSided._interpolate_linear(a_x, a_y, p)
                + FrequencyKSTestOneSided._error_fn(n_a, alpha / 2, avi),
                1,
            )
            for p in sample_points
        ]
        F_u_b = [
            np.minimum(
                FrequencyKSTestOneSided._interpolate_linear(b_x, b_y, p)
                + FrequencyKSTestOneSided._error_fn(n_b, alpha / 2, avi),
                1,
            )
            for p in sample_points
        ]
        F_l_a = [
            np.maximum(
                FrequencyKSTestOneSided._interpolate_linear(a_x, a_y, p)
                - FrequencyKSTestOneSided._error_fn(n_a, alpha / 2, avi),
                0,
            )
            for p in sample_points
        ]
        F_l_b = [
            np.maximum(
                FrequencyKSTestOneSided._interpolate_linear(b_x, b_y, p)
                - FrequencyKSTestOneSided._error_fn(n_b, alpha / 2, avi),
                0,
            )
            for p in sample_points
        ]

        return F_u_a, F_u_b, F_l_a, F_l_b
