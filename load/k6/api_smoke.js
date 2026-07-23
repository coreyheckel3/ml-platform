import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = __ENV.FORGEML_BASE_URL || "http://127.0.0.1:8000";

export const options = {
  vus: 8,
  duration: "45s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
    checks: ["rate>0.99"]
  }
};

export default function () {
  const ready = http.get(`${baseUrl}/health/ready`);
  check(ready, {
    "ready endpoint returns 200": (response) => response.status === 200,
    "ready endpoint has request id": (response) => Boolean(response.headers["X-Request-Id"])
  });

  const metrics = http.get(`${baseUrl}/metrics`);
  check(metrics, {
    "metrics endpoint returns 200": (response) => response.status === 200,
    "metrics include api counter": (response) =>
      response.body.includes("forgeml_api_requests_total")
  });

  const auth = http.get(`${baseUrl}/api/v1/auth/me`);
  check(auth, {
    "unauthenticated me request is rejected": (response) => response.status === 401
  });

  sleep(1);
}
