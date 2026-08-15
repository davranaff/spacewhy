import assert from 'node:assert/strict';
import test from 'node:test';

import { SPACEWHY_BRAND } from 'src/brand/brand-config';
import { paths } from 'src/routes/paths';

const collectStrings = (value: unknown): string[] => {
  if (typeof value === 'string') {
    return [value];
  }

  if (typeof value !== 'object' || value === null) {
    return [];
  }

  return Object.values(value).flatMap(collectStrings);
};

test('brand configuration exposes a complete Spacewhy identity contract', () => {
  assert.equal(SPACEWHY_BRAND.productName, 'Spacewhy UI Kit');
  assert.equal(SPACEWHY_BRAND.shortName, 'Spacewhy');
  assert.equal(SPACEWHY_BRAND.websiteUrl, 'https://spacewhy.uz');
  assert.equal(SPACEWHY_BRAND.contactEmail.endsWith('@spacewhy.uz'), true);
  assert.equal(SPACEWHY_BRAND.supportEmail.endsWith('@spacewhy.uz'), true);
  assert.equal(SPACEWHY_BRAND.demoEmail.endsWith('@spacewhy.uz'), true);
});

test('route constants stay internal except for the explicit public website', () => {
  const routeStrings = collectStrings(paths);

  assert.ok(routeStrings.length > 50);
  routeStrings.forEach((path) => {
    assert.equal(path.startsWith('/') || path === SPACEWHY_BRAND.websiteUrl, true, path);
  });
  assert.equal(paths.docs, SPACEWHY_BRAND.documentationUrl);
  assert.equal(paths.changelog, SPACEWHY_BRAND.changelogUrl);
  assert.equal(paths.designSystem, SPACEWHY_BRAND.designSystemUrl);
  assert.equal(paths.website, SPACEWHY_BRAND.websiteUrl);
});

test('dynamic route builders preserve the expected route hierarchy', () => {
  assert.equal(paths.product.details('product-id'), '/product/product-id');
  assert.equal(paths.post.details('Glass System'), '/post/glass-system');
  assert.equal(paths.dashboard.user.edit('user-id'), '/dashboard/user/user-id/edit');
  assert.equal(
    paths.dashboard.product.edit('product-id'),
    '/dashboard/product/product-id/edit'
  );
});
