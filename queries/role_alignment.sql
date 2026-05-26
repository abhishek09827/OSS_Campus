-- Parameterised: {github_username}, {target_repos_csv}
-- Cross-join GitHub activity with JD requirements file
SELECT
  jd.repo_name                                   AS required_repo,
  jd.importance                                  AS jd_importance,
  COALESCE(pr_counts.merged_prs, 0)              AS my_merged_prs,
  COALESCE(pr_counts.merge_rate_pct, 0)          AS my_merge_rate,
  CASE
    WHEN COALESCE(pr_counts.merged_prs, 0) = 0 THEN 1.0
    WHEN pr_counts.merged_prs < 2             THEN 0.6
    WHEN pr_counts.merged_prs < 5             THEN 0.3
    ELSE 0.0
  END                                            AS gap_score

FROM jd_requirements.repos jd
LEFT JOIN (
  SELECT
    repo,
    COUNT(*)                                     AS merged_prs,
    ROUND(COUNT(*) * 100.0 /
      NULLIF(COUNT(*) + COUNT(CASE WHEN state = 'closed'
                                   AND merged_at IS NULL
                                   THEN 1 END), 0), 2) AS merge_rate_pct
  FROM github.pull_requests
  WHERE author = '{github_username}'
    AND state = 'merged'
  GROUP BY repo
) pr_counts ON pr_counts.repo = jd.repo_name

ORDER BY jd.importance DESC, gap_score DESC;
