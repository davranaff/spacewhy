import { createAppTheme } from '@/shared/theme/tokens';
import {
  resolveGlassEffect,
  resolveGlassMaterial,
} from '@/shared/ui/glass-material';

const baseInput = {
  variant: 'surface' as const,
  opticalIntensity: 50,
  transparency: 50,
  surfaceLiquidity: 50,
};

describe('resolveGlassMaterial', () => {
  it('keeps the native material clear through the everyday range', () => {
    expect(resolveGlassEffect(0)).toBe('clear');
    expect(resolveGlassEffect(77)).toBe('clear');
    expect(resolveGlassEffect(78)).toBe('regular');
    expect(resolveGlassEffect(100)).toBe('regular');
  });

  it('keeps every numeric material value finite', () => {
    const material = resolveGlassMaterial(createAppTheme('dark'), baseInput);

    expect(material.blurAmount).toBeGreaterThan(0);
    expect(material.borderRadius).toBeGreaterThan(0);
    expect(material.shadowOpacity).toBeGreaterThan(0);
    expect(material.shadowRadius).toBeGreaterThan(0);
  });

  it('maps optical intensity and liquidity monotonically', () => {
    const theme = createAppTheme('light');
    const low = resolveGlassMaterial(theme, {
      ...baseInput,
      opticalIntensity: 0,
      surfaceLiquidity: 0,
    });
    const high = resolveGlassMaterial(theme, {
      ...baseInput,
      opticalIntensity: 100,
      surfaceLiquidity: 100,
    });

    expect(high.blurAmount).toBeGreaterThan(low.blurAmount);
    expect(high.borderRadius).toBeGreaterThan(low.borderRadius);
    expect(high.shadowRadius).toBeGreaterThan(low.shadowRadius);
  });

  it('keeps transparency independent from blur and geometry', () => {
    const theme = createAppTheme('dark');
    const solid = resolveGlassMaterial(theme, {
      ...baseInput,
      transparency: 0,
    });
    const clear = resolveGlassMaterial(theme, {
      ...baseInput,
      transparency: 100,
    });

    expect(clear.matteColor).not.toEqual(solid.matteColor);
    expect(clear.nativeTintColor).not.toEqual(solid.nativeTintColor);
    expect(clear.blurAmount).toEqual(solid.blurAmount);
    expect(clear.borderRadius).toEqual(solid.borderRadius);
    expect(clear.borderColor).toEqual(solid.borderColor);
    expect(clear.shadowRadius).toEqual(solid.shadowRadius);
  });

  it('keeps optical intensity independent from opacity and geometry', () => {
    const theme = createAppTheme('light');
    const clear = resolveGlassMaterial(theme, {
      ...baseInput,
      opticalIntensity: 0,
    });
    const deep = resolveGlassMaterial(theme, {
      ...baseInput,
      opticalIntensity: 100,
    });

    expect(deep.blurAmount).toBeGreaterThan(clear.blurAmount);
    expect(deep.matteColor).toEqual(clear.matteColor);
    expect(deep.nativeTintColor).not.toEqual(clear.nativeTintColor);
    expect(deep.borderRadius).toEqual(clear.borderRadius);
  });
});
