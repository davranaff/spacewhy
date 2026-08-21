import { formatPlayerTime } from '@/features/player/lib/format-time';

describe('formatPlayerTime', () => {
  it.each([
    [Number.NaN, '0:00'],
    [-3, '0:00'],
    [0, '0:00'],
    [7.9, '0:07'],
    [65, '1:05'],
    [3661, '61:01'],
  ])('formats %s seconds as %s', (seconds, expected) => {
    expect(formatPlayerTime(seconds)).toBe(expected);
  });
});
