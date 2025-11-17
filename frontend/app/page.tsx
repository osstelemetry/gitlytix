import DashboardClient from "./dashboard-client";
import { calculateOsScore } from "../lib/scoring";
import {
  fetchReleaseData,
  fetchIssueData,
  fetchIssueTypeData,
  fetchDashboardMetrics,
  fetchNewContributors,
  type ReleaseDataEntry,
  type IssueDataEntry,
  type IssueTypeEntry,
  type DashboardMetrics
} from "../lib/api";

// Force dynamic rendering to prevent static generation during build
export const dynamic = 'force-dynamic';

export default async function Page() {
  const defaultRepo = "facebook/react";
  
  const [releaseData, issueData, issueTypeData, rawMetrics, newContributorsCount] = await Promise.all(
    [
      fetchReleaseData(defaultRepo),
      fetchIssueData(defaultRepo),
      fetchIssueTypeData(),
      fetchDashboardMetrics(defaultRepo),
      fetchNewContributors(defaultRepo)
    ]
  );

  const osScore = calculateOsScore(rawMetrics);

  return (
    <DashboardClient
      initialReleaseData={releaseData}
      initialIssueData={issueData}
      initialIssueTypeData={issueTypeData}
      score={osScore}
      firstResponseTime={rawMetrics.firstResponseTimeReadable}
      avgIssueResolution={rawMetrics.avgIssueResolutionReadable}
      prReviewTime={rawMetrics.prReviewTimeReadable}
      newContributors={newContributorsCount}
      bugFixRate={rawMetrics.bugFixResolutionReadable}
      defaultRepo={defaultRepo}
    />
  );
}
