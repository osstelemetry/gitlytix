// Shared API utility functions for data fetching

// Define interfaces for the data structures
export interface ReleaseDataEntry {
  month: string;
  releases: number;
}

export interface IssueDataEntry {
  month: string;
  opened: number;
  closed: number;
}

export interface IssueTypeEntry {
  name: string;
  value: number;
}

export interface IssuesOpenClosedResponse {
  repository: string;
  data: { month: string; opened: number; closed: number }[];
}

export interface DashboardMetrics {
  firstResponseTimeReadable: number;
  avgIssueResolutionReadable: number;
  prReviewTimeReadable: number;
  firstResponseTimeSeconds: number;
  avgIssueResolutionSeconds: number;
  prReviewTimeSeconds: number;
}

// Interface for the PR Review Time API response
export interface PrReviewTimeResponse {
  average_review_time_seconds: number;
  average_review_time_readable: number;
}

// Interface for the First Response Time API response
export interface IssueFirstResponseTimeResponse {
  average_response_time_seconds: number;
  average_response_time_readable: number;
}

// Interface for the Avg Issue Resolution Time API response
export interface IssueAvgResolutionTimeResponse {
  average_resolution_time_seconds: number;
  average_resolution_time_readable: number;
}

export interface NewContributors {
  new_contributors_count: number;
}

function getApiBaseUrl(): string {
  const isServer = typeof window === 'undefined';
  
  if (isServer) {
    // Server-side: use Docker network hostname
    return process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
  } else {
    // Client-side: use localhost 
    return "http://localhost:8000";
  }
}

// Generic data fetching function
export async function fetchData<T>(
  url: string,
  mockData: T,
  delay: number = 500
): Promise<T> {
  const API_BASE_URL = getApiBaseUrl();
  const fullUrl = API_BASE_URL + url;
  console.log(`Fetching ${fullUrl}...`);
  try {
    const response = await fetch(fullUrl);
    if (!response.ok) {
      console.warn(`Fetch failed with status ${response.status}, using mock data`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return mockData;
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Fetch error for ${fullUrl}:`, error);
    await new Promise((resolve) => setTimeout(resolve, delay));
    return mockData;
  }
}

export async function fetchReleaseData(repoName: string): Promise<ReleaseDataEntry[]> {
  try {
    const apiResponse = await fetchData<ReleaseDataEntry[]>(
      `/api/v1/stats/releases/frequency?repo_name=${encodeURIComponent(repoName)}`,
      []
    );
    if (Array.isArray(apiResponse)) {
      return apiResponse.map(({ month, releases }) => ({ month, releases }));
    }
    return [];
  } catch (error) {
    console.error("Error in fetchReleaseData, returning empty array:", error);
    return [];
  }
}

export async function fetchIssueData(repoName: string): Promise<IssueDataEntry[]> {
  try {
    const apiResponse = await fetchData<IssuesOpenClosedResponse>(
      `/api/v1/stats/issues/open-closed?repo_name=${encodeURIComponent(repoName)}`,
      {
        repository: repoName,
        data: [
          { month: "2024-12", opened: 12, closed: 12 },
          { month: "2025-01", opened: 40, closed: 24 },
          { month: "2025-02", opened: 30, closed: 35 },
          { month: "2025-03", opened: 20, closed: 45 },
          { month: "2025-04", opened: 27, closed: 38 },
          { month: "2025-05", opened: 18, closed: 48 },
        ],
      }
    );

    if (apiResponse && apiResponse.data && Array.isArray(apiResponse.data)) {
      const transformedData = apiResponse.data.map((item) => {
        const [year, monthNum] = item.month.split("-");
        const date = new Date(parseInt(year), parseInt(monthNum) - 1, 1);
        const monthName = date.toLocaleString("en-US", { month: "short" });
        return {
          month: monthName,
          opened: item.opened,
          closed: item.closed,
        };
      });

      console.log("Transformed Issue Data (in fetchIssueData):", transformedData);
      return transformedData;
    }

    console.error("Failed to fetch or transform issue data, returning empty array.");
    return [];
  } catch (error) {
    console.error("Error in fetchIssueData, returning empty array:", error);
    return [];
  }
}

export async function fetchIssueTypeData(): Promise<IssueTypeEntry[]> {
  return fetchData<IssueTypeEntry[]>("/api/issue-type-data", [
    { name: "Bugs", value: 30 },
    { name: "Features", value: 45 },
    { name: "Docs", value: 25 },
  ]);
}

export async function fetchDashboardMetrics(repoName: string): Promise<DashboardMetrics> {
  const mockMetrics: DashboardMetrics = {
    firstResponseTimeReadable: 2.1,
    avgIssueResolutionReadable: 3.0,
    prReviewTimeReadable: 1.5,
    firstResponseTimeSeconds: 2.1,
    avgIssueResolutionSeconds: 3.0,
    prReviewTimeSeconds: 1.5,
  };

  try {
    // Fetch first response time
    const firstResponseData = await fetchData<IssueFirstResponseTimeResponse>(
      `/api/v1/stats/issues/first-response-time?repo_name=${encodeURIComponent(repoName)}`,
      {
        average_response_time_seconds: mockMetrics.firstResponseTimeSeconds,
        average_response_time_readable: mockMetrics.firstResponseTimeReadable,
      },
      100
    );

    // Fetch average issue resolution time
    const issueResolutionData = await fetchData<IssueAvgResolutionTimeResponse>(
      `/api/v1/stats/issues/avg-resolution-time?repo_name=${encodeURIComponent(repoName)}`,
      {
        average_resolution_time_seconds: mockMetrics.avgIssueResolutionSeconds,
        average_resolution_time_readable: mockMetrics.avgIssueResolutionReadable,
      },
      100
    );

    // Fetch PR review time
    const prReviewData = await fetchData<PrReviewTimeResponse>(
      `/api/v1/stats/prs/review-time?repo_name=${encodeURIComponent(repoName)}`,
      {
        average_review_time_seconds: mockMetrics.prReviewTimeSeconds,
        average_review_time_readable: mockMetrics.prReviewTimeReadable,
      },
      100
    );

    // Combine metrics
    return {
      firstResponseTimeReadable: firstResponseData.average_response_time_readable,
      avgIssueResolutionReadable: issueResolutionData.average_resolution_time_readable,
      prReviewTimeReadable: prReviewData.average_review_time_readable,
      firstResponseTimeSeconds: firstResponseData.average_response_time_seconds,
      avgIssueResolutionSeconds: issueResolutionData.average_resolution_time_seconds,
      prReviewTimeSeconds: prReviewData.average_review_time_seconds,
    };
  } catch (error) {
    console.error("Error fetching dashboard metrics, using mock data:", error);
    return mockMetrics;
  }
}

export async function fetchNewContributors(repoName: string): Promise<number> {
  try {
    const response = await fetchData<NewContributors>(
      `/api/v1/stats/contributors/new?repo_name=${encodeURIComponent(repoName)}`,
      {
        new_contributors_count: 17,
      }
    );
    return response.new_contributors_count;
  } catch (error) {
    console.error("Error fetching new contributors, using default value:", error);
    return 17;
  }
} 