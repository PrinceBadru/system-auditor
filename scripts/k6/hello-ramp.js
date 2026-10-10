import { check } from 'k6';
import http from 'k6/http';

export const options = {
  scenarios: {
    one_vu: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      startTime: '0s',
      exec: 'hello',
      tags: { load: '1-vu' },
    },
    two_vus: {
      executor: 'constant-vus',
      vus: 2,
      duration: '30s',
      startTime: '35s',
      exec: 'hello',
      tags: { load: '2-vu' },
    },
    four_vus: {
      executor: 'constant-vus',
      vus: 4,
      duration: '30s',
      startTime: '70s',
      exec: 'hello',
      tags: { load: '4-vu' },
    },
  },
  thresholds: {
    checks: ['rate==1'],
    http_req_failed: ['rate==0'],
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
