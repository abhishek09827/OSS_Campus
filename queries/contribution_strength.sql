-- Parameterised: {github_username}
-- Returns contribution strength per repo
SELECT
  r.full_name                                    AS repo,
  COUNT(CASE WHEN pr.state = 'merged'
             THEN 1 END)                        AS merged_prs,
  COUNT(CASE WHEN pr.state = 'closed'
             AND pr.merged_at IS NULL
             THEN 1 END)                        AS closed_unmerged,
  COUNT(DISTINCT pr.number)                      AS total_prs,
  ROUND(
    COUNT(CASE WHEN pr.state = 'merged' THEN 1 END) * 100.0
    / NULLIF(COUNT(DISTINCT pr.number), 0), 2
  )                                              AS merge_rate_pct,
  MAX(pr.merged_at)                              AS last_merged_at

FROM github.pull_requests pr
JOIN github.repos r ON r.full_name = pr.repo

WHERE pr.author = '{github_username}'
  AND pr.created_at >= CURRENT_DATE - INTERVAL '12 months'

GROUP BY r.full_name
HAVING COUNT(CASE WHEN pr.state = 'merged' THEN 1 END) > 0
ORDER BY merged_prs DESC;
