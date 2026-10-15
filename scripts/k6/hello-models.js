import { check } from 'k6';
import http from 'k6/http';

export const options = {
  scenarios: {
    open_model_fixed_arrival_rate: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 5,
      maxVUs: 10,
      exec: 'hello',
      tags: { model: 'open', load: '10-iterations-per-second' },
    },
    closed_model_fixed_users: {
      executor: 'constant-vus',
      vus: 4,
      duration: '30s',
      startTime: '65s',
      exec: 'hello',
      tags: { model: 'closed', load: '4-vus' },
    },
  },
  thresholds: {
    checks: ['rate==1'],
    http_req_failed: ['rate==0'],
    dropped_iterations: ['count==0'],
  },
};

export function hello() {
  const response = http.get('http://127.0.0.1:8000/hello');
  check(response, {
    'hello returns HTTP 200': (res) => res.status === 200,
    'Postgres connection is healthy': (res) =>
      res.json('services.postgres') === 'ok',
    'Redis connection is healthy': (res) => res.json('services.redis') === 'ok',
  });
}
