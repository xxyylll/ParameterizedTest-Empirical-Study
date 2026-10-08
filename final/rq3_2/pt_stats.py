#!/usr/bin/env python3
"""
Shared non-parametric statistics for the RQ3.x analyses, implemented in pure
Python so the numbers stay consistent with the RQ3.1 heatmap pipeline
(heatmap_unified_44projects.py), which hand-rolls the same Mann-Whitney U /
Cliff's delta.

Used by rq3_2_methodsource/, rq3_3_cross_source/ and rq3_4_enumsource/.
Validated against scipy/statsmodels to machine precision.
"""
import math


# --- Mann-Whitney U + Cliff's delta (identical to the RQ3.1 implementation) ---
def mann_whitney_u(group1, group2):
    """Two-sided Mann-Whitney U with tie-corrected normal approximation and a
    continuity correction. Returns (cliffs_delta, p). Positive delta means
    group1 tends to be larger."""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return float('nan'), float('nan')
    N = n1 + n2
    combined = [(x, 1) for x in group1] + [(x, 2) for x in group2]
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * N
    i = 0
    tie_term_sum = 0
    while i < N:
        j = i
        while j + 1 < N and combined[j + 1][0] == combined[i][0]:
            j += 1
        tie_size = j - i + 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        if tie_size > 1:
            tie_term_sum += tie_size ** 3 - tie_size
        i = j + 1
    R1 = sum(r for r, (val, grp) in zip(ranks, combined) if grp == 1)
    U1 = R1 - n1 * (n1 + 1) / 2.0
    mean_U = n1 * n2 / 2.0
    var_U = (n1 * n2 / 12.0) * ((N + 1) - tie_term_sum / (N * (N - 1))) if N > 1 else 0.0
    sigma_U = math.sqrt(var_U) if var_U > 0 else 0.0
    if sigma_U == 0:
        z = 0.0
    else:
        z = (U1 - 0.5 - mean_U) / sigma_U if U1 > mean_U else ((U1 + 0.5 - mean_U) / sigma_U if U1 < mean_U else 0.0)
    p = max(0.0, min(1.0, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))))
    cliffs_delta = (2 * U1) / (n1 * n2) - 1
    return cliffs_delta, p


def cliffs_magnitude(delta):
    """Romano et al. thresholds, the same bands the RQ3.1 heatmap colours use."""
    if delta != delta:  # nan
        return 'n/a'
    d = abs(delta)
    if d < 0.147:
        return 'negligible'
    if d < 0.330:
        return 'small'
    if d < 0.474:
        return 'medium'
    return 'large'


