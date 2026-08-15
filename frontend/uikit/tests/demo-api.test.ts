import assert from 'node:assert/strict';
import test from 'node:test';

import { getDemoApiResponse } from 'src/_mock/_demo-api';
import { shouldUseLocalDemoApi } from 'src/utils/demo-api-mode';

test('local demo API is the default and remote mode requires an explicit flag', () => {
  assert.equal(shouldUseLocalDemoApi(undefined), true);
  assert.equal(shouldUseLocalDemoApi('false'), true);
  assert.equal(shouldUseLocalDemoApi('true'), false);
});

test('catalog endpoints provide navigable local list, details, and search data', () => {
  const productList = getDemoApiResponse('/api/product/list') as {
    products: { id: string; name: string }[];
  };
  const firstProduct = productList.products[0];

  assert.ok(productList.products.length >= 12);
  assert.ok(firstProduct.id);
  assert.ok(firstProduct.name);

  const details = getDemoApiResponse('/api/product/details', 'get', {
    productId: firstProduct.id,
  }) as { product: { id: string } };
  const search = getDemoApiResponse('/api/product/search', 'get', {
    query: firstProduct.name.slice(0, 3).toUpperCase(),
  }) as { results: { id: string }[] };

  assert.equal(details.product.id, firstProduct.id);
  assert.equal(search.results.some((product) => product.id === firstProduct.id), true);
});

test('dashboard demo endpoints return stable local contracts without a backend', () => {
  const labels = getDemoApiResponse('/api/mail/labels') as { labels: unknown[] };
  const conversations = getDemoApiResponse('/api/chat', 'get') as {
    conversations: unknown[];
  };
  const board = getDemoApiResponse('/api/kanban', 'get') as { board: { columns: unknown[] } };
  const calendar = getDemoApiResponse('/api/calendar', 'get') as { events: unknown[] };

  assert.ok(labels.labels.length > 0);
  assert.ok(conversations.conversations.length > 0);
  assert.ok(board.board.columns.length > 0);
  assert.ok(calendar.events.length > 0);
});

test('the local adapter ignores unknown endpoints so Axios can handle them normally', () => {
  assert.equal(getDemoApiResponse('/api/unknown'), undefined);
});
