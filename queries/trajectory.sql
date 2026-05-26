-- Contribution velocity over last 12 months
SELECT
  TO_CHAR(DATE_TRUNC('month', merged_at), 'YYYY-MM') AS month,
  COUNT(*)                                            AS merged_prs,
  COUNT(DISTINCT repo)                                AS repos_contributed_to

FROM github.pull_requests

WHERE author = '{github_username}'
  AND state = 'merged'
  AND merged_at >= CURRENT_DATE - INTERVAL '12 months'

GROUP BY DATE_TRUNC('month', merged_at)
ORDER BY month ASC;
