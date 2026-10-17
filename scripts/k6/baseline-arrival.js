import { check } from 'k6';
import http from 'k6/http';

const arrivalRate = Number(__ENV.ARRIVAL_RATE || 5);
const durationSeconds = Number(__ENV.DURATION_SECONDS || 30);

if (!Number.isInteger(arrivalRate) || arrivalRate < 1) {
  throw new Error(`ARRIVAL_RATE must be a positive integer; got ${__ENV.ARRIVAL_RATE}`);
}
if (!Number.isInteger(durationSeconds) || durationSeconds < 1) {
  throw new Error(
    `DURATION_SECONDS must be a positive integer; got ${__ENV.DURATION_SECONDS}`,
  );
}

export const options = {
  scenarios: {
    fixed_arrival_rate: {
      executor: 'constant-arrival-rate',
      rate: arrivalRate,
      timeUnit: '1s',
      duration: `${durationSeconds}s`,
      preAllocatedVUs: 10,
      maxVUs: 50,
      tags: {
        model: 'open',
        arrival_rate: `${arrivalRate}`,
      },
    },
  },
};

export default function () {
  const response = http.get('http://127.0.0.1:8000/hello');
  check(response, {
    'hello returns HTTP 200': (res) => res.status === 200,
    'Postgres connection is healthy': (res) =>
      res.json('services.postgres') === 'ok',
    'Redis connection is healthy': (res) =>
      res.json('services.redis') === 'ok',
  });
}
