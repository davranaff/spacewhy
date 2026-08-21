import assert from 'node:assert/strict';
import test from 'node:test';

import { clampGlassValue, getGlassCssVars } from 'src/theme/glass-tokens';

const numericValue = (value: string) => Number.parseFloat(value);

const expectIncreasing = (values: number[]) => {
  values.slice(1).forEach((value, index) => {
    assert.ok(value > values[index]);
  });
};

const expectDecreasing = (values: number[]) => {
  values.slice(1).forEach((value, index) => {
    assert.ok(value < values[index]);
  });
};

test('clampGlassValue keeps every input inside the supported range', () => {
  assert.equal(clampGlassValue(-1), 0);
  assert.equal(clampGlassValue(42), 42);
  assert.equal(clampGlassValue(101), 100);
  assert.equal(clampGlassValue(Number.NaN), 0);
  assert.equal(clampGlassValue(Number.POSITIVE_INFINITY), 100);
  assert.equal(clampGlassValue(Number.NEGATIVE_INFINITY), 0);
});

test('glass CSS variables are finite across and beyond the control range', () => {
  [-100, 0, 25, 50, 75, 100, 200, Number.NaN].forEach((value) => {
    const variables = getGlassCssVars({
      glassIntensity: value,
      glassTransparency: value,
      glassLiquidity: value,
    });

    Object.values(variables).forEach((cssValue) => {
      assert.equal(Number.isFinite(numericValue(cssValue)), true, cssValue);
      assert.equal(cssValue.includes('NaN'), false, cssValue);
    });
  });
});

test('optical intensity changes only optical depth and remains monotonic', () => {
  const samples = [0, 25, 50, 75, 100].map((glassIntensity) =>
    getGlassCssVars({ glassIntensity, glassTransparency: 50, glassLiquidity: 50 })
  );

  expectIncreasing(samples.map((sample) => numericValue(sample['--spacewhy-glass-blur'])));
  expectIncreasing(
    samples.map((sample) => numericValue(sample['--spacewhy-glass-surface-blur']))
  );
  expectIncreasing(
    samples.map((sample) => numericValue(sample['--spacewhy-glass-saturation']))
  );
  assert.equal(new Set(samples.map((sample) => sample['--spacewhy-glass-alpha'])).size, 1);
  assert.equal(new Set(samples.map((sample) => sample['--spacewhy-glass-radius'])).size, 1);
});

test('transparency reveals more background without changing blur or geometry', () => {
  const samples = [0, 25, 50, 75, 100].map((glassTransparency) =>
    getGlassCssVars({ glassIntensity: 50, glassTransparency, glassLiquidity: 50 })
  );

  expectDecreasing(samples.map((sample) => numericValue(sample['--spacewhy-glass-alpha'])));
  expectDecreasing(
    samples.map((sample) => numericValue(sample['--spacewhy-glass-alpha-light']))
  );
  assert.equal(new Set(samples.map((sample) => sample['--spacewhy-glass-blur'])).size, 1);
  assert.equal(new Set(samples.map((sample) => sample['--spacewhy-glass-radius'])).size, 1);
});

test('liquidity softens edges and motion without changing optics or opacity', () => {
  const samples = [0, 25, 50, 75, 100].map((glassLiquidity) =>
    getGlassCssVars({ glassIntensity: 50, glassTransparency: 50, glassLiquidity })
  );

  expectIncreasing(samples.map((sample) => numericValue(sample['--spacewhy-glass-radius'])));
  expectIncreasing(
    samples.map((sample) => numericValue(sample['--spacewhy-glass-shadow-blur']))
  );
  expectIncreasing(
    samples.map((sample) => numericValue(sample['--spacewhy-glass-motion-duration']))
  );
  expectDecreasing(
    samples.map((sample) => numericValue(sample['--spacewhy-glass-edge-alpha-dark']))
  );
  assert.equal(new Set(samples.map((sample) => sample['--spacewhy-glass-blur'])).size, 1);
  assert.equal(new Set(samples.map((sample) => sample['--spacewhy-glass-alpha'])).size, 1);
});
