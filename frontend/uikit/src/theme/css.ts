// @mui
import { alpha, Theme } from '@mui/material/styles';
import { dividerClasses } from '@mui/material/Divider';
import { checkboxClasses } from '@mui/material/Checkbox';
import { menuItemClasses } from '@mui/material/MenuItem';
import { autocompleteClasses } from '@mui/material/Autocomplete';

// ----------------------------------------------------------------------

export const liquidGlass = ({
  theme,
  elevated = true,
  interactive = false,
  blurred = false,
  blurStrength = 'full',
}: {
  theme: Theme;
  elevated?: boolean;
  interactive?: boolean;
  blurred?: boolean;
  blurStrength?: 'full' | 'surface' | 'control';
}) => {
  const isDark = theme.palette.mode === 'dark';

  const blurVariable = {
    full: 'var(--spacewhy-glass-blur)',
    surface: 'var(--spacewhy-glass-surface-blur)',
    control: 'var(--spacewhy-glass-control-blur)',
  }[blurStrength];

  const elevatedShadow = isDark
    ? '0 var(--spacewhy-glass-shadow-offset) var(--spacewhy-glass-shadow-blur) rgba(0,0,0,var(--spacewhy-glass-shadow-alpha-dark))'
    : '0 var(--spacewhy-glass-shadow-offset) var(--spacewhy-glass-shadow-blur) rgba(26,32,44,var(--spacewhy-glass-shadow-alpha-light))';

  return {
    position: 'relative',
    overflow: 'hidden',
    border: isDark
      ? '1px solid rgba(255,255,255,var(--spacewhy-glass-edge-alpha-dark))'
      : '1px solid rgba(18,24,33,var(--spacewhy-glass-edge-alpha-light))',
    borderRadius: 'var(--spacewhy-glass-radius)',
    backgroundColor: isDark
      ? 'rgba(9, 9, 12, var(--spacewhy-glass-alpha))'
      : 'rgba(255, 255, 255, var(--spacewhy-glass-alpha-light))',
    backgroundImage: 'none',
    ...(blurred && {
      backdropFilter: `blur(${blurVariable}) saturate(var(--spacewhy-glass-saturation))`,
      WebkitBackdropFilter: `blur(${blurVariable}) saturate(var(--spacewhy-glass-saturation))`,
    }),
    boxShadow: elevated ? elevatedShadow : 'none',
    ...(interactive && {
      transition: theme.transitions.create(['transform', 'border-color'], {
        duration: 180,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
      }),
      '&:hover': {
        borderColor: isDark ? 'rgba(255,255,255,0.20)' : 'rgba(18,24,33,0.18)',
        transform: 'translateY(-1px) scale(1.006)',
      },
      '&:active': {
        transform: 'translateY(0) scale(0.985)',
      },
    }),
  } as const;
};

// ----------------------------------------------------------------------

export const paper = ({
  theme,
  bgcolor,
  dropdown,
}: {
  theme: Theme;
  bgcolor?: string;
  dropdown?: boolean;
}) => ({
  ...liquidGlass({ theme, blurred: true }),
  ...(!!bgcolor && {
    backgroundColor: bgcolor,
  }),
  ...(dropdown && {
    padding: theme.spacing(0.5),
    boxShadow: theme.customShadows.dropdown,
    borderRadius: theme.shape.borderRadius * 1.25,
  }),
});

// ----------------------------------------------------------------------

export const menuItem = (theme: Theme) => ({
  ...theme.typography.body2,
  padding: theme.spacing(0.75, 1),
  borderRadius: theme.shape.borderRadius * 0.75,
  '&:not(:last-of-type)': {
    marginBottom: 4,
  },
  [`&.${menuItemClasses.selected}`]: {
    fontWeight: theme.typography.fontWeightSemiBold,
    backgroundColor: theme.palette.action.selected,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  },
  [`& .${checkboxClasses.root}`]: {
    padding: theme.spacing(0.5),
    marginLeft: theme.spacing(-0.5),
    marginRight: theme.spacing(0.5),
  },
  [`&.${autocompleteClasses.option}[aria-selected="true"]`]: {
    backgroundColor: theme.palette.action.selected,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  },
  [`&+.${dividerClasses.root}`]: {
    margin: theme.spacing(0.5, 0),
  },
});

// ----------------------------------------------------------------------

type BgBlurProps = {
  blur?: number;
  opacity?: number;
  color?: string;
  imgUrl?: string;
};

export function bgBlur(props?: BgBlurProps) {
  const color = props?.color || '#000000';
  const blur = props?.blur || 6;
  const opacity = props?.opacity || 0.8;
  const imgUrl = props?.imgUrl;

  if (imgUrl) {
    return {
      position: 'relative',
      backgroundImage: `url(${imgUrl})`,
      '&:before': {
        position: 'absolute',
        top: 0,
        left: 0,
        zIndex: 9,
        content: '""',
        width: '100%',
        height: '100%',
        backdropFilter: `blur(${blur}px)`,
        WebkitBackdropFilter: `blur(${blur}px)`,
        backgroundColor: alpha(color, opacity),
      },
    } as const;
  }

  return {
    backdropFilter: `blur(${blur}px)`,
    WebkitBackdropFilter: `blur(${blur}px)`,
    backgroundColor: alpha(color, opacity),
  };
}

// ----------------------------------------------------------------------

type BgGradientProps = {
  direction?: string;
  color?: string;
  startColor?: string;
  endColor?: string;
  imgUrl?: string;
};

export function bgGradient(props?: BgGradientProps) {
  const direction = props?.direction || 'to bottom';
  const startColor = props?.startColor;
  const endColor = props?.endColor;
  const imgUrl = props?.imgUrl;
  const color = props?.color;

  if (imgUrl) {
    return {
      background: `linear-gradient(${direction}, ${startColor || color}, ${
        endColor || color
      }), url(${imgUrl})`,
      backgroundSize: 'cover',
      backgroundRepeat: 'no-repeat',
      backgroundPosition: 'center center',
    };
  }

  return {
    background: `linear-gradient(${direction}, ${startColor}, ${endColor})`,
  };
}

// ----------------------------------------------------------------------

export function textGradient(value: string) {
  return {
    background: `-webkit-linear-gradient(${value})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  };
}

// ----------------------------------------------------------------------

export const hideScroll = {
  x: {
    msOverflowStyle: 'none',
    scrollbarWidth: 'none',
    overflowX: 'scroll',
    '&::-webkit-scrollbar': {
      display: 'none',
    },
  },
  y: {
    msOverflowStyle: 'none',
    scrollbarWidth: 'none',
    overflowY: 'scroll',
    '&::-webkit-scrollbar': {
      display: 'none',
    },
  },
} as const;
