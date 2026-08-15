import { validateShowcaseForm } from './showcase-validation';

describe('showcase form validation', () => {
  it('accepts a complete local form', () => {
    expect(
      validateShowcaseForm({
        name: 'Spacewhy',
        email: 'demo@spacewhy.uz',
        description: 'A complete local project description.',
      }),
    ).toEqual({});
  });

  it('returns field-specific accessible errors', () => {
    expect(
      validateShowcaseForm({
        name: '',
        email: 'invalid',
        description: 'short',
      }),
    ).toEqual({
      name: 'Enter at least 2 characters.',
      email: 'Enter a valid email address.',
      description: 'Add at least 12 characters.',
    });
  });
});
