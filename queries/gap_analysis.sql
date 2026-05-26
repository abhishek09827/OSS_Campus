-- Find repos the JD cares about with zero or thin contribution
SELECT
  jd.repo_name,
  jd.importance,
  jd.why_it_matters,
  COALESCE(my.merged_prs, 0)                    AS my_merged_prs,
  oi.open_issues_count                           AS available_issues,
  oi.good_first_issues                           AS good_first_issue_count

FROM jd_requirements.repos jd
LEFT JOIN (
  SELECT repo, COUNT(*) AS merged_prs
  FROM github.pull_requests
  WHERE author = '{github_username}' AND state = 'merged'
  GROUP BY repo
) my ON my.repo = jd.repo_name
LEFT JOIN (
  SELECT
    owner || '/' || repo                         AS full_repo,
    COUNT(*)                                     AS open_issues_count,
    COUNT(CASE WHEN 'good first issue' = ANY(labels)
               THEN 1 END)                       AS good_first_issues
  FROM github.issues
  WHERE state = 'open'
  GROUP BY owner, repo
) oi ON oi.full_repo = jd.repo_name

WHERE COALESCE(my.merged_prs, 0) < 3
ORDER BY jd.importance DESC;
