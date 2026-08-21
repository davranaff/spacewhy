import { useState, useCallback } from 'react';
// @mui
import { alpha } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import Portal from '@mui/material/Portal';
import InputBase from '@mui/material/InputBase';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
// hooks
import { useBoolean } from 'src/hooks/use-boolean';
import { useResponsive } from 'src/hooks/use-responsive';
// components
import Iconify from 'src/components/iconify';

// ----------------------------------------------------------------------

const ZINDEX = 1998;

const POSITION = 24;

type Props = {
  onCloseCompose: VoidFunction;
};

export default function MailCompose({ onCloseCompose }: Props) {
  const smUp = useResponsive('up', 'sm');

  const [message, setMessage] = useState('');

  const fullScreen = useBoolean();

  const modal = fullScreen.value || !smUp;

  const handleChangeMessage = useCallback((value: string) => {
    setMessage(value);
  }, []);

  const composeContent = (
    <>
      <Stack
        direction="row"
        alignItems="center"
        sx={{
          bgcolor: 'background.neutral',
          p: (theme) => theme.spacing(1.5, 1, 1.5, 2),
        }}
      >
        <Typography id="mail-compose-title" variant="h6" sx={{ flexGrow: 1 }}>
          New Message
        </Typography>

        {smUp && (
          <IconButton
            aria-label={fullScreen.value ? 'Exit fullscreen composer' : 'Open fullscreen composer'}
            onClick={fullScreen.onToggle}
          >
            <Iconify icon={fullScreen.value ? 'eva:collapse-fill' : 'eva:expand-fill'} />
          </IconButton>
        )}

        <IconButton aria-label="Close composer" onClick={onCloseCompose}>
          <Iconify icon="mingcute:close-line" />
        </IconButton>
      </Stack>

      <InputBase
        placeholder="To"
        inputProps={{ 'aria-label': 'Recipients' }}
        endAdornment={
          <Stack direction="row" spacing={0.5} sx={{ typography: 'subtitle2' }}>
            <Box sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}>Cc</Box>
            <Box sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}>Bcc</Box>
          </Stack>
        }
        sx={{
          px: 2,
          height: 48,
          borderBottom: (theme) => `solid 1px ${alpha(theme.palette.grey[500], 0.08)}`,
        }}
      />

      <InputBase
        placeholder="Subject"
        inputProps={{ 'aria-label': 'Subject' }}
        sx={{
          px: 2,
          height: 48,
          borderBottom: (theme) => `solid 1px ${alpha(theme.palette.grey[500], 0.08)}`,
        }}
      />

      <Stack spacing={2} flexGrow={1} sx={{ p: 2, minHeight: 0 }}>
        <InputBase
          multiline
          minRows={8}
          value={message}
          onChange={(event) => handleChangeMessage(event.target.value)}
          placeholder="Type a message"
          inputProps={{ 'aria-label': 'Message body' }}
          sx={{
            px: 2,
            py: 1.5,
            flexGrow: 1,
            minHeight: 180,
            alignItems: 'flex-start',
            border: (theme) => `solid 1px ${theme.palette.divider}`,
            borderRadius: 1.5,
            ...(modal && {
              minHeight: 0,
            }),
          }}
        />

        <Stack direction="row" alignItems="center">
          <Stack direction="row" alignItems="center" flexGrow={1}>
            <IconButton aria-label="Attach image">
              <Iconify icon="solar:gallery-add-bold" />
            </IconButton>

            <IconButton aria-label="Attach file">
              <Iconify icon="eva:attach-2-fill" />
            </IconButton>
          </Stack>

          <Button
            variant="contained"
            color="primary"
            endIcon={<Iconify icon="iconamoon:send-fill" />}
          >
            Send
          </Button>
        </Stack>
      </Stack>
    </>
  );

  if (modal) {
    return (
      <Dialog
        fullScreen
        open
        onClose={onCloseCompose}
        aria-labelledby="mail-compose-title"
        sx={{ zIndex: ZINDEX }}
      >
        {composeContent}
      </Dialog>
    );
  }

  return (
    <Portal>
      <Paper
        role="dialog"
        aria-labelledby="mail-compose-title"
        sx={{
          right: 0,
          bottom: 0,
          width: 560,
          maxWidth: `calc(100vw - ${POSITION * 2}px)`,
          borderRadius: 2,
          display: 'flex',
          position: 'fixed',
          zIndex: ZINDEX + 1,
          m: `${POSITION}px`,
          overflow: 'hidden',
          flexDirection: 'column',
          boxShadow: (theme) => theme.customShadows.dropdown,
        }}
      >
        {composeContent}
      </Paper>
    </Portal>
  );
}
