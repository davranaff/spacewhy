import type { PlayerTrack } from '@/features/player/types/player.types';

/**
 * Short royalty-free demo audio hosted by Samplelib. Playback is intentionally
 * network-backed: loading or connectivity failures surface as real errors.
 */
export const PLAYER_DEMO_QUEUE: readonly PlayerTrack[] = [
  {
    id: 'samplelib-15s',
    title: '15-second audio sample',
    artist: 'Samplelib demo audio',
    source: 'https://samplelib.com/mp3/sample-15s.mp3',
  },
  {
    id: 'samplelib-12s',
    title: '12-second audio sample',
    artist: 'Samplelib demo audio',
    source: 'https://samplelib.com/mp3/sample-12s.mp3',
  },
  {
    id: 'samplelib-9s',
    title: '9-second audio sample',
    artist: 'Samplelib demo audio',
    source: 'https://samplelib.com/mp3/sample-9s.mp3',
  },
];
