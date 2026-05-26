-- Find actionable good-first-issues in gap repos
SELECT
  owner || '/' || repo                           AS repo,
  number                                         AS issue_number,
  title                                          AS issue_title,
  html_url                                       AS issue_url,
  labels,
  created_at,
  comments                                       AS existing_comments

FROM github.issues

WHERE state = 'open'
  AND repo IN ({target_repos_csv})
  AND (
    'good first issue' = ANY(labels)
    OR 'help wanted' = ANY(labels)
  )
  AND comments < 5

ORDER BY created_at DESC
LIMIT 15;
