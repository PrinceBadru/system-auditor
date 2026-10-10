import { check } from 'k6';
import http from 'k6/http';

export const options = {
  vus: 1,
  duration: '10s',
  thresholds: {
    checks: ['rate==1'],
    http_req_failed: ['rate==0'],
  },
};

export default function () {
  const response = http.get('http://127.0.0.1:8000/hello');
  check(response, {
    'hello returns HTTP 200': (res) => res.status === 200,
    'Postgres connection is healthy': (res) =>
      res.json('services.postgres') === 'ok',
    'Redis connection is healthy': (res) => res.json('services.redis') === 'ok',
  });
}
