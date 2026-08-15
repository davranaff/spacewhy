export interface ShowcaseFormValues {
  name: string;
  email: string;
  description: string;
}

export type ShowcaseFormErrors = Partial<
  Record<keyof ShowcaseFormValues, string>
>;

export function validateShowcaseForm(
  values: ShowcaseFormValues,
): ShowcaseFormErrors {
  const errors: ShowcaseFormErrors = {};

  if (values.name.trim().length < 2)
    errors.name = 'Enter at least 2 characters.';
  if (!/^\S+@\S+\.\S+$/.test(values.email.trim()))
    errors.email = 'Enter a valid email address.';
  if (values.description.trim().length < 12)
    errors.description = 'Add at least 12 characters.';

  return errors;
}