# --- regularized upper incomplete gamma -> chi-square survival function ---
def _gser(a, x, itmax=500, eps=3.0e-14):
    """Series expansion for the regularized lower incomplete gamma P(a, x)."""
    if x <= 0:
        return 0.0
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(itmax):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * eps:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a, x, itmax=500, eps=3.0e-14, fpmin=1e-300):
    """Continued fraction for the regularized upper incomplete gamma Q(a, x)."""
    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b
    h = d
    for i in range(1, itmax + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def gammq(a, x):
    """Regularized upper incomplete gamma Q(a, x) = 1 - P(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError('gammq: invalid arguments')
    if x == 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)


def chi2_sf(x, df):
    """Upper-tail probability of the chi-square distribution."""
    if x <= 0:
        return 1.0
    return max(0.0, min(1.0, gammq(df / 2.0, x / 2.0)))


# --- Kruskal-Wallis H ---
def kruskal_wallis(groups):
    """Tie-corrected Kruskal-Wallis H for >=2 groups (list of lists).
    Returns (H, df, p)."""
    groups = [g for g in groups if len(g) > 0]
    k = len(groups)
    if k < 2:
        return float('nan'), 0, float('nan')
    combined = []
    for gi, g in enumerate(groups):
        combined.extend((x, gi) for x in g)
    N = len(combined)
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * N
    i = 0
    tie_term_sum = 0
    while i < N:
        j = i
        while j + 1 < N and combined[j + 1][0] == combined[i][0]:
            j += 1
        tie_size = j - i + 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for m in range(i, j + 1):
            ranks[m] = avg_rank
        if tie_size > 1:
            tie_term_sum += tie_size ** 3 - tie_size
        i = j + 1
    rank_sums = [0.0] * k
    for r, (val, gi) in zip(ranks, combined):
        rank_sums[gi] += r
    H = 12.0 / (N * (N + 1)) * sum(rs * rs / len(g) for rs, g in zip(rank_sums, groups)) - 3.0 * (N + 1)
    tie_corr = 1.0 - tie_term_sum / float(N ** 3 - N) if N > 1 else 1.0
    if tie_corr > 0:
        H /= tie_corr
    df = k - 1
    return H, df, chi2_sf(H, df)


# --- multiple-comparison corrections ---
def holm_adjust(pvals):
    """Holm-Bonferroni step-down adjusted p-values (FWER), order preserved."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running = max(running, val)
        adj[idx] = min(1.0, running)
    return adj


def bh_adjust(pvals):
    """Benjamini-Hochberg adjusted p-values (FDR q), order preserved."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i], reverse=True)
    adj = [0.0] * m
    running = 1.0
    for rank, idx in enumerate(order):
        k = m - rank  # rank of this p-value in ascending order
        val = pvals[idx] * m / k
        running = min(running, val)
        adj[idx] = min(1.0, running)
    return adj


# --- descriptives ---
def quantile(sorted_vals, q):
    """Linear-interpolation quantile (numpy's default 'linear' method)."""
    n = len(sorted_vals)
    if n == 0:
        return float('nan')
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def describe(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return {'n': 0, 'mean': float('nan'), 'median': float('nan'),
                'q1': float('nan'), 'q3': float('nan'), 'iqr': float('nan')}
    q1 = quantile(s, 0.25)
    q3 = quantile(s, 0.75)
    return {'n': n, 'mean': sum(s) / n, 'median': quantile(s, 0.5),
            'q1': q1, 'q3': q3, 'iqr': q3 - q1}


def describe_full(vals):
    """Full distributional summary. Reported alongside the median because the
    reuse and complexity distributions here are heavy-tailed and strongly
    right-skewed, where a central-tendency number on its own misleads: the
    percentile ladder and the tail shares are what carry the shape."""
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return {k: float('nan') for k in
                ('n', 'mean', 'sd', 'min', 'p5', 'q1', 'median', 'q3',
                 'p90', 'p95', 'p99', 'max', 'iqr', 'cv', 'mean_median_ratio')} | {'n': 0}
    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    med = quantile(s, 0.5)
    q1, q3 = quantile(s, 0.25), quantile(s, 0.75)
    return {'n': n, 'mean': mean, 'sd': sd, 'min': s[0],
            'p5': quantile(s, 0.05), 'q1': q1, 'median': med, 'q3': q3,
            'p90': quantile(s, 0.90), 'p95': quantile(s, 0.95),
            'p99': quantile(s, 0.99), 'max': s[-1], 'iqr': q3 - q1,
            'cv': sd / mean if mean else float('nan'),
            'mean_median_ratio': mean / med if med else float('nan')}


def share_at_most(vals, threshold):
    """Fraction of values <= threshold (for reporting tail mass explicitly)."""
    if not vals:
        return float('nan')
    return sum(1 for v in vals if v <= threshold) / len(vals)


def share_at_least(vals, threshold):
    if not vals:
        return float('nan')
    return sum(1 for v in vals if v >= threshold) / len(vals)


def cohens_kappa(pairs):
    """Cohen's kappa for a list of (rater_a_label, rater_b_label) pairs.
    Returns (kappa, observed_agreement, expected_agreement, n)."""
    n = len(pairs)
    if n == 0:
        return float('nan'), float('nan'), float('nan'), 0
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    po = sum(1 for a, b in pairs if a == b) / n
    count_a = {l: sum(1 for a, _ in pairs if a == l) for l in labels}
    count_b = {l: sum(1 for _, b in pairs if b == l) for l in labels}
    pe = sum((count_a[l] / n) * (count_b[l] / n) for l in labels)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return kappa, po, pe, n


def _rankdata(vals):
    """Average ranks, ties shared (the same convention the U test uses)."""
    n = len(vals)
    order = sorted(range(n), key=lambda i: vals[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(x, y):
    """Spearman rank correlation with tie-corrected ranks.
    Returns (rho, p) using the t approximation; p is unreliable for n < 10."""
    n = len(x)
    if n != len(y):
        raise ValueError('spearman: length mismatch')
    if n < 3:
        return float('nan'), float('nan')
    rx, ry = _rankdata(x), _rankdata(y)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx <= 0 or syy <= 0:
        return float('nan'), float('nan')
    rho = sxy / math.sqrt(sxx * syy)
    rho = max(-1.0, min(1.0, rho))
    if abs(rho) >= 1.0 or n <= 2:
        return rho, 0.0
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    # two-sided p from the t distribution via the incomplete beta identity
    df = n - 2
    x_ = df / (df + t * t)
    p = _betai(df / 2.0, 0.5, x_)
    return rho, max(0.0, min(1.0, p))


def _betacf(a, b, x, itmax=300, eps=3.0e-14, fpmin=1e-300):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b
